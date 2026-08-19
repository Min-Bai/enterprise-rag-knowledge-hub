import { ApiError, getUserErrorMessage, request } from "./client";
import type { Citation, Conversation, ConversationMessage } from "../types/api";

export function getKnowledgeBaseConversations(
  accessToken: string,
  knowledgeBaseId: number,
) {
  return request<Conversation[]>(
    `/ai/knowledge-bases/${knowledgeBaseId}/conversations`,
    {},
    accessToken,
  );
}

export function deleteConversation(
  accessToken: string,
  conversationId: number,
) {
  return request<void>(
    `/ai/conversations/${conversationId}`,
    { method: "DELETE" },
    accessToken,
  );
}

export function submitFeedback(
  accessToken: string,
  messageId: number,
  feedback: "helpful" | "unhelpful",
) {
  return request<ConversationMessage>(
    `/ai/answer-messages/${messageId}/feedback`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ feedback }),
    },
    accessToken,
  );
}

type StreamHandlers = {
  onMetadata: (metadata: {
    conversation_id: number;
    sources: Citation[];
  }) => void;
  onToken: (text: string) => void;
};

export async function streamKnowledgeBaseAnswer(
  accessToken: string,
  requestBody: {
    knowledge_base_id: number;
    question: string;
    conversation_id?: number;
    tags?: string[];
  },
  handlers: StreamHandlers,
  signal: AbortSignal,
) {
  const response = await fetch("/api/ai/knowledge-base-answer/stream", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(requestBody),
    signal,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(
      getUserErrorMessage(response.status, body?.code, body?.detail),
      response.status,
      body?.code,
    );
  }
  if (!response.body) throw new Error("问答服务暂不可用，请稍后重试。");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
    const frames = buffer.split(/\r?\n\r?\n/);
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      const event = frame.match(/^event: (.+)$/m)?.[1];
      const data = frame.match(/^data: (.+)$/m)?.[1];
      if (!event || data === undefined) continue;
      const payload = JSON.parse(data);
      if (event === "metadata") handlers.onMetadata(payload);
      if (event === "token") handlers.onToken(payload.text ?? "");
      if (event === "error")
        throw new Error("AI 服务生成回答失败，请稍后重试。");
    }
    if (done) break;
  }
}
