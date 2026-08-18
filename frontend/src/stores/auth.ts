import { computed, ref } from "vue";
import { defineStore } from "pinia";
import { getCurrentUser, login, logout, refresh } from "../api/auth";
import type { User } from "../types/api";

const TAB_ACCOUNT_KEY = "enterprise-rag.client.account-id";
const TAB_REFRESH_TOKEN_KEY = "enterprise-rag.client.refresh-token";

function getTabAccountId() {
  const value = sessionStorage.getItem(TAB_ACCOUNT_KEY);
  return value ? Number(value) : null;
}

function setTabAccount(userId: number) {
  sessionStorage.setItem(TAB_ACCOUNT_KEY, String(userId));
}

export const useAuthStore = defineStore("auth", () => {
  const token = ref<string | null>(null);
  const refreshToken = ref<string | null>(sessionStorage.getItem(TAB_REFRESH_TOKEN_KEY));
  const user = ref<User | null>(null);
  const isLoading = ref(false);
  const isAuthenticated = computed(() => Boolean(token.value && user.value));
  const isAdmin = computed(() => user.value?.role === "admin");
  let restorePromise: Promise<void> | null = null;

  function clearSession() {
    token.value = null;
    refreshToken.value = null;
    user.value = null;
    sessionStorage.removeItem(TAB_ACCOUNT_KEY);
    sessionStorage.removeItem(TAB_REFRESH_TOKEN_KEY);
  }

  async function signIn(username: string, password: string) {
    isLoading.value = true;
    try {
      clearSession();
      const result = await login(username, password);
      const currentUser = await getCurrentUser(result.access_token);
      token.value = result.access_token;
      refreshToken.value = result.refresh_token;
      sessionStorage.setItem(TAB_REFRESH_TOKEN_KEY, result.refresh_token);
      user.value = currentUser;
      setTabAccount(currentUser.id);
    } finally {
      isLoading.value = false;
    }
  }

  async function restoreSession() {
    if (user.value || restorePromise || !refreshToken.value) return restorePromise ?? Promise.resolve();
    restorePromise = (async () => {
      try {
        const expectedUserId = getTabAccountId();
        const result = await refresh(refreshToken.value!);
        const currentUser = await getCurrentUser(result.access_token);
        if (expectedUserId !== null && expectedUserId !== currentUser.id) {
          clearSession();
          return;
        }
        token.value = result.access_token;
        refreshToken.value = result.refresh_token;
        sessionStorage.setItem(TAB_REFRESH_TOKEN_KEY, result.refresh_token);
        user.value = currentUser;
        setTabAccount(currentUser.id);
      } catch {
        clearSession();
      } finally {
        restorePromise = null;
      }
    })();
    return restorePromise;
  }

  async function signOut() {
    try { if (token.value) await logout(token.value); } finally { clearSession(); }
  }

  function updateCurrentUser(updated: User) { user.value = updated; setTabAccount(updated.id); }

  return { token, refreshToken, user, isLoading, isAuthenticated, isAdmin, signIn, signOut, restoreSession, clearSession, updateCurrentUser };
});
