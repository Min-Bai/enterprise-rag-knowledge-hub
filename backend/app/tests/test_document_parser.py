import pytest
from zipfile import ZipFile

from backend.app.services import document_parser
from backend.app.services.document_parser import split_document_into_chunks, split_pdf_into_chunks, split_text_into_chunks


def write_office_archive(path, files: dict[str, str]) -> None:
    with ZipFile(path, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)


def test_split_text_into_chunks_prefers_paragraph_boundaries():
    text = "First paragraph explains the policy.\n\nSecond paragraph explains exceptions."

    chunks = split_text_into_chunks(text, chunk_size=45, overlap=5)

    assert chunks == [
        "First paragraph explains the policy.",
        "Second paragraph explains exceptions.",
    ]


@pytest.mark.parametrize(
    ("chunk_size", "overlap", "message"),
    [
        (0, 0, "chunk_size must be greater than zero"),
        (10, -1, "overlap must be between zero and chunk_size"),
        (10, 10, "overlap must be between zero and chunk_size"),
    ],
)
def test_split_text_into_chunks_rejects_invalid_sizes(
    chunk_size,
    overlap,
    message,
):
    with pytest.raises(ValueError, match=message):
        split_text_into_chunks("document text", chunk_size, overlap)


def test_split_text_into_chunks_returns_empty_list_for_blank_text():
    assert split_text_into_chunks("  \n\t ") == []


def test_split_pdf_into_chunks_preserves_one_based_page_numbers(monkeypatch):
    class Page:
        def __init__(self, text):
            self.text = text

        def extract_text(self):
            return self.text

    class Reader:
        pages = [Page("First page policy."), Page("Second page exception.")]

    monkeypatch.setattr(document_parser, "PdfReader", lambda _: Reader())

    chunks = split_pdf_into_chunks("document.pdf", chunk_size=100, overlap=10)

    assert [(chunk.text, chunk.page) for chunk in chunks] == [
        ("First page policy.", 1),
        ("Second page exception.", 2),
    ]


def test_split_pdf_into_chunks_rejects_pdf_without_extractable_text(monkeypatch):
    class Page:
        def extract_text(self):
            return ""

    class Reader:
        pages = [Page()]

    monkeypatch.setattr(document_parser, "PdfReader", lambda _: Reader())

    with pytest.raises(ValueError, match="PDF does not contain extractable text"):
        split_pdf_into_chunks("document.pdf")


def test_split_document_into_chunks_reads_utf8_csv(tmp_path):
    document = tmp_path / "sales.csv"
    document.write_text("月份,销售额\n一月,100", encoding="utf-8")

    chunks = split_document_into_chunks(str(document), chunk_size=100, overlap=10)

    assert [(chunk.text, chunk.page) for chunk in chunks] == [("月份\t销售额\n一月\t100", 1)]


def test_split_document_into_chunks_reads_docx_paragraphs_and_table_cells(tmp_path):
    document = tmp_path / "handbook.docx"
    write_office_archive(document, {
        "word/document.xml": """<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>员工手册</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>年假</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>5 天</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>""",
    })

    chunks = split_document_into_chunks(str(document), chunk_size=100, overlap=10)

    assert [(chunk.text, chunk.page) for chunk in chunks] == [("员工手册\n年假\n5 天", 1)]


def test_split_document_into_chunks_reads_xlsx_shared_and_inline_strings(tmp_path):
    document = tmp_path / "sales.xlsx"
    write_office_archive(document, {
        "xl/workbook.xml": "<workbook xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\" />",
        "xl/sharedStrings.xml": "<sst xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\"><si><t>月份</t></si><si><t>销售额</t></si></sst>",
        "xl/worksheets/sheet1.xml": """<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row><row r="2"><c r="A2" t="inlineStr"><is><t>一月</t></is></c><c r="B2"><v>100</v></c></row></sheetData></worksheet>""",
    })

    chunks = split_document_into_chunks(str(document), chunk_size=100, overlap=10)

    assert [(chunk.text, chunk.page) for chunk in chunks] == [("工作表 1\n月份\t销售额\n一月\t100", 1)]
