import { ApiError, getUserErrorMessage, request } from "./client";
import type { DocumentChunk, DocumentItem } from "../types/api";

export async function downloadDocument(
  accessToken: string,
  documentId: number,
  filename: string,
) {
  const response = await fetch(`/api/documents/${documentId}/download`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) throw new Error("下载文档失败，请稍后重试。");
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function getDocuments(
  accessToken: string,
  knowledgeBaseId: number,
  limit = 100,
  offset = 0,
) {
  return request<DocumentItem[]>(
    `/documents?knowledge_base_id=${knowledgeBaseId}&limit=${limit}&offset=${offset}`,
    {},
    accessToken,
  );
}

export function retryDocument(accessToken: string, id: number) {
  return request<DocumentItem>(
    `/documents/${id}/retry`,
    { method: "POST" },
    accessToken,
  );
}

export function reindexDocument(accessToken: string, id: number) {
  return request<DocumentItem>(
    `/documents/${id}/reindex`,
    { method: "POST" },
    accessToken,
  );
}

export function deleteDocument(accessToken: string, id: number) {
  return request<void>(`/documents/${id}`, { method: "DELETE" }, accessToken);
}

export function updateDocumentTags(
  accessToken: string,
  id: number,
  tags: string[],
) {
  return request<DocumentItem>(
    `/documents/${id}/tags`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tags }),
    },
    accessToken,
  );
}

export function searchDocuments(
  accessToken: string,
  knowledgeBaseId: number,
  payload: { question: string; tags: string[] },
) {
  return request<{ items: DocumentChunk[] }>(
    `/documents/search?knowledge_base_id=${knowledgeBaseId}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
    accessToken,
  );
}

export async function uploadDocument(
  accessToken: string,
  knowledgeBaseId: number,
  file: File,
  tags: string[],
) {
  const body = new FormData();
  body.append("file", file);
  body.append("knowledge_base_id", String(knowledgeBaseId));
  if (tags.length) body.append("tags", tags.join(","));
  const response = await fetch("/api/documents", {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
    body,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new ApiError(
      getUserErrorMessage(response.status, payload?.code, payload?.detail),
      response.status,
      payload?.code,
    );
  }
  return response.json() as Promise<DocumentItem>;
}
