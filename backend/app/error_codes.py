from typing import Any


ERROR_CODE_BY_DETAIL = {
    "AI provider request failed": "AI_PROVIDER_REQUEST_FAILED",
    "AI request limit exceeded": "AI_RATE_LIMITED",
    "AI service is not configured": "AI_SERVICE_UNAVAILABLE",
    "admin permission required": "ADMIN_PERMISSION_REQUIRED",
    "an identical document already exists in this knowledge base": "DOCUMENT_DUPLICATE",
    "answer message not found": "ANSWER_MESSAGE_NOT_FOUND",
    "conversation not found": "CONVERSATION_NOT_FOUND",
    "delete all documents before deleting this knowledge base": "KNOWLEDGE_BASE_NOT_EMPTY",
    "dependencies unavailable": "DEPENDENCIES_UNAVAILABLE",
    "document is not ready": "DOCUMENT_NOT_READY",
    "document not found": "DOCUMENT_NOT_FOUND",
    "document upload rate limit exceeded": "DOCUMENT_UPLOAD_RATE_LIMITED",
    "invalid authorization credentials": "AUTH_INVALID_TOKEN",
    "invalid access token": "AUTH_INVALID_TOKEN",
    "invalid refresh token": "AUTH_REFRESH_EXPIRED",
    "refresh token reuse detected": "AUTH_REFRESH_REUSE_DETECTED",
    "csrf validation failed": "AUTH_CSRF_INVALID",
    "missing access token": "AUTH_INVALID_TOKEN",
    "invalid cursor": "VALIDATION_ERROR",
    "invalid username or password": "AUTH_INVALID_CREDENTIALS",
    "invitation is invalid": "INVITATION_INVALID",
    "invitation has expired": "INVITATION_EXPIRED",
    "invitation email does not match": "INVITATION_EMAIL_MISMATCH",
    "invitation not found": "INVITATION_NOT_FOUND",
    "accepted invitation cannot be revoked": "INVITATION_ALREADY_ACCEPTED",
    "email already exists": "EMAIL_ALREADY_EXISTS",
    "password reset is invalid": "PASSWORD_RESET_INVALID",
    "password reset has expired": "PASSWORD_RESET_EXPIRED",
    "inactive user cannot reset password": "PASSWORD_RESET_USER_INACTIVE",
    "registration requests are disabled": "REGISTRATION_REQUESTS_DISABLED",
    "registration request already pending": "REGISTRATION_REQUEST_PENDING",
    "username or email already exists": "USERNAME_OR_EMAIL_ALREADY_EXISTS",
    "registration request not found": "REGISTRATION_REQUEST_NOT_FOUND",
    "registration request has already been reviewed": "REGISTRATION_REQUEST_ALREADY_REVIEWED",
    "password reset request not found": "PASSWORD_RESET_REQUEST_NOT_FOUND",
    "password reset request has already been reviewed": "PASSWORD_RESET_REQUEST_ALREADY_REVIEWED",
    "knowledge base access denied": "KNOWLEDGE_BASE_ACCESS_DENIED",
    "knowledge base editor access required": "KNOWLEDGE_BASE_EDITOR_REQUIRED",
    "knowledge base not found": "KNOWLEDGE_BASE_NOT_FOUND",
    "knowledge base owner access required": "KNOWLEDGE_BASE_OWNER_REQUIRED",
    "member not found": "KNOWLEDGE_BASE_MEMBER_NOT_FOUND",
    "only failed documents can be retried": "DOCUMENT_RETRY_NOT_ALLOWED",
    "only ready documents can be reindexed": "DOCUMENT_REINDEX_NOT_ALLOWED",
    "only PDF files are allowed": "DOCUMENT_FILE_TYPE_INVALID",
    "processing documents cannot have tags updated": "DOCUMENT_TAGS_LOCKED",
    "rate limit service unavailable": "RATE_LIMIT_SERVICE_UNAVAILABLE",
    "too many login attempts": "LOGIN_RATE_LIMITED",
    "self registration is disabled": "REGISTRATION_DISABLED",
    "user is inactive": "USER_INACTIVE",
    "user not found": "USER_NOT_FOUND",
    "username already exists": "USERNAME_ALREADY_EXISTS",
}


def get_error_code(detail: Any, status_code: int) -> str:
    if isinstance(detail, str):
        if detail.startswith("file size must not exceed "):
            return "DOCUMENT_FILE_TOO_LARGE"
        if detail == "file content type must be application/pdf":
            return "DOCUMENT_FILE_TYPE_INVALID"
        if detail == "invalid PDF file":
            return "DOCUMENT_FILE_INVALID"
        if detail.startswith("provide at least one field to update"):
            return "REQUEST_EMPTY_UPDATE"
        if detail in ERROR_CODE_BY_DETAIL:
            return ERROR_CODE_BY_DETAIL[detail]
    return f"HTTP_{status_code}"
