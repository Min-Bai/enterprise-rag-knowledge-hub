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
    { path: "/", redirect: "/chat" },
    {
      path: "/login",
      name: "login",
      component: () => import("../views/LoginView.vue"),
    },
    {
      path: "/chat",
      name: "chat",
      component: () => import("../views/ChatView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/conversations",
      name: "conversations",
      component: () => import("../views/ConversationListView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/knowledge-bases",
      name: "knowledge-bases",
      component: () => import("../views/KnowledgeBaseListView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/knowledge-bases/:id",
      component: () => import("../views/KnowledgeBaseOverviewView.vue"),
    },
    {
      path: "/knowledge-bases/:id/documents",
      component: () => import("../views/DocumentListView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/knowledge-bases/:id/retrieval-test",
      component: () => import("../views/RetrievalTestView.vue"),
      meta: { requiresAuth: true, knowledgeBaseManagerOnly: true },
    },
    {
      path: "/knowledge-bases/:id/access",
      component: () => import("../views/KnowledgeBaseAccessView.vue"),
      meta: { requiresAuth: true, knowledgeBaseOwnerOnly: true },
    },
    {
      path: "/settings",
      name: "settings",
      component: () => import("../views/SettingsView.vue"),
      meta: { requiresAuth: true, adminOnly: true },
    },
    { path: "/:pathMatch(.*)*", redirect: "/chat" },
  ],
});

router.beforeEach(async (to) => {
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
