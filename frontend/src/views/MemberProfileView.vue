<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ArrowLeft } from "lucide-vue-next";
import { getPublicUserProfile } from "../api/users";
import AppLayout from "../layouts/AppLayout.vue";
import { useAuthStore } from "../stores/auth";
import { useRoute } from "vue-router";
import type { PublicUserProfile } from "../types/api";

const auth = useAuthStore();
const route = useRoute();
const loading = ref(true);
const error = ref("");
const profile = ref<PublicUserProfile>();
const id = computed(() => Number(route.params.id));
const initials = computed(() => (profile.value?.display_name || profile.value?.username || "U").slice(0, 1).toUpperCase());
onMounted(async () => {
  if (!auth.token) return;
  try { profile.value = await getPublicUserProfile(auth.token, id.value); }
  catch (caught) { error.value = caught instanceof Error ? caught.message : "加载成员资料失败。"; }
  finally { loading.value = false; }
});
</script>

<template>
  <AppLayout><section class="page-shell member-profile-page"><RouterLink class="back-link" to="/app/knowledge-bases"><ArrowLeft :size="15"/> 返回知识库列表</RouterLink><el-skeleton v-if="loading" :rows="5" animated/><el-alert v-else-if="error" type="error" :title="error" show-icon/><section v-else-if="profile" class="table-surface member-profile-card"><el-avatar :size="88" :src="profile.avatar_url || undefined">{{ initials }}</el-avatar><div><p class="eyebrow">企业成员</p><h1>{{ profile.display_name || profile.username }}</h1><p class="member-username">@{{ profile.username }}</p><p class="member-bio">{{ profile.bio || "这位成员暂未填写个人简介。" }}</p></div></section></section></AppLayout>
</template>
