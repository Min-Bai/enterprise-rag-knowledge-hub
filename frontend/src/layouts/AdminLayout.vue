<script setup lang="ts">
import { BarChart3, BriefcaseBusiness, ClipboardCheck, LogOut, Settings, ShieldCheck, Users } from "lucide-vue-next";
import { useRoute, useRouter } from "vue-router";
import { ref } from "vue";
import { useAdminAuthStore } from "../stores/adminAuth";
const route = useRoute();
const router = useRouter();
const auth = useAdminAuthStore();
const isLoggingOut = ref(false);
const sectionTitle = () => ({
  "/admin/users": "用户管理",
  "/admin/account-requests": "账户审批",
  "/admin/jobs": "任务状态",
  "/admin/analytics": "运行概览",
}[route.path] ?? "系统管理");
async function signOut() { if (isLoggingOut.value) return; isLoggingOut.value = true; try { await auth.signOut(); await router.replace("/admin/login"); } finally { isLoggingOut.value = false; } }
async function handleAccountCommand(command: "profile" | "security") { await router.push({ name: command === "profile" ? "admin-profile" : "admin-security" }); }
</script>

<template>
  <div class="app-layout"><aside class="app-sidebar" aria-label="管理导航"><RouterLink class="brand" to="/admin/users"><span class="brand-mark"><ShieldCheck :size="21" /></span><span>RAG 知识库</span></RouterLink><nav class="primary-nav" aria-label="管理工作区"><RouterLink class="nav-item" :class="{ active: route.path === '/admin/users' }" to="/admin/users"><Users :size="18" />用户管理</RouterLink><RouterLink class="nav-item" :class="{ active: route.path === '/admin/account-requests' }" to="/admin/account-requests"><ClipboardCheck :size="18" />账户审批</RouterLink><RouterLink class="nav-item" :class="{ active: route.path === '/admin/jobs' }" to="/admin/jobs"><BriefcaseBusiness :size="18" />任务状态</RouterLink><RouterLink class="nav-item" :class="{ active: route.path === '/admin/analytics' }" to="/admin/analytics"><BarChart3 :size="18" />运行概览</RouterLink></nav><div class="sidebar-footer"><el-dropdown trigger="click" @command="handleAccountCommand"><button class="account-summary account-menu-trigger" type="button" aria-label="打开管理员账户菜单"><span class="account-avatar" aria-hidden="true">{{ auth.user?.username.slice(0, 1).toUpperCase() }}</span><span class="account-name">{{ auth.user?.display_name || auth.user?.username }}</span><small>系统管理员</small></button><template #dropdown><el-dropdown-menu><el-dropdown-item command="profile"><Settings :size="15" />个人资料</el-dropdown-item><el-dropdown-item command="security"><Settings :size="15" />账户安全</el-dropdown-item></el-dropdown-menu></template></el-dropdown><el-button class="sidebar-logout" :icon="LogOut" circle title="退出管理台" aria-label="退出管理台" :loading="isLoggingOut" @click.stop="signOut" /></div></aside><main class="app-content"><header class="app-topbar"><strong>{{ sectionTitle() }}</strong><div class="topbar-user"><el-tag size="small" type="danger" effect="light">系统管理员</el-tag><span>{{ auth.user?.display_name || auth.user?.username }}</span></div></header><slot /></main></div>
</template>
