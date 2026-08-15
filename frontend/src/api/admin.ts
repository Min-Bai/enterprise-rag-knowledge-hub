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
export function updateAdminProfile(token: string, payload: { username?: string; email?: string; display_name?: string; avatar_url?: string; bio?: string }) { return adminRequest<User>("/me", { method: "PATCH", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(payload) }); }
export function changeAdminPassword(token: string, payload: { old_password: string; new_password: string }) { return adminRequest<void>("/me/password", { method: "PATCH", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(payload) }); }
export function getAdminUsers(token: string, cursor?: number) { return adminRequest<{ items: User[]; page: { next_cursor: number | null; has_more: boolean; limit: number } }>(`/users?limit=20${cursor ? `&cursor=${cursor}` : ""}`, { headers: { Authorization: `Bearer ${token}` } }); }
export function createAdminUser(token: string, payload: { username: string; email?: string; password: string; role: UserRole }) { return adminRequest<User>("/users", { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(payload) }); }
export function setUserRole(token: string, id: number, role: UserRole) { return adminRequest<User>(`/users/${id}/role`, { method: "PATCH", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify({ role }) }); }
export function setUserStatus(token: string, id: number, is_active: boolean) { return adminRequest<User>(`/users/${id}/status`, { method: "PATCH", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify({ is_active }) }); }
export function deleteAdminUser(token: string, id: number) { return adminRequest<void>(`/users/${id}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } }); }
export interface UserInvitation { id: string; email: string; expires_at: string; accepted_at: string | null; revoked_at: string | null; created_at: string; created_by_user_id: number | null; }
export interface CreatedUserInvitation extends UserInvitation { invitation_token: string; }
export function getUserInvitations(token: string) { return adminRequest<UserInvitation[]>("/invitations", { headers: { Authorization: `Bearer ${token}` } }); }
export function createUserInvitation(token: string, payload: { email: string; expires_in_hours: number }) { return adminRequest<CreatedUserInvitation>("/invitations", { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(payload) }); }
export function revokeUserInvitation(token: string, id: string) { return adminRequest<void>(`/invitations/${id}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } }); }
export function createPasswordResetLink(token: string, userId: number, expiresInHours: number) { return adminRequest<{ expires_at: string; reset_token: string }>(`/users/${userId}/password-reset`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify({ expires_in_hours: expiresInHours }) }); }
export function getOverview(token: string) { return adminRequest<{ users: number; knowledge_bases: number; documents: number; ready_documents: number }>("/analytics/overview", { headers: { Authorization: `Bearer ${token}` } }); }
export function getWorkerStatus(token: string) { return adminRequest<{ registered_workers: string[]; active_tasks: number; reserved_tasks: number }>("/operations/worker-status", { headers: { Authorization: `Bearer ${token}` } }); }
export interface AdminJob { id: number; filename: string; status: string; error_message: string | null; created_at: string; knowledge_base_id: number; }
export function getAdminJobs(token: string) { return adminRequest<{ status_counts: Record<string, number>; recent: AdminJob[] }>("/operations/jobs", { headers: { Authorization: `Bearer ${token}` } }); }
export interface AuditLog { id: number; actor_user_id: number; actor_username: string; action: string; target_type: string; target_id: number | null; details: Record<string, unknown> | null; created_at: string; }
export function getAdminAuditLogs(token: string) { return adminRequest<AuditLog[]>("/audit-logs", { headers: { Authorization: `Bearer ${token}` } }); }
