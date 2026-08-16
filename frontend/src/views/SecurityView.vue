<script setup lang="ts">
import { ref } from "vue";
import { ElMessage } from "element-plus";
import { ShieldCheck } from "lucide-vue-next";
import { changeMyPassword } from "../api/users";
import AppLayout from "../layouts/AppLayout.vue";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const saving = ref(false);
const form = ref({ old_password: "", new_password: "", confirm_password: "" });
async function save() {
  if (!auth.token || form.value.new_password.length < 6 || form.value.new_password !== form.value.confirm_password) return;
  saving.value = true;
  try { await changeMyPassword(auth.token, { old_password: form.value.old_password, new_password: form.value.new_password }); await auth.signOut(); ElMessage.success("密码已更新，请使用新密码登录。"); }
  catch (caught) { ElMessage.error(caught instanceof Error ? caught.message : "修改密码失败。"); }
  finally { saving.value = false; }
}
</script>
<template><AppLayout><section class="page-shell profile-page"><header class="page-header"><div><p class="eyebrow">账户中心</p><h1>账户安全</h1><p>修改密码后，当前账号的所有登录会话都会失效。</p></div></header><section class="table-surface security-surface"><div class="section-heading"><h2>修改密码</h2><ShieldCheck :size="20"/></div><el-form label-position="top" @submit.prevent="save"><el-form-item label="当前密码"><el-input v-model="form.old_password" type="password" show-password autocomplete="current-password"/></el-form-item><el-form-item label="新密码"><el-input v-model="form.new_password" type="password" show-password minlength="6" autocomplete="new-password"/></el-form-item><el-form-item label="确认新密码" :error="form.confirm_password && form.confirm_password !== form.new_password ? '两次输入的密码不一致' : ''"><el-input v-model="form.confirm_password" type="password" show-password autocomplete="new-password"/></el-form-item><el-button native-type="submit" type="primary" :loading="saving" :disabled="form.new_password.length < 6 || form.new_password !== form.confirm_password">更新密码</el-button></el-form></section></section></AppLayout></template>
