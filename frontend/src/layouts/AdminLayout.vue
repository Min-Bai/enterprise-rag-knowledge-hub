<script setup lang="ts">
import { BarChart3, BriefcaseBusiness, LogOut, ShieldCheck, Users } from "lucide-vue-next";
import { useRoute, useRouter } from "vue-router";
import { useAdminAuthStore } from "../stores/adminAuth";
const route = useRoute();
const router = useRouter();
const auth = useAdminAuthStore();
async function signOut() { await auth.signOut(); await router.push("/admin/login"); }
</script>

<template>
  <div class="app-layout">
    <aside class="app-sidebar" aria-label="管理导航">
      <RouterLink class="brand" to="/admin/users"><span class="brand-mark"><ShieldCheck :size="21" /></span><span>企业 RAG 管理台</span></RouterLink>
      <nav class="primary-nav" aria-label="管理工作区">
        <RouterLink class="nav-item" :class="{ active: route.path === '/admin/users' }" to="/admin/users"><Users :size="18" />用户管理</RouterLink>
        <RouterLink class="nav-item" :class="{ active: route.path === '/admin/jobs' }" to="/admin/jobs"><BriefcaseBusiness :size="18" />任务状态</RouterLink>
        <RouterLink class="nav-item" :class="{ active: route.path === '/admin/analytics' }" to="/admin/analytics"><BarChart3 :size="18" />运行概览</RouterLink>
      </nav>
      <div class="sidebar-footer"><RouterLink class="nav-item" to="/app/chat">返回工作台</RouterLink><button class="icon-button" type="button" title="退出管理台" aria-label="退出管理台" @click="signOut"><LogOut :size="18" /></button></div>
    </aside>
    <main class="app-content"><slot /></main>
  </div>
</template>
