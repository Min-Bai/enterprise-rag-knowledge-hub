<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { UserRoundPlus } from "lucide-vue-next";
import { ElMessage } from "element-plus";
import { acceptInvitation, getRegistrationStatus, register } from "../api/auth";
import { useRoute, useRouter } from "vue-router";

const router = useRouter();
const route = useRoute();
const invitationToken = computed(() => typeof route.query.invite === "string" ? route.query.invite : "");
const hasInvitation = computed(() => invitationToken.value.length > 0);
const enabled = ref<boolean | null>(null);
const loading = ref(false);
const errorMessage = ref("");
const form = ref({ username: "", email: "", password: "", confirmPassword: "" });
onMounted(async () => { try { enabled.value = (await getRegistrationStatus()).enabled; } catch { errorMessage.value = "无法读取注册策略，请稍后重试。"; } });
async function submit() {
  if ((!enabled.value && !hasInvitation.value) || form.value.password !== form.value.confirmPassword || form.value.password.length < 6) return;
  loading.value = true; errorMessage.value = "";
  try {
    if (hasInvitation.value) {
      await acceptInvitation({ username: form.value.username.trim(), email: form.value.email.trim(), password: form.value.password, invitation_token: invitationToken.value });
    } else {
      await register({ username: form.value.username.trim(), email: form.value.email.trim() || undefined, password: form.value.password });
    }
    ElMessage.success(hasInvitation.value ? "账号已创建，请登录。" : "注册申请已提交，管理员批准后即可登录。");
    await router.push({ name: "login" });
  } catch (caught) {
    errorMessage.value = caught instanceof Error ? caught.message : "注册申请提交失败，请稍后重试。";
  } finally { loading.value = false; }
}
</script>
<template><main class="login-page"><section class="login-panel" aria-labelledby="register-title"><div class="login-brand"><UserRoundPlus :size="28"/><span>企业知识助手</span></div><h1 id="register-title">{{ hasInvitation ? "接受邀请" : "注册账号" }}</h1><p>{{ hasInvitation ? "请使用收到邀请的邮箱完成账号创建。" : "提交申请后由系统管理员审核并开通账号。" }}</p><el-alert v-if="enabled === false && !hasInvitation" type="info" :closable="false" title="当前未开放注册申请，请联系系统管理员。" class="form-alert"/><el-alert v-else-if="hasInvitation" type="success" :closable="false" title="邀请链接有效时，可直接完成账号创建。" class="form-alert"/><el-alert v-else type="info" :closable="false" title="注册申请需要管理员批准；提交后请等待开通通知。" class="form-alert"/><el-form v-if="enabled !== false || hasInvitation" label-position="top" @submit.prevent="submit"><el-form-item label="用户名" required><el-input v-model="form.username" autocomplete="username" maxlength="50"/></el-form-item><el-form-item label="邮箱" required><el-input v-model="form.email" type="email" autocomplete="email"/></el-form-item><el-form-item label="密码" required><el-input v-model="form.password" type="password" show-password minlength="6" autocomplete="new-password"/></el-form-item><el-form-item label="确认密码" required :error="form.confirmPassword && form.confirmPassword !== form.password ? '两次输入的密码不一致' : ''"><el-input v-model="form.confirmPassword" type="password" show-password autocomplete="new-password"/></el-form-item><el-alert v-if="errorMessage" type="error" :closable="false" :title="errorMessage" class="form-alert"/><el-button class="login-submit" native-type="submit" type="primary" :loading="loading" :disabled="(!enabled && !hasInvitation) || !form.username.trim() || !form.email.trim() || form.password.length < 6 || form.password !== form.confirmPassword">{{ hasInvitation ? "创建账号" : "提交注册申请" }}</el-button></el-form><RouterLink class="login-return-link" to="/login">返回登录</RouterLink></section></main></template>
