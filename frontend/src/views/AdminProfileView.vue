<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { updateAdminProfile } from "../api/admin";
import AdminLayout from "../layouts/AdminLayout.vue";
import { useAdminAuthStore } from "../stores/adminAuth";

const auth = useAdminAuthStore();
const saving = ref(false);
const profile = ref({ username: "", email: "", display_name: "", avatar_url: "", bio: "" });
watch(() => auth.user, (user) => {
  if (user) profile.value = { username: user.username, email: user.email ?? "", display_name: user.display_name ?? "", avatar_url: user.avatar_url ?? "", bio: user.bio ?? "" };
}, { immediate: true });
const initials = computed(() => (profile.value.display_name || profile.value.username || "A").slice(0, 1).toUpperCase());
async function saveProfile() {
  if (!auth.token || !profile.value.username.trim()) return;
  saving.value = true;
  try {
    const user = await updateAdminProfile(auth.token, { username: profile.value.username.trim(), email: profile.value.email.trim() || "", display_name: profile.value.display_name.trim() || "", avatar_url: profile.value.avatar_url.trim() || "", bio: profile.value.bio.trim() || "" });
    auth.updateCurrentUser(user);
    ElMessage.success("个人资料已保存");
  } catch (caught) { ElMessage.error(caught instanceof Error ? caught.message : "保存个人资料失败。"); }
  finally { saving.value = false; }
}
</script>
<template><AdminLayout><section class="page-shell profile-page"><header class="page-header"><div><p class="eyebrow">管理员账户</p><h1>个人资料</h1><p>维护管理端显示的身份信息。</p></div></header><section class="table-surface"><div class="section-heading"><div><p class="eyebrow">公开资料</p><h2>个人信息</h2></div></div><div class="profile-avatar-editor"><el-avatar :size="72" :src="profile.avatar_url || undefined">{{ initials }}</el-avatar><div><strong>{{ profile.display_name || profile.username }}</strong><p>未设置头像时显示名称首字母。</p></div></div><el-form label-position="top" @submit.prevent="saveProfile"><el-form-item label="显示名称"><el-input v-model="profile.display_name" maxlength="80" show-word-limit/></el-form-item><el-form-item label="用户名" required><el-input v-model="profile.username" maxlength="50"/></el-form-item><el-form-item label="邮箱"><el-input v-model="profile.email" type="email"/></el-form-item><el-form-item label="头像链接"><el-input v-model="profile.avatar_url" placeholder="https://example.com/avatar.png"/></el-form-item><el-form-item label="个人简介"><el-input v-model="profile.bio" type="textarea" :rows="4" maxlength="280" show-word-limit/></el-form-item><el-button native-type="submit" type="primary" :loading="saving">保存资料</el-button></el-form></section></section></AdminLayout></template>
