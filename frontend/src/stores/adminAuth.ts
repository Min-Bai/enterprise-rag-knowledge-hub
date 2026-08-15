import { computed, ref } from "vue";
import { defineStore } from "pinia";
import { adminLogin, adminLogout, adminMe, adminRefresh } from "../api/admin";
import type { User } from "../types/api";

export const useAdminAuthStore = defineStore("adminAuth", () => {
  const token = ref<string | null>(null);
  const csrfToken = ref<string | null>(null);
  const user = ref<User | null>(null);
  const isLoading = ref(false);
  const isAuthenticated = computed(() => Boolean(token.value && user.value));
  let restorePromise: Promise<void> | null = null;
  const csrfFromCookie = () => document.cookie.split(";").map((item) => item.trim()).find((item) => item.startsWith("rag_admin_refresh_csrf="))?.slice("rag_admin_refresh_csrf=".length) ?? "";
  async function signIn(username: string, password: string) { isLoading.value = true; try { const result = await adminLogin(username, password); token.value = result.access_token; csrfToken.value = result.csrf_token; user.value = await adminMe(result.access_token); } finally { isLoading.value = false; } }
  async function restoreSession() { if (user.value || restorePromise) return restorePromise; restorePromise = (async () => { try { const result = await adminRefresh(csrfToken.value ?? csrfFromCookie()); token.value = result.access_token; csrfToken.value = result.csrf_token; user.value = await adminMe(result.access_token); } catch { clearSession(); } finally { restorePromise = null; } })(); return restorePromise; }
  async function signOut() { try { if (token.value) await adminLogout(token.value, csrfToken.value ?? csrfFromCookie()); } finally { clearSession(); } }
  function clearSession() { token.value = null; csrfToken.value = null; user.value = null; }
  return { token, csrfToken, user, isLoading, isAuthenticated, signIn, signOut, restoreSession, clearSession };
});
