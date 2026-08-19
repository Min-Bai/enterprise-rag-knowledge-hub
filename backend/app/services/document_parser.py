import csv
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from zipfile import BadZipFile, ZipFile
from xml.etree import ElementTree

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from ..config import OCR_ENABLED, OCR_LANGUAGES, TRANSCRIPTION_API_KEY, TRANSCRIPTION_BASE_URL, TRANSCRIPTION_ENABLED, TRANSCRIPTION_MODEL


OFFICE_MAX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
OFFICE_MAX_MEMBERS = 2_000
WORD_NAMESPACE = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
SPREADSHEET_NAMESPACE = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


@dataclass(frozen=True)
class DocumentChunk:
    text: str
    page: int


def extract_pdf_pages(storage_path: str) -> list[tuple[int, str]]:
    reader = PdfReader(Path(storage_path))
    pages = [
        (page_number, (page.extract_text() or "").strip())
        for page_number, page in enumerate(reader.pages, start=1)
    ]
    pages = [page for page in pages if page[1]]
    if not pages:
        raise ValueError("PDF does not contain extractable text")
    return pages


def extract_pdf_text(storage_path: str) -> str:
    return "\n".join(text for _, text in extract_pdf_pages(storage_path))

    return text

def create_text_splitter(
    *,
    chunk_size: int,
    overlap: int,
) -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        length_function=len,
        separators=["\n\n", "\n", "。", "！", "？", " ", ""],
    )


def split_text_into_chunks(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be between zero and chunk_size")

    cleaned_text = text.strip()
    if not cleaned_text:
        return []

    return create_text_splitter(
        chunk_size=chunk_size,
        overlap=overlap,
    ).split_text(cleaned_text)


def split_pdf_into_chunks(
    storage_path: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[DocumentChunk]:
    splitter = create_text_splitter(
        chunk_size=chunk_size,
        overlap=overlap,
    )
    return [
        DocumentChunk(text=chunk, page=page_number)
        for page_number, page_text in extract_pdf_pages(storage_path)
        for chunk in splitter.split_text(page_text)
    ]


def extract_text_document(storage_path: str) -> str:
    path = Path(storage_path)
    content = path.read_text(encoding="utf-8-sig").strip()
    if not content:
        raise ValueError("text document does not contain extractable text")
    if path.suffix.lower() == ".csv":
        rows = csv.reader(content.splitlines())
        content = "\n".join("\t".join(cell.strip() for cell in row) for row in rows).strip()
    if not content:
        raise ValueError("text document does not contain extractable text")
    return content


def _open_office_archive(storage_path: str, required_member: str) -> ZipFile:
    try:
        archive = ZipFile(Path(storage_path))
    except BadZipFile as error:
        raise ValueError("Office document is invalid") from error
    infos = archive.infolist()
    if len(infos) > OFFICE_MAX_MEMBERS or sum(info.file_size for info in infos) > OFFICE_MAX_UNCOMPRESSED_BYTES:
        archive.close()
        raise ValueError("Office document expands beyond the allowed extraction size")
    if required_member not in archive.namelist():
        archive.close()
        raise ValueError("Office document is invalid")
    return archive


def _xml_root(archive: ZipFile, member: str) -> ElementTree.Element:
    try:
        return ElementTree.fromstring(archive.read(member))
    except (KeyError, ElementTree.ParseError) as error:
        raise ValueError("Office document contains invalid XML") from error


def extract_docx_text(storage_path: str) -> str:
    with _open_office_archive(storage_path, "word/document.xml") as archive:
        root = _xml_root(archive, "word/document.xml")
    paragraphs = []
    for paragraph in root.iter(f"{WORD_NAMESPACE}p"):
        text = "".join(node.text or "" for node in paragraph.iter(f"{WORD_NAMESPACE}t")).strip()
        if text:
            paragraphs.append(text)
    content = "\n".join(paragraphs).strip()
    if not content:
        raise ValueError("Word document does not contain extractable text")
    return content


def _xlsx_shared_strings(archive: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = _xml_root(archive, "xl/sharedStrings.xml")
    return ["".join(node.text or "" for node in item.iter(f"{SPREADSHEET_NAMESPACE}t")) for item in root.iter(f"{SPREADSHEET_NAMESPACE}si")]


def _xlsx_cell_value(cell: ElementTree.Element, shared_strings: list[str]) -> str:
    cell_type = cell.get("t")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.iter(f"{SPREADSHEET_NAMESPACE}t"))
    value_node = cell.find(f"{SPREADSHEET_NAMESPACE}v")
    if value_node is None or value_node.text is None:
        return ""
    if cell_type == "s":
        try:
            return shared_strings[int(value_node.text)]
        except (IndexError, ValueError):
            return ""
    return value_node.text


def extract_xlsx_text(storage_path: str) -> str:
    with _open_office_archive(storage_path, "xl/workbook.xml") as archive:
        shared_strings = _xlsx_shared_strings(archive)
        sheet_members = sorted(
            member for member in archive.namelist()
            if member.startswith("xl/worksheets/") and member.endswith(".xml")
        )
        lines: list[str] = []
        for sheet_number, member in enumerate(sheet_members, start=1):
            root = _xml_root(archive, member)
            rows = []
            for row in root.iter(f"{SPREADSHEET_NAMESPACE}row"):
                values = [_xlsx_cell_value(cell, shared_strings).strip() for cell in row.iter(f"{SPREADSHEET_NAMESPACE}c")]
                if any(values):
                    rows.append("\t".join(values))
            if rows:
                lines.extend([f"工作表 {sheet_number}", *rows])
    content = "\n".join(lines).strip()
    if not content:
        raise ValueError("Excel document does not contain extractable cells")
    return content


def extract_xls_text(storage_path: str) -> str:
    try:
        import xlrd
    except ImportError as error:
        raise ValueError("旧版 Excel 文件需要安装 xlrd 解析组件") from error
    workbook = xlrd.open_workbook(storage_path, on_demand=True)
    lines: list[str] = []
    for sheet in workbook.sheets():
        lines.append(f"工作表：{sheet.name}")
        for row in sheet.get_rows():
            values = [str(cell.value).strip() for cell in row]
            if any(values):
                lines.append("\t".join(values))
    content = "\n".join(lines).strip()
    if not content:
        raise ValueError("Excel 文档不包含可提取的单元格")
    return content


def extract_doc_text(storage_path: str) -> str:
    try:
        result = subprocess.run(["antiword", storage_path], capture_output=True, text=True, timeout=30, check=True)
    except FileNotFoundError as error:
        raise ValueError("旧版 Word 文件需要在服务器安装 antiword，或先转换为 DOCX") from error
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise ValueError("旧版 Word 文件解析失败，请转换为 DOCX 后重试") from error
    content = result.stdout.strip()
    if not content:
        raise ValueError("Word 文档不包含可提取文本")
    return content


def extract_image_text(storage_path: str) -> str:
    if not OCR_ENABLED:
        raise ValueError("图片 OCR 未启用，请在环境变量中设置 OCR_ENABLED=true")
    try:
        from PIL import Image
        import pytesseract
        image = Image.open(storage_path)
        content = pytesseract.image_to_string(image, lang=OCR_LANGUAGES).strip()
    except ImportError as error:
        raise ValueError("图片 OCR 需要安装 Pillow、pytesseract 和 Tesseract OCR") from error
    except Exception as error:
        raise ValueError("图片 OCR 解析失败，请检查 Tesseract 语言包") from error
    if not content:
        raise ValueError("图片中未识别到可用文字")
    return content


def extract_audio_text(storage_path: str) -> str:
    if not TRANSCRIPTION_ENABLED or not TRANSCRIPTION_BASE_URL or not TRANSCRIPTION_API_KEY:
        raise ValueError("音频转写未配置，请设置 TRANSCRIPTION_ENABLED、TRANSCRIPTION_BASE_URL 和 TRANSCRIPTION_API_KEY")
    import requests
    try:
        with open(storage_path, "rb") as audio:
            response = requests.post(
                f"{TRANSCRIPTION_BASE_URL}/audio/transcriptions",
                headers={"Authorization": f"Bearer {TRANSCRIPTION_API_KEY}"},
                files={"file": (os.path.basename(storage_path), audio)},
                data={"model": TRANSCRIPTION_MODEL},
                timeout=180,
            )
        response.raise_for_status()
        content = str(response.json().get("text", "")).strip()
    except (requests.RequestException, ValueError, KeyError) as error:
        raise ValueError("音频转写服务请求失败") from error
    if not content:
        raise ValueError("音频转写未返回文本")
    return content


def split_document_into_chunks(
    storage_path: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[DocumentChunk]:
    suffix = Path(storage_path).suffix.lower()
    if suffix == ".pdf":
        return split_pdf_into_chunks(storage_path, chunk_size, overlap)
    if suffix == ".docx":
        content = extract_docx_text(storage_path)
    elif suffix == ".doc":
        content = extract_doc_text(storage_path)
    elif suffix == ".xlsx":
        content = extract_xlsx_text(storage_path)
    elif suffix == ".xls":
        content = extract_xls_text(storage_path)
    elif suffix in {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}:
        content = extract_image_text(storage_path)
    elif suffix in {".mp3", ".wav", ".m4a", ".ogg"}:
        content = extract_audio_text(storage_path)
    else:
        content = extract_text_document(storage_path)
    return [
        DocumentChunk(text=chunk, page=1)
        for chunk in split_text_into_chunks(
            content, chunk_size, overlap
        )
    ]
