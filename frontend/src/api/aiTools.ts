import { request } from "./client";
export interface ToolSource { document_id: number; filename: string; page: number | null; chunk_index: number; }
export interface ToolResult { result: string | { people: string[]; amounts: string[]; clauses: string[] }; sources: ToolSource[]; }
export function summarizeKnowledgeBase(token: string, id: number) { return request<ToolResult>(`/ai/knowledge-bases/${id}/summarize`, { method: "POST" }, token); }
export function extractKnowledgeBase(token: string, id: number) { return request<ToolResult>(`/ai/knowledge-bases/${id}/extract`, { method: "POST" }, token); }
export function askTableQuestion(token: string, id: number, question: string) { return request<ToolResult>(`/ai/knowledge-bases/${id}/table-query`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ knowledge_base_id: id, question }) }, token); }
