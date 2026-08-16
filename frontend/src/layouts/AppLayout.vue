<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  BotMessageSquare,
  BookOpen,
  LogOut,
  MessageSquareText,
  History,
  Settings,
} from "lucide-vue-next";
import { useAuthStore } from "../stores/auth";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const isLoggingOut = ref(false);
const activePath = computed(() =>
  route.path.startsWith("/app/knowledge-bases") ? "/app/knowledge-bases" : route.path,
);
const sectionTitle = computed(() => {
  if (route.path.startsWith("/app/knowledge-bases")) return "知识库管理";
  if (route.path.startsWith("/app/conversations")) return "历史会话";
  if (route.path.startsWith("/app/profile") || route.path.startsWith("/app/security")) return "账户中心";
  return "问答对话";
});

async function handleLogout() {
  if (isLoggingOut.value) return;
  isLoggingOut.value = true;
  try {
    await auth.signOut();
    await router.replace({ name: "login" });
  } finally {
    isLoggingOut.value = false;
  }
}
async function handleAccountCommand(command: "profile" | "security") {
  if (command === "profile") {
    await router.push({ name: "profile" });
    return;
  }
  await router.push({ name: "security" });
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
        <el-dropdown trigger="click" @command="handleAccountCommand">
          <button class="account-summary account-menu-trigger" type="button" aria-label="打开账户菜单">
            <span class="account-avatar" aria-hidden="true">{{ auth.user?.username.slice(0, 1).toUpperCase() }}</span>
            <span class="account-name">{{ auth.user?.username }}</span>
            <small>{{ auth.isAdmin ? "系统管理员" : "企业成员" }}</small>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile"><Settings :size="15" /> 个人资料</el-dropdown-item>
              <el-dropdown-item command="security"><Settings :size="15" /> 账户安全</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button class="sidebar-logout" :icon="LogOut" circle title="退出登录" aria-label="退出登录" :loading="isLoggingOut" @click.stop="handleLogout" />
      </div>
    </aside>
    <main class="app-content">
      <header class="app-topbar">
        <strong>{{ sectionTitle }}</strong>
        <span class="topbar-context">企业知识问答系统</span>
      </header>
      <slot />
    </main>
  </div>
</template>
