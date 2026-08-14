import { request } from "./client";
import type { User, UserRole } from "../types/api";

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
