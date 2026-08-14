export type UserRole = "admin" | "user";

export interface User {
  id: number;
  username: string;
  email: string | null;
  is_active: boolean;
  role: UserRole;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export type KnowledgeBaseRole = "owner" | "editor" | "viewer";

export interface KnowledgeBase {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
  role: KnowledgeBaseRole;
}

export interface DocumentItem {
  id: number;
  knowledge_base_id: number;
  filename: string;
  status: "uploaded" | "processing" | "ready" | "failed" | string;
  content_sha256: string | null;
  tags: string[];
  chunk_count: number;
  processed_at: string | null;
  error_message: string | null;
  created_at: string;
}

export interface DocumentChunk {
  document_id: number;
  filename: string;
  chunk_index: number;
  page: number | null;
  text: string;
  score: number;
}

export interface KnowledgeBaseMember {
  user_id: number;
  username: string;
  role: KnowledgeBaseRole;
}

export interface Citation {
  document_id: number;
  filename: string;
  page: number | null;
  chunk_index: number;
}

export interface ConversationMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  sources: Citation[] | null;
  feedback: "helpful" | "unhelpful" | null;
  feedback_comment: string | null;
  created_at: string;
}

export interface Conversation {
  id: number;
  knowledge_base_id: number | null;
  document_id: number | null;
  created_at: string;
  updated_at: string;
  messages: ConversationMessage[];
}
