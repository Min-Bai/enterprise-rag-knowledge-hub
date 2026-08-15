import type { User } from "../types/api";

export interface AuthTokens {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  csrf_token: string;
}

interface ApiEnvelope<T> {
  code: string;
  message: string;
  data: T;
  request_id: string;
}

async function v1Request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api/v1/client${path}`, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init.headers },
  });
  if (response.status === 204) return undefined as T;
  const body = (await response.json()) as ApiEnvelope<T>;
  if (!response.ok) throw new Error(body.message || "请求失败");
  return body.data;
}

export function login(username: string, password: string) {
  return v1Request<AuthTokens>("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
}

export function getCurrentUser(accessToken: string) {
  return v1Request<User>("/me", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}

export function refresh(csrfToken: string) {
  return v1Request<AuthTokens>("/auth/refresh", {
    method: "POST",
    headers: { "X-CSRF-Token": csrfToken },
  });
}

export function logout(accessToken: string, csrfToken: string) {
  return v1Request<void>("/auth/logout", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "X-CSRF-Token": csrfToken,
    },
  });
}
