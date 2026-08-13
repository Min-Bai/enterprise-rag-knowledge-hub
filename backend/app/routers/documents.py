from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
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
    reindex_document_service,
    retry_document_service,
)
from ..services.document_queue import enqueue_document_processing
from ..services.document_vectors import search_document_chunks
from ..rate_limit import enforce_document_upload_rate_limit

from ..exceptions import (
    DocumentNotFoundError,
    DocumentReindexNotAllowedError,
    DocumentRetryNotAllowedError,
)
from ..services.knowledge_bases import KnowledgeBaseNotFoundError
from ..services.knowledge_base_members import KnowledgeBaseAccessDeniedError
from ..services.audit_logs import write_audit_log

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentResponse])
def get_documents(
    knowledge_base_id: int | None = Query(default=None, ge=1),
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return get_documents_service(
            db=db,
            user_id=current_user.id,
            knowledge_base_id=knowledge_base_id,
        )
    except KnowledgeBaseNotFoundError:
        raise HTTPException(status_code=404, detail="knowledge base not found")
    except KnowledgeBaseAccessDeniedError:
        raise HTTPException(status_code=403, detail="knowledge base access denied")


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    knowledge_base_id: int | None = Form(default=None),
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    original_filename = file.filename or "document.pdf"
    
    enforce_document_upload_rate_limit(current_user.id)

    try:
        storage_path = await save_document_file(file)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    try:
        document = create_document_service(
            db=db,
            user_id=current_user.id,
            knowledge_base_id=knowledge_base_id,
            filename=original_filename,
            storage_path=storage_path,
        )
    except KnowledgeBaseNotFoundError:
        from pathlib import Path

        Path(storage_path).unlink(missing_ok=True)
        raise HTTPException(status_code=404, detail="knowledge base not found")
    except KnowledgeBaseAccessDeniedError:
        from pathlib import Path

        Path(storage_path).unlink(missing_ok=True)
        raise HTTPException(status_code=403, detail="knowledge base editor access required")

    enqueue_document_processing(document.id)
    write_audit_log(actor_user_id=current_user.id, action="document.uploaded", target_type="document", target_id=document.id, knowledge_base_id=document.knowledge_base_id, details={"filename": document.filename}, db=db)
    return document

@router.post("/search", response_model=DocumentSearchResponse)
def search_documents(
    request: DocumentSearchRequest,
    knowledge_base_id: int | None = Query(default=None, ge=1),
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        documents = get_ready_documents_service(
            db=db,
            user_id=current_user.id,
            knowledge_base_id=knowledge_base_id,
        )
    except KnowledgeBaseNotFoundError:
        raise HTTPException(status_code=404, detail="knowledge base not found")
    except KnowledgeBaseAccessDeniedError:
        raise HTTPException(status_code=403, detail="knowledge base access denied")
    filename_by_id = {
        document.id: document.filename
        for document in documents
    }

    chunks = search_document_chunks(
        question=request.question,
        user_id=None if knowledge_base_id is not None else current_user.id,
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

@router.post(
    "/{document_id}/reindex",
    response_model=DocumentResponse,
)
def reindex_document(
    document_id: int,
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        document = reindex_document_service(document_id=document_id, user_id=current_user.id, db=db)
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail="document not found")
    except DocumentReindexNotAllowedError:
        raise HTTPException(status_code=409, detail="only ready documents can be reindexed")
    except KnowledgeBaseAccessDeniedError:
        raise HTTPException(status_code=403, detail="knowledge base editor access required")
    enqueue_document_processing(document.id)
    write_audit_log(actor_user_id=current_user.id, action="document.reindexed", target_type="document", target_id=document.id, knowledge_base_id=document.knowledge_base_id, details=None, db=db)
    return document


@router.post(
    "/{document_id}/retry",
    response_model=DocumentResponse,
)
def retry_document(
    document_id: int,
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        document = retry_document_service(
            document_id=document_id,
            user_id=current_user.id,
            db=db,
        )
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="document not found",
        )
    except DocumentRetryNotAllowedError:
        raise HTTPException(
            status_code=409,
            detail="only failed documents can be retried",
        )
    except KnowledgeBaseAccessDeniedError:
        raise HTTPException(status_code=403, detail="knowledge base editor access required")

    enqueue_document_processing(document.id)
    write_audit_log(actor_user_id=current_user.id, action="document.retried", target_type="document", target_id=document.id, knowledge_base_id=document.knowledge_base_id, details=None, db=db)
    return document

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
        document = delete_document_service(
            document_id=document_id,
            user_id=current_user.id,
            db=db,
        )
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="document not found",
        )
    except KnowledgeBaseAccessDeniedError:
        raise HTTPException(status_code=403, detail="knowledge base editor access required")
    write_audit_log(actor_user_id=current_user.id, action="document.deleted", target_type="document", target_id=document.id, knowledge_base_id=document.knowledge_base_id, details={"filename": document.filename}, db=db)
