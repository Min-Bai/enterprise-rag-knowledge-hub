from fastapi import APIRouter, Depends, HTTPException

from ..auth import get_current_user
from ..models.user import UserORM
from ..rate_limit import enforce_ai_rate_limit
from ..schemas.ai import (
    ProjectQuestionRequest,
    ProjectQuestionResponse,
    TaskPlanSuggestionRequest,
    TaskPlanSuggestionResponse,
    TaskTitleRewriteRequest,
    TaskTitleRewriteResponse,
)
from ..services.ai import (
    AiNotConfiguredError,
    AiProviderError,
    answer_project_question_service,
    rewrite_task_title_service,
    suggest_task_plan_service,
)


router = APIRouter(prefix="/ai", tags=["ai"])


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
