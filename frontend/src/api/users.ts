import { request } from "./client";
import type { PublicUserProfile, User, UserRole } from "../types/api";

export function updateMyProfile(accessToken: string, payload: { username?: string; email?: string; display_name?: string; avatar_url?: string; bio?: string }) {
  return request<User>("/users/me", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }, accessToken);
}
export function changeMyPassword(accessToken: string, payload: { old_password: string; new_password: string }) {
  return request<void>("/users/me/password", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }, accessToken);
}
export function getPublicUserProfile(accessToken: string, id: number) {
  return request<PublicUserProfile>(`/users/${id}/profile`, {}, accessToken);
}

export function getUsers(accessToken: string) {
  return request<User[]>("/users", {}, accessToken);
}
export function updateUserRole(
  accessToken: string,
  id: number,
  role: UserRole,
) {
  return request<User>(
    `/users/${id}/role`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role }),
    },
    accessToken,
  );
}
export function deactivateUser(accessToken: string, id: number) {
  return request<User>(
    `/users/${id}/deactivate`,
    { method: "PATCH" },
    accessToken,
  );
}
