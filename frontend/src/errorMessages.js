const ERROR_MESSAGES = {
  ADMIN_PERMISSION_REQUIRED: "需要管理员权限才能执行此操作。",
  AI_PROVIDER_REQUEST_FAILED: "AI 服务暂时无法响应，请稍后重试。",
  AI_RATE_LIMITED: "问答请求过于频繁，请稍后重试。",
  AI_SERVICE_UNAVAILABLE: "AI 服务暂不可用，请联系管理员。",
  ANSWER_MESSAGE_NOT_FOUND: "未找到要操作的回答。",
  AUTH_INVALID_CREDENTIALS: "用户名或密码错误。",
  AUTH_INVALID_TOKEN: "登录已失效，请重新登录。",
  CONVERSATION_NOT_FOUND: "未找到该历史对话。",
  DEPENDENCIES_UNAVAILABLE: "系统服务暂不可用，请稍后重试。",
  DOCUMENT_DUPLICATE: "该知识库中已存在内容相同的文档。",
  DOCUMENT_FILE_INVALID: "文件不是有效的 PDF 文档。",
  DOCUMENT_FILE_TOO_LARGE: "文件不能超过 10 MB。",
  DOCUMENT_FILE_TYPE_INVALID: "仅支持上传 PDF 文件。",
  DOCUMENT_NOT_FOUND: "未找到该文档。",
  DOCUMENT_NOT_READY: "文档尚未处理完成，请稍后重试。",
  DOCUMENT_REINDEX_NOT_ALLOWED: "仅已就绪文档可以重新索引。",
  DOCUMENT_RETRY_NOT_ALLOWED: "仅处理失败的文档可以重试。",
  DOCUMENT_TAGS_LOCKED: "文档处理中，暂时不能修改标签。",
  INTERNAL_SERVER_ERROR: "系统发生异常，请稍后重试。",
  KNOWLEDGE_BASE_ACCESS_DENIED: "你没有访问该知识库的权限。",
  KNOWLEDGE_BASE_EDITOR_REQUIRED: "需要知识库编辑权限才能执行此操作。",
  KNOWLEDGE_BASE_MEMBER_NOT_FOUND: "未找到该知识库成员。",
  KNOWLEDGE_BASE_NOT_EMPTY: "请先删除知识库中的全部文档。",
  KNOWLEDGE_BASE_NOT_FOUND: "未找到该知识库。",
  KNOWLEDGE_BASE_OWNER_REQUIRED: "需要知识库所有者权限才能执行此操作。",
  LOGIN_RATE_LIMITED: "登录尝试过于频繁，请稍后重试。",
  RATE_LIMIT_SERVICE_UNAVAILABLE: "限流服务暂不可用，请稍后重试。",
  REQUEST_EMPTY_UPDATE: "请至少填写一项需要修改的内容。",
  USER_INACTIVE: "该账号已被停用。",
  USER_NOT_FOUND: "未找到该用户。",
  USERNAME_ALREADY_EXISTS: "用户名已存在，请更换后重试。",
};

const STATUS_MESSAGES = {
  400: "请求内容不正确，请检查后重试。",
  401: "登录已失效，请重新登录。",
  403: "你没有执行此操作的权限。",
  404: "未找到请求的资源。",
  409: "当前状态不允许执行此操作。",
  413: "文件不能超过 10 MB。",
  422: "填写内容不符合要求，请检查后重试。",
  429: "操作过于频繁，请稍后重试。",
  500: "系统发生异常，请稍后重试。",
  502: "上游服务暂时不可用，请稍后重试。",
  503: "服务暂时不可用，请稍后重试。",
};

function formatRetryAfter(seconds) {
  if (!Number.isFinite(seconds) || seconds <= 0) return "稍后";
  if (seconds < 60) return `${Math.ceil(seconds)} 秒后`;
  return `${Math.ceil(seconds / 60)} 分钟后`;
}

export function getUserErrorMessage({ code, status, retryAfterSeconds } = {}) {
  if (code === "DOCUMENT_UPLOAD_RATE_LIMITED") {
    return `上传操作过于频繁，请在${formatRetryAfter(retryAfterSeconds)}重试。`;
  }
  return ERROR_MESSAGES[code] || STATUS_MESSAGES[status] || "操作失败，请稍后重试。";
}
