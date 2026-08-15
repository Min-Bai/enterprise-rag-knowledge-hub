<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  BotMessageSquare,
  BookOpen,
  LogOut,
  MessageSquareText,
  History,
} from "lucide-vue-next";
import { useAuthStore } from "../stores/auth";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const activePath = computed(() =>
  route.path.startsWith("/app/knowledge-bases") ? "/app/knowledge-bases" : route.path,
);

async function handleLogout() {
  await auth.signOut();
  await router.push({ name: "login" });
}
</script>

<template>
  <div class="app-layout">
    <aside class="app-sidebar" aria-label="主导航">
      <RouterLink class="brand" to="/app/chat" aria-label="企业知识助手首页">
        <span class="brand-mark"><BotMessageSquare :size="21" /></span>
        <span>企业知识助手</span>
      </RouterLink>

      <nav class="primary-nav" aria-label="工作区">
        <RouterLink
          class="nav-item"
          :class="{ active: activePath === '/app/chat' }"
          to="/app/chat"
        >
          <MessageSquareText :size="18" />
          智能问答
        </RouterLink>
        <RouterLink
          class="nav-item"
          :class="{ active: activePath === '/app/conversations' }"
          to="/app/conversations"
          ><History :size="18" />会话记录</RouterLink
        >
        <RouterLink
          class="nav-item"
          :class="{ active: activePath === '/app/knowledge-bases' }"
          to="/app/knowledge-bases"
        >
          <BookOpen :size="18" />
          知识库
        </RouterLink>
      </nav>

      <div class="sidebar-footer">
        <div class="account-summary">
          <span class="account-avatar" aria-hidden="true">{{
            auth.user?.username.slice(0, 1).toUpperCase()
          }}</span>
          <span class="account-name">{{ auth.user?.username }}</span>
          <small>{{ auth.isAdmin ? "系统管理员" : "企业成员" }}</small>
        </div>
        <button
          class="icon-button"
          type="button"
          title="退出登录"
          aria-label="退出登录"
          @click="handleLogout"
        >
          <LogOut :size="18" />
        </button>
      </div>
    </aside>
    <main class="app-content"><slot /></main>
  </div>
</template>
