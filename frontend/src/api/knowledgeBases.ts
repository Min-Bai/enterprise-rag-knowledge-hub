import { request } from "./client";
import type { KnowledgeBase, KnowledgeBaseMember } from "../types/api";

export function getKnowledgeBases(accessToken: string) {
  return request<KnowledgeBase[]>("/knowledge-bases", {}, accessToken);
}

export function createKnowledgeBase(
  accessToken: string,
  payload: { name: string; description?: string },
) {
  return request<KnowledgeBase>(
    "/knowledge-bases",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
    accessToken,
  );
}

export function deleteKnowledgeBase(accessToken: string, id: number) {
  return request<void>(
    `/knowledge-bases/${id}`,
    { method: "DELETE" },
    accessToken,
  );
}

export function getKnowledgeBaseMembers(accessToken: string, id: number) {
  return request<KnowledgeBaseMember[]>(
    `/knowledge-bases/${id}/members`,
    {},
    accessToken,
  );
}

export function addKnowledgeBaseMember(
  accessToken: string,
  id: number,
  payload: { username: string; role: "editor" | "viewer" },
) {
  return request<KnowledgeBaseMember>(
    `/knowledge-bases/${id}/members`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
    accessToken,
  );
}

export function removeKnowledgeBaseMember(
  accessToken: string,
  id: number,
  userId: number,
) {
  return request<void>(
    `/knowledge-bases/${id}/members/${userId}`,
    { method: "DELETE" },
    accessToken,
  );
}
