import { createRouter, createWebHistory } from "vue-router";
import { pinia } from "../stores";
import { useAuthStore } from "../stores/auth";
import { getKnowledgeBases } from "../api/knowledgeBases";

declare module "vue-router" {
  interface RouteMeta {
    requiresAuth?: boolean;
    adminOnly?: boolean;
    knowledgeBaseOwnerOnly?: boolean;
    knowledgeBaseManagerOnly?: boolean;
  }
}

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/app/chat" },
    {
      path: "/login",
      name: "login",
      component: () => import("../views/LoginView.vue"),
    },
    {
      path: "/admin/login",
      name: "admin-login",
      component: () => import("../views/AdminLoginView.vue"),
    },
    {
      path: "/admin/users",
      name: "admin-users",
      component: () => import("../views/AdminUsersView.vue"),
      meta: { requiresAuth: true, adminOnly: true },
    },
    {
      path: "/admin/jobs",
      name: "admin-jobs",
      component: () => import("../views/AdminOperationsView.vue"),
      meta: { requiresAuth: true, adminOnly: true },
    },
    {
      path: "/admin/analytics",
      name: "admin-analytics",
      component: () => import("../views/AdminOperationsView.vue"),
      meta: { requiresAuth: true, adminOnly: true },
    },
    {
      path: "/app/chat",
      alias: "/chat",
      name: "chat",
      component: () => import("../views/ChatView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/app/conversations",
      alias: "/conversations",
      name: "conversations",
      component: () => import("../views/ConversationListView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/app/knowledge-bases",
      alias: "/knowledge-bases",
      name: "knowledge-bases",
      component: () => import("../views/KnowledgeBaseListView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/app/knowledge-bases/:id",
      alias: "/knowledge-bases/:id",
      component: () => import("../views/KnowledgeBaseOverviewView.vue"),
    },
    {
      path: "/app/knowledge-bases/:id/documents",
      alias: "/knowledge-bases/:id/documents",
      component: () => import("../views/DocumentListView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/app/knowledge-bases/:id/retrieval-test",
      alias: "/knowledge-bases/:id/retrieval-test",
      component: () => import("../views/RetrievalTestView.vue"),
      meta: { requiresAuth: true, knowledgeBaseManagerOnly: true },
    },
    {
      path: "/app/knowledge-bases/:id/access",
      alias: "/knowledge-bases/:id/access",
      component: () => import("../views/KnowledgeBaseAccessView.vue"),
      meta: { requiresAuth: true, knowledgeBaseOwnerOnly: true },
    },
    {
      path: "/settings",
      name: "settings",
      component: () => import("../views/SettingsView.vue"),
      meta: { requiresAuth: true, adminOnly: true },
    },
    { path: "/:pathMatch(.*)*", redirect: "/app/chat" },
  ],
});

router.beforeEach(async (to) => {
  if (to.path.startsWith("/admin")) {
    const { useAdminAuthStore } = await import("../stores/adminAuth");
    const adminAuth = useAdminAuthStore(pinia);
    await adminAuth.restoreSession();
    if (to.name === "admin-login" && adminAuth.isAuthenticated) return { name: "admin-users" };
    if (to.name !== "admin-login" && !adminAuth.isAuthenticated) return { name: "admin-login" };
    return true;
  }
  const auth = useAuthStore(pinia);
  await auth.restoreSession();
  if (to.meta.requiresAuth && !auth.isAuthenticated) return { name: "login" };
  if (to.meta.adminOnly && !auth.isAdmin) return { name: "chat" };
  if (
    (to.meta.knowledgeBaseOwnerOnly || to.meta.knowledgeBaseManagerOnly) &&
    auth.token
  ) {
    const id = Number(to.params.id);
    try {
      const knowledgeBase = (await getKnowledgeBases(auth.token)).find(
        (item) => item.id === id,
      );
      const isOwner = knowledgeBase?.role === "owner";
      const canManage = isOwner || knowledgeBase?.role === "editor";
      if (
        (to.meta.knowledgeBaseOwnerOnly && !isOwner) ||
        (to.meta.knowledgeBaseManagerOnly && !canManage)
      ) {
        return { name: "knowledge-bases" };
      }
    } catch {
      return { name: "knowledge-bases" };
    }
  }
  if (to.name === "login" && auth.isAuthenticated) return { name: "chat" };
  return true;
});
