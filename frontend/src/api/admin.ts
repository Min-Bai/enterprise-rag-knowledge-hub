import type { User, UserRole } from "../types/api";

export interface AdminTokens { access_token: string; token_type: "bearer"; expires_in: number; csrf_token: string; }
interface Envelope<T> { code: string; message: string; data: T; request_id: string; }

async function adminRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api/v1/admin${path}`, { ...init, credentials: "include", headers: { "Content-Type": "application/json", ...init.headers } });
  if (response.status === 204) return undefined as T;
  const body = await response.json() as Envelope<T>;
  if (!response.ok) throw new Error(body.message || "请求失败");
  return body.data;
}

export function adminLogin(username: string, password: string) { return adminRequest<AdminTokens>("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }); }
export function adminRefresh(csrfToken: string) { return adminRequest<AdminTokens>("/auth/refresh", { method: "POST", headers: { "X-CSRF-Token": csrfToken } }); }
export function adminLogout(token: string, csrfToken: string) { return adminRequest<void>("/auth/logout", { method: "POST", headers: { Authorization: `Bearer ${token}`, "X-CSRF-Token": csrfToken } }); }
export function adminMe(token: string) { return adminRequest<User>("/me", { headers: { Authorization: `Bearer ${token}` } }); }
export function getAdminUsers(token: string, cursor?: number) { return adminRequest<{ items: User[]; page: { next_cursor: number | null; has_more: boolean; limit: number } }>(`/users?limit=20${cursor ? `&cursor=${cursor}` : ""}`, { headers: { Authorization: `Bearer ${token}` } }); }
export function setUserRole(token: string, id: number, role: UserRole) { return adminRequest<User>(`/users/${id}/role`, { method: "PATCH", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify({ role }) }); }
export function setUserStatus(token: string, id: number, is_active: boolean) { return adminRequest<User>(`/users/${id}/status`, { method: "PATCH", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify({ is_active }) }); }
export function getOverview(token: string) { return adminRequest<{ users: number; knowledge_bases: number; documents: number; ready_documents: number }>("/analytics/overview", { headers: { Authorization: `Bearer ${token}` } }); }
export function getWorkerStatus(token: string) { return adminRequest<{ registered_workers: string[]; active_tasks: number; reserved_tasks: number }>("/operations/worker-status", { headers: { Authorization: `Bearer ${token}` } }); }
