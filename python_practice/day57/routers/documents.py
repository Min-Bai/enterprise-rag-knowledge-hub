from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models.user import UserORM
from ..schemas.document import DocumentResponse
from ..services.document_storage import save_document_file
from ..services.documents import create_document_service, get_documents_service
from ..services.document_processor import process_document

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
