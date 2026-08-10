from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models.user import UserORM
from ..schemas.document import (
    DocumentResponse,
    DocumentSearchRequest,
    DocumentSearchResponse,
)
from ..services.document_storage import save_document_file
from ..services.documents import (
    create_document_service,
    delete_document_service,
    get_documents_service,
    get_ready_documents_service,
)
from ..services.document_processor import process_document
from ..services.document_vectors import search_document_chunks

from ..exceptions import DocumentNotFoundError

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentResponse])
def get_documents(
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_documents_service(db=db, user_id=current_user.id)


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    original_filename = file.filename or "document.pdf"

    try:
        storage_path = await save_document_file(file)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    document = create_document_service(
        db=db,
        user_id=current_user.id,
        filename=original_filename,
        storage_path=storage_path,
    )

    background_tasks.add_task(process_document, document.id)
    return document

@router.post("/search", response_model=DocumentSearchResponse)
def search_documents(
    request: DocumentSearchRequest,
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    documents = get_ready_documents_service(
        db=db,
        user_id=current_user.id,
    )
    filename_by_id = {
        document.id: document.filename
        for document in documents
    }

    chunks = search_document_chunks(
        question=request.question,
        user_id=current_user.id,
        document_ids=list(filename_by_id),
    )

    items = [
        {
            **chunk,
            "filename": filename_by_id[int(chunk["document_id"])],
        }
        for chunk in chunks
    ]
    return {"items": items}

@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_document(
    document_id: int,
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        delete_document_service(
            document_id=document_id,
            user_id=current_user.id,
            db=db,
        )
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="document not found",
        )