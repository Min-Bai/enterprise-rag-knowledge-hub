<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAdminAuthStore } from "../stores/adminAuth";
const username = ref(""); const password = ref(""); const error = ref(""); const auth = useAdminAuthStore(); const router = useRouter();
async function submit() { error.value = ""; try { await auth.signIn(username.value, password.value); await router.push("/admin/users"); } catch (cause) { error.value = cause instanceof Error ? cause.message : "登录失败"; } }
</script>
<template><main class="login-page"><section class="login-panel"><h1>企业 RAG 管理台</h1><p>仅系统管理员可访问</p><form @submit.prevent="submit"><label>账号<input v-model="username" autocomplete="username" required /></label><label>密码<input v-model="password" type="password" autocomplete="current-password" required /></label><p v-if="error" class="form-error">{{ error }}</p><button type="submit" :disabled="auth.isLoading">{{ auth.isLoading ? "登录中" : "管理员登录" }}</button></form></section></main></template>
