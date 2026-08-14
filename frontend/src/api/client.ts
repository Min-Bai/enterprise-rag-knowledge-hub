const API_PREFIX = "/api";

const ERROR_MESSAGES: Record<string, string> = {
  AUTH_INVALID_CREDENTIALS: "用户名或密码错误。",
  AUTH_INVALID_TOKEN: "登录已失效，请重新登录。",
  USER_INACTIVE: "该账号已被停用。",
  INTERNAL_SERVER_ERROR: "系统发生异常，请稍后重试。",
  DEPENDENCIES_UNAVAILABLE: "系统服务暂不可用，请稍后重试。",
};

const STATUS_MESSAGES: Record<number, string> = {
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

export class ApiError extends Error {
  status: number;
  code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

const DETAIL_MESSAGES: Record<string, string> = {
  "an identical document already exists in this knowledge base":
    "该知识库已存在内容相同的文档。",
  "only failed documents can be retried": "仅失败的文档可以重试。",
  "only ready documents can be reindexed": "仅处理完成的文档可以重建索引。",
  "processing documents cannot have tags updated":
    "文档解析中，暂时不能修改标签。",
  "delete all documents before deleting this knowledge base":
    "知识库内仍有文档，请先删除全部文档。",
  "document is not ready": "文档尚未处理完成，暂时无法问答。",
  "AI service is not configured": "AI 服务尚未配置，请联系系统管理员。",
  "AI provider request failed": "AI 服务请求失败，请稍后重试。",
  "username already exists": "该用户名已存在。",
  "old password is incorrect": "原密码不正确。",
};

export function getUserErrorMessage(
  status: number,
  code?: string,
  detail?: string,
): string {
  return (
    ERROR_MESSAGES[code ?? ""] ??
    DETAIL_MESSAGES[detail ?? ""] ??
    STATUS_MESSAGES[status] ??
    "操作失败，请稍后重试。"
  );
}

export function getDocumentProcessingErrorMessage(detail?: string | null) {
  return (
    DETAIL_MESSAGES[detail ?? ""] ??
    "文档处理失败，请重试；若问题持续存在，请检查 PDF 是否可正常打开。"
  );
}

export async function request<T>(
  path: string,
  options: RequestInit = {},
  accessToken?: string | null,
): Promise<T> {
  const headers = new Headers(options.headers);
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  const response = await fetch(`${API_PREFIX}${path}`, { ...options, headers });
  if (response.status === 204) return undefined as T;

  const contentType = response.headers.get("content-type") ?? "";
  const body = contentType.includes("application/json")
    ? await response.json()
    : null;
  if (!response.ok) {
    throw new ApiError(
      getUserErrorMessage(response.status, body?.code, body?.detail),
      response.status,
      body?.code,
    );
  }
  if (body === null)
    throw new ApiError(
      "服务器返回的数据格式不正确，请稍后重试。",
      response.status,
    );
  return body as T;
}
