<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
const props = defineProps<{
  knowledgeBaseId: number;
  role: "owner" | "editor" | "viewer" | null;
}>();
const route = useRoute();
const tabs = computed(() => [
  {
    label: "概览",
    path: `/app/knowledge-bases/${props.knowledgeBaseId}`,
  },
  {
    label: "文档管理",
    path: `/app/knowledge-bases/${props.knowledgeBaseId}/documents`,
  },
  {
    label: "检索测试",
    path: `/app/knowledge-bases/${props.knowledgeBaseId}/retrieval-test`,
    hidden: props.role === "viewer",
  },
  {
    label: "高级能力",
    path: `/app/knowledge-bases/${props.knowledgeBaseId}/tools`,
  },
  ...(props.role === "owner"
    ? [
        {
          label: "成员权限",
          path: `/app/knowledge-bases/${props.knowledgeBaseId}/access`,
        },
      ]
    : []),
]);
const visibleTabs = computed(() => tabs.value.filter((tab) => !tab.hidden));
</script>
<template>
  <nav class="knowledge-tabs" aria-label="知识库功能">
    <RouterLink
      v-for="tab in visibleTabs"
      :key="tab.path"
      :to="tab.path"
      :class="{ active: route.path === tab.path || route.path === tab.path.replace('/app', '') }"
      >{{ tab.label }}</RouterLink
    >
  </nav>
</template>
