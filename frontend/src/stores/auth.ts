import { computed, ref } from "vue";
import { defineStore } from "pinia";
import { getCurrentUser, login, logout, refresh } from "../api/auth";
import type { User } from "../types/api";

const TAB_ACCOUNT_KEY = "enterprise-rag.client.account-id";
const TAB_RESTORE_BLOCKED_KEY = "enterprise-rag.client.restore-blocked";
const CHANNEL_NAME = "enterprise-rag.client-auth";
const tabId = typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
  ? crypto.randomUUID()
  : `${Date.now()}-${Math.random().toString(36).slice(2)}`;

type AuthMessage = {
  source: string;
  type: "account-changed" | "session-refreshed";
  user: User;
  accessToken?: string;
  csrfToken?: string;
};

function getTabAccountId() {
  const value = sessionStorage.getItem(TAB_ACCOUNT_KEY);
  return value ? Number(value) : null;
}

function setTabAccount(userId: number) {
  sessionStorage.setItem(TAB_ACCOUNT_KEY, String(userId));
  sessionStorage.removeItem(TAB_RESTORE_BLOCKED_KEY);
}

export const useAuthStore = defineStore("auth", () => {
  const token = ref<string | null>(null);
  const csrfToken = ref<string | null>(null);
  const user = ref<User | null>(null);
  const isLoading = ref(false);
  const isAuthenticated = computed(() => Boolean(token.value && user.value));
  const isAdmin = computed(() => user.value?.role === "admin");
  let restorePromise: Promise<void> | null = null;
  const channel = typeof BroadcastChannel === "undefined" ? null : new BroadcastChannel(CHANNEL_NAME);

  function readCsrfCookie() {
    const prefix = "rag_client_refresh_csrf=";
    return document.cookie
      .split(";")
      .map((item) => item.trim())
      .find((item) => item.startsWith(prefix))
      ?.slice(prefix.length) ?? null;
  }

  function clearSession(blockAutomaticRestore = false) {
    token.value = null;
    csrfToken.value = null;
    user.value = null;
    sessionStorage.removeItem(TAB_ACCOUNT_KEY);
    if (blockAutomaticRestore) sessionStorage.setItem(TAB_RESTORE_BLOCKED_KEY, "1");
    else sessionStorage.removeItem(TAB_RESTORE_BLOCKED_KEY);
  }

  function publish(message: Omit<AuthMessage, "source">) {
    channel?.postMessage({ ...message, source: tabId } satisfies AuthMessage);
  }

  async function runWithRefreshLock(task: () => Promise<void>) {
    if (!navigator.locks) {
      await task();
      return;
    }
    await navigator.locks.request("enterprise-rag.client-refresh", task);
  }

  channel?.addEventListener("message", (event: MessageEvent<AuthMessage>) => {
    const message = event.data;
    if (!message || message.source === tabId) return;
    if (sessionStorage.getItem(TAB_RESTORE_BLOCKED_KEY) === "1") return;

    const expectedUserId = getTabAccountId();
    if (expectedUserId !== null && expectedUserId !== message.user.id) {
      // A browser origin can only hold one refresh cookie. Do not silently
      // turn this tab into the account that signed in elsewhere.
      clearSession(true);
      return;
    }

    if (message.type === "session-refreshed" && message.accessToken && message.csrfToken) {
      token.value = message.accessToken;
      csrfToken.value = message.csrfToken;
      user.value = message.user;
      setTabAccount(message.user.id);
    }
  });

  async function signIn(username: string, password: string) {
    isLoading.value = true;
    try {
      clearSession();
      const result = await login(username, password);
      const currentUser = await getCurrentUser(result.access_token);
      token.value = result.access_token;
      csrfToken.value = result.csrf_token;
      user.value = currentUser;
      setTabAccount(currentUser.id);
      publish({ type: "account-changed", user: currentUser });
    } finally {
      isLoading.value = false;
    }
  }

  async function restoreSession() {
    if (user.value || restorePromise || sessionStorage.getItem(TAB_RESTORE_BLOCKED_KEY) === "1") {
      return restorePromise ?? Promise.resolve();
    }
    restorePromise = (async () => {
      try {
        await runWithRefreshLock(async () => {
          // Another tab may have refreshed and shared a fresh access token
          // while this tab waited for the browser-wide lock.
          if (user.value) return;

          const expectedUserId = getTabAccountId();
          const result = await refresh(csrfToken.value ?? readCsrfCookie() ?? "");
          const currentUser = await getCurrentUser(result.access_token);
          if (expectedUserId !== null && expectedUserId !== currentUser.id) {
            clearSession(true);
            return;
          }

          token.value = result.access_token;
          csrfToken.value = result.csrf_token;
          user.value = currentUser;
          setTabAccount(currentUser.id);
          publish({
            type: "session-refreshed",
            user: currentUser,
            accessToken: result.access_token,
            csrfToken: result.csrf_token,
          });
        });
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

  function updateCurrentUser(updated: User) {
    user.value = updated;
    setTabAccount(updated.id);
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
    updateCurrentUser,
  };
});
