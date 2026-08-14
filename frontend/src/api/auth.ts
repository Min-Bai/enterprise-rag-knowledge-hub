import { request } from "./client";
import type { LoginResponse, User } from "../types/api";

export function login(username: string, password: string) {
  return request<LoginResponse>("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
}

export function getCurrentUser(accessToken: string) {
  return request<User>("/users/me", {}, accessToken);
}

export function logout(accessToken: string) {
  return request<void>("/users/me/logout", { method: "POST" }, accessToken);
}
