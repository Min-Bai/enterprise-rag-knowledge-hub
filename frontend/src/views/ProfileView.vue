<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { updateMyProfile } from "../api/users";
import AppLayout from "../layouts/AppLayout.vue";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const savingProfile = ref(false);
const profile = ref({ username: "", email: "", display_name: "", avatar_url: "", bio: "" });

watch(() => auth.user, (user) => {
  if (!user) return;
  profile.value = { username: user.username, email: user.email ?? "", display_name: user.display_name ?? "", avatar_url: user.avatar_url ?? "", bio: user.bio ?? "" };
}, { immediate: true });

const initials = computed(() => (profile.value.display_name || profile.value.username || "U").slice(0, 1).toUpperCase());

async function saveProfile() {
  if (!auth.token || !profile.value.username.trim()) return;
  savingProfile.value = true;
  try {
    const updated = await updateMyProfile(auth.token, {
      username: profile.value.username.trim(),
      email: profile.value.email.trim() || undefined,
      display_name: profile.value.display_name.trim() || undefined,
      avatar_url: profile.value.avatar_url.trim() || undefined,
      bio: profile.value.bio.trim() || undefined,
    });
    auth.updateCurrentUser(updated);
    ElMessage.success("个人资料已保存");
  } catch (caught) {
    ElMessage.error(caught instanceof Error ? caught.message : "保存个人资料失败。");
  } finally { savingProfile.value = false; }
}

</script>

<template>
  <AppLayout><section class="page-shell profile-page"><header class="page-header"><div><p class="eyebrow">账户中心</p><h1>个人资料</h1><p>维护成员对外显示的信息。</p></div></header><section class="table-surface"><div class="section-heading"><div><p class="eyebrow">公开资料</p><h2>个人信息</h2></div></div><div class="profile-avatar-editor"><el-avatar :size="72" :src="profile.avatar_url || undefined">{{ initials }}</el-avatar><div><strong>{{ profile.display_name || profile.username }}</strong><p>头像可使用 HTTPS 图片链接；未设置时显示名称首字母。</p></div></div><el-form label-position="top" @submit.prevent="saveProfile"><el-form-item label="显示名称"><el-input v-model="profile.display_name" maxlength="80" show-word-limit placeholder="例如：白小明"/></el-form-item><el-form-item label="用户名" required><el-input v-model="profile.username" maxlength="50"/></el-form-item><el-form-item label="邮箱"><el-input v-model="profile.email" type="email"/></el-form-item><el-form-item label="头像链接"><el-input v-model="profile.avatar_url" placeholder="https://example.com/avatar.png"/></el-form-item><el-form-item label="个人简介"><el-input v-model="profile.bio" type="textarea" :rows="4" maxlength="280" show-word-limit placeholder="这段信息会向已登录成员公开。"/></el-form-item><el-button native-type="submit" type="primary" :loading="savingProfile">保存资料</el-button></el-form></section></section></AppLayout>
</template>
