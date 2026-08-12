from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import get_current_user
from ..database import get_db
from ..models.user import UserORM
from ..rate_limit import enforce_ai_rate_limit
from sqlalchemy.orm import Session
from ..schemas.ai import (
    AssistantRequest,
    AssistantHistoryResponse,
    AssistantResponse,
    ProjectQuestionRequest,
    ProjectQuestionResponse,
    TaskPlanSuggestionRequest,
    TaskPlanSuggestionResponse,
    TaskTitleRewriteRequest,
    TaskTitleRewriteResponse,
    DocumentAnswerRequest,
    DocumentAnswerResponse,
)
from ..services.ai import (
    AiHistoryStoreError,
    AiNotConfiguredError,
    AiProviderError,
    DocumentNotFoundError,
    DocumentNotReadyError,
    answer_document_service,
    answer_project_question_service,
    answer_assistant_service,
    clear_assistant_history,
    load_assistant_history,
    rewrite_task_title_service,
    suggest_task_plan_service,
)


router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/assistant/history", response_model=AssistantHistoryResponse)
def get_assistant_conversation(
    current_user: UserORM = Depends(get_current_user),
):
    return {"items": load_assistant_history(current_user.id)}


@router.delete("/assistant/history", status_code=status.HTTP_204_NO_CONTENT)
def clear_assistant_conversation(
    current_user: UserORM = Depends(get_current_user),
):
    try:
        clear_assistant_history(current_user.id)
    except AiHistoryStoreError:
        raise HTTPException(
            status_code=503,
            detail="assistant history service unavailable",
        )


@router.post("/assistant", response_model=AssistantResponse)
def assistant(request: AssistantRequest, db=Depends(get_db), current_user: UserORM = Depends(get_current_user)):
    enforce_ai_rate_limit(current_user.id)
    try:
        return answer_assistant_service(request.message, current_user, db)
    except AiNotConfiguredError:
        raise HTTPException(status_code=503, detail="AI service is not configured")
    except AiProviderError:
        raise HTTPException(status_code=502, detail="AI provider request failed")


@router.post("/rewrite-task-title", response_model=TaskTitleRewriteResponse)
def rewrite_task_title(
    request: TaskTitleRewriteRequest,
    current_user: UserORM = Depends(get_current_user),
):
    enforce_ai_rate_limit(current_user.id)

    try:
        reply = rewrite_task_title_service(request.title)
    except AiNotConfiguredError:
        raise HTTPException(status_code=503, detail="AI service is not configured")
    except AiProviderError:
        raise HTTPException(status_code=502, detail="AI provider request failed")

    return {"reply": reply}


@router.post("/suggest-task-plan", response_model=TaskPlanSuggestionResponse)
def suggest_task_plan(
    request: TaskPlanSuggestionRequest,
    current_user: UserORM = Depends(get_current_user),
):
    enforce_ai_rate_limit(current_user.id)

    try:
        return suggest_task_plan_service(request.title)
    except AiNotConfiguredError:
        raise HTTPException(status_code=503, detail="AI service is not configured")
    except AiProviderError:
        raise HTTPException(status_code=502, detail="AI provider request failed")


@router.post("/answer-project-question", response_model=ProjectQuestionResponse)
def answer_project_question(
    request: ProjectQuestionRequest,
    current_user: UserORM = Depends(get_current_user),
):
    enforce_ai_rate_limit(current_user.id)

    try:
        return answer_project_question_service(request.question)
    except AiNotConfiguredError:
        raise HTTPException(status_code=503, detail="AI service is not configured")
    except AiProviderError:
        raise HTTPException(status_code=502, detail="AI provider request failed")

@router.post(
    "/document-answer",
    response_model=DocumentAnswerResponse,
)
def answer_document(
    request: DocumentAnswerRequest,
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(get_current_user),
):
    enforce_ai_rate_limit(current_user.id)

    try:
        return answer_document_service(
            request=request,
            current_user=current_user,
            db=db,
        )
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="document not found",
        )
    except DocumentNotReadyError:
        raise HTTPException(
            status_code=409,
            detail="document is not ready",
        )
    except AiNotConfiguredError:
        raise HTTPException(
            status_code=503,
            detail="AI service is not configured",
        )
    except AiProviderError:
        raise HTTPException(
            status_code=502,
            detail="AI provider request failed",
        )