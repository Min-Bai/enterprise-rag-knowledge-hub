<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { ShieldCheck } from "lucide-vue-next";
import { useAdminAuthStore } from "../stores/adminAuth";

const username = ref("");
const password = ref("");
const errorMessage = ref("");
const auth = useAdminAuthStore();
const router = useRouter();

async function submit() {
  errorMessage.value = "";
  try {
    await auth.signIn(username.value, password.value);
    await router.push({ name: "admin-users" });
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "登录失败，请稍后重试。";
  }
}
</script>

<template>
  <main class="login-page admin-login-page">
    <section class="login-panel" aria-labelledby="admin-login-title">
      <div class="login-brand"><ShieldCheck :size="28" /><span>企业 RAG 管理台</span></div>
      <h1 id="admin-login-title">管理员登录</h1>
      <p>使用管理员账号管理用户访问、文档任务和系统运行状态。</p>
      <el-form label-position="top" @submit.prevent="submit">
        <el-form-item label="账号"><el-input v-model="username" autocomplete="username" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="password" type="password" show-password autocomplete="current-password" /></el-form-item>
        <el-alert v-if="errorMessage" class="form-alert" type="error" :closable="false" :title="errorMessage" />
        <el-button class="login-submit" native-type="submit" type="primary" :loading="auth.isLoading">登录管理台</el-button>
      </el-form>
      <RouterLink class="login-return-link" to="/login">返回用户工作台登录</RouterLink>
    </section>
  </main>
</template>
