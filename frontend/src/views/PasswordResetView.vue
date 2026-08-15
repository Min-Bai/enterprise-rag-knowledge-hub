<script setup lang="ts">
import { computed, ref } from "vue";
import { KeyRound } from "lucide-vue-next";
import { ElMessage } from "element-plus";
import { useRoute, useRouter } from "vue-router";
import { requestPasswordReset, resetPassword } from "../api/auth";

const route = useRoute();
const router = useRouter();
const resetToken = computed(() => typeof route.query.token === "string" ? route.query.token : "");
const password = ref("");
const confirmPassword = ref("");
const email = ref("");
const loading = ref(false);
const errorMessage = ref("");

async function submit() {
  if (!resetToken.value || password.value.length < 6 || password.value !== confirmPassword.value) return;
  loading.value = true;
  errorMessage.value = "";
  try {
    await resetPassword({ reset_token: resetToken.value, new_password: password.value });
    ElMessage.success("密码已重置，请使用新密码登录。");
    await router.replace({ name: "login" });
  } catch (caught) {
    errorMessage.value = caught instanceof Error ? caught.message : "重置失败，请联系系统管理员重新生成链接。";
  } finally { loading.value = false; }
}
async function requestReset() {
  if (!email.value.trim()) return;
  loading.value = true;
  errorMessage.value = "";
  try {
    await requestPasswordReset(email.value.trim());
    ElMessage.success("申请已提交。若邮箱对应有效账号，管理员审核后会提供重置链接。");
  } catch (caught) {
    errorMessage.value = caught instanceof Error ? caught.message : "提交失败，请稍后重试。";
  } finally { loading.value = false; }
}
</script>

<template>
  <main class="login-page"><section class="login-panel" aria-labelledby="password-reset-title"><div class="login-brand"><KeyRound :size="28"/><span>企业知识助手</span></div><h1 id="password-reset-title">重置密码</h1><p v-if="resetToken">设置新密码后，当前账号的其他登录会话将自动失效。</p><p v-else>填写注册邮箱提交重置申请，管理员审核后会通过受控渠道提供限时链接。</p><el-form v-if="resetToken" label-position="top" @submit.prevent="submit"><el-form-item label="新密码" required><el-input v-model="password" type="password" show-password minlength="6" autocomplete="new-password"/></el-form-item><el-form-item label="确认新密码" required :error="confirmPassword && confirmPassword !== password ? '两次输入的密码不一致' : ''"><el-input v-model="confirmPassword" type="password" show-password autocomplete="new-password"/></el-form-item><el-alert v-if="errorMessage" type="error" :closable="false" :title="errorMessage" class="form-alert"/><el-button class="login-submit" native-type="submit" type="primary" :loading="loading" :disabled="password.length < 6 || password !== confirmPassword">确认重置</el-button></el-form><el-form v-else label-position="top" @submit.prevent="requestReset"><el-form-item label="注册邮箱" required><el-input v-model="email" type="email" autocomplete="email"/></el-form-item><el-alert v-if="errorMessage" type="error" :closable="false" :title="errorMessage" class="form-alert"/><el-button class="login-submit" native-type="submit" type="primary" :loading="loading" :disabled="!email.trim()">提交重置申请</el-button></el-form><RouterLink class="login-return-link" to="/login">返回登录</RouterLink></section></main>
</template>
