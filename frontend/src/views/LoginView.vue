<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { BotMessageSquare } from "lucide-vue-next";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const router = useRouter();
const username = ref("");
const password = ref("");
const errorMessage = ref("");

async function submit() {
  errorMessage.value = "";
  try {
    await auth.signIn(username.value, password.value);
    await router.push({ name: "chat" });
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : "登录失败，请稍后重试。";
  }
}
</script>

<template>
  <main class="login-page">
    <section class="login-panel" aria-labelledby="login-title">
      <div class="login-brand">
        <BotMessageSquare :size="28" /><span>企业知识助手</span>
      </div>
      <h1 id="login-title">登录工作台</h1>
      <p>访问已授权的企业知识库并获取可追溯的回答。</p>
      <el-form label-position="top" @submit.prevent="submit">
        <el-form-item label="用户名"
          ><el-input v-model="username" autocomplete="username"
        /></el-form-item>
        <el-form-item label="密码"
          ><el-input
            v-model="password"
            type="password"
            show-password
            autocomplete="current-password"
        /></el-form-item>
        <el-alert
          v-if="errorMessage"
          class="form-alert"
          type="error"
          :closable="false"
          :title="errorMessage"
        />
        <el-button
          class="login-submit"
          native-type="submit"
          type="primary"
          :loading="auth.isLoading"
          >登录</el-button
        >
      </el-form>
    </section>
  </main>
</template>
