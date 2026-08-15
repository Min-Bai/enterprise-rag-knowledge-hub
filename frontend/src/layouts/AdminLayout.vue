<script setup lang="ts">
import { BarChart3, BriefcaseBusiness, LogOut, Settings, ShieldCheck, Users } from "lucide-vue-next";
import { useRoute, useRouter } from "vue-router";
import { useAdminAuthStore } from "../stores/adminAuth";
const route = useRoute();
const router = useRouter();
const auth = useAdminAuthStore();
async function signOut() { await auth.signOut(); await router.push("/admin/login"); }
async function handleAccountCommand(command: "profile" | "logout") { if (command === "profile") await router.push({ name: "admin-profile" }); else await signOut(); }
</script>

<template>
  <div class="app-layout"><aside class="app-sidebar" aria-label="管理导航"><RouterLink class="brand" to="/admin/users"><span class="brand-mark"><ShieldCheck :size="21" /></span><span>企业 RAG 管理台</span></RouterLink><nav class="primary-nav" aria-label="管理工作区"><RouterLink class="nav-item" :class="{ active: route.path === '/admin/users' }" to="/admin/users"><Users :size="18" />用户管理</RouterLink><RouterLink class="nav-item" :class="{ active: route.path === '/admin/jobs' }" to="/admin/jobs"><BriefcaseBusiness :size="18" />任务状态</RouterLink><RouterLink class="nav-item" :class="{ active: route.path === '/admin/analytics' }" to="/admin/analytics"><BarChart3 :size="18" />运行概览</RouterLink></nav><div class="sidebar-footer"><el-dropdown trigger="click" @command="handleAccountCommand"><button class="account-summary account-menu-trigger" type="button" aria-label="打开管理员账户菜单"><span class="account-avatar" aria-hidden="true">{{ auth.user?.username.slice(0, 1).toUpperCase() }}</span><span class="account-name">{{ auth.user?.display_name || auth.user?.username }}</span><small>系统管理员</small></button><template #dropdown><el-dropdown-menu><el-dropdown-item command="profile"><Settings :size="15" />个人资料与安全</el-dropdown-item><el-dropdown-item command="logout" divided><LogOut :size="15" />退出管理台</el-dropdown-item></el-dropdown-menu></template></el-dropdown></div></aside><main class="app-content"><slot /></main></div>
</template>
