import { computed, ref } from "vue";
import { defineStore } from "pinia";
import { getCurrentUser, login, logout, refresh } from "../api/auth";
import type { User } from "../types/api";

export const useAuthStore = defineStore("auth", () => {
  const token = ref<string | null>(null);
  const csrfToken = ref<string | null>(null);
  const user = ref<User | null>(null);
  const isLoading = ref(false);
  const isAuthenticated = computed(() => Boolean(token.value && user.value));
  const isAdmin = computed(() => user.value?.role === "admin");
  let restorePromise: Promise<void> | null = null;

  function readCsrfCookie() {
    const prefix = "rag_client_refresh_csrf=";
    return document.cookie
      .split(";")
      .map((item) => item.trim())
      .find((item) => item.startsWith(prefix))
      ?.slice(prefix.length) ?? null;
  }

  async function signIn(username: string, password: string) {
    isLoading.value = true;
    try {
      const result = await login(username, password);
      token.value = result.access_token;
      csrfToken.value = result.csrf_token;
      user.value = await getCurrentUser(result.access_token);
    } finally {
      isLoading.value = false;
    }
  }

  async function restoreSession() {
    if (user.value || restorePromise) return restorePromise;
    restorePromise = (async () => {
      try {
        const result = await refresh(csrfToken.value ?? readCsrfCookie() ?? "");
        token.value = result.access_token;
        csrfToken.value = result.csrf_token;
        user.value = await getCurrentUser(result.access_token);
      } catch {
        clearSession();
      } finally {
        restorePromise = null;
      }
    })();
    return restorePromise;
  }

  async function signOut() {
    try {
      if (token.value) await logout(token.value, csrfToken.value ?? "");
    } finally {
      clearSession();
    }
  }

  function clearSession() {
    token.value = null;
    csrfToken.value = null;
    user.value = null;
  }

  return {
    token,
    csrfToken,
    user,
    isLoading,
    isAuthenticated,
    isAdmin,
    signIn,
    signOut,
    restoreSession,
    clearSession,
  };
});
