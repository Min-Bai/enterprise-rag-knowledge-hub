import { computed, ref } from "vue";
import { defineStore } from "pinia";
import { getCurrentUser, login, logout } from "../api/auth";
import type { User } from "../types/api";

const TOKEN_KEY = "enterprise_rag_access_token";

export const useAuthStore = defineStore("auth", () => {
  const token = ref<string | null>(sessionStorage.getItem(TOKEN_KEY));
  const user = ref<User | null>(null);
  const isLoading = ref(false);
  const isAuthenticated = computed(() => Boolean(token.value && user.value));
  const isAdmin = computed(() => user.value?.role === "admin");

  async function signIn(username: string, password: string) {
    isLoading.value = true;
    try {
      const result = await login(username, password);
      token.value = result.access_token;
      sessionStorage.setItem(TOKEN_KEY, result.access_token);
      user.value = await getCurrentUser(result.access_token);
    } finally {
      isLoading.value = false;
    }
  }

  async function restoreSession() {
    if (!token.value || user.value) return;
    try {
      user.value = await getCurrentUser(token.value);
    } catch {
      clearSession();
    }
  }

  async function signOut() {
    try {
      if (token.value) await logout(token.value);
    } finally {
      clearSession();
    }
  }

  function clearSession() {
    token.value = null;
    user.value = null;
    sessionStorage.removeItem(TOKEN_KEY);
  }

  return {
    token,
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
