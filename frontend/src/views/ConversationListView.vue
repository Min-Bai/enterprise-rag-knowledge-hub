<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { MessageSquarePlus } from "lucide-vue-next";
import { deleteConversation, getKnowledgeBaseConversations } from "../api/chat";
import { getKnowledgeBases } from "../api/knowledgeBases";
import AppEmpty from "../components/common/AppEmpty.vue";
import AppLayout from "../layouts/AppLayout.vue";
import { useAuthStore } from "../stores/auth";
import type { Conversation, KnowledgeBase } from "../types/api";
const auth = useAuthStore();
const knowledgeBases = ref<KnowledgeBase[]>([]);
const selectedId = ref<number | null>(null);
const conversations = ref<Conversation[]>([]);
const loading = ref(true);
const error = ref("");
const selectedKnowledgeBase = computed(() =>
  knowledgeBases.value.find((item) => item.id === selectedId.value),
);
function title(item: Conversation) {
  const question = item.messages
    .find((message) => message.role === "user")
    ?.content.trim();
  return question
    ? question.length > 70
      ? `${question.slice(0, 70)}...`
      : question
    : "未命名对话";
}
function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
async function loadConversations() {
  if (!auth.token || !selectedId.value) return;
  loading.value = true;
  error.value = "";
  try {
    conversations.value = await getKnowledgeBaseConversations(
      auth.token,
      selectedId.value,
    );
  } catch (caught) {
    error.value =
      caught instanceof Error ? caught.message : "加载会话失败，请稍后重试。";
  } finally {
    loading.value = false;
  }
}
async function initialize() {
  if (!auth.token) return;
  loading.value = true;
  try {
    knowledgeBases.value = await getKnowledgeBases(auth.token);
    selectedId.value = knowledgeBases.value[0]?.id ?? null;
    if (selectedId.value) await loadConversations();
  } catch (caught) {
    error.value =
      caught instanceof Error
        ? caught.message
        : "加载会话记录失败，请稍后重试。";
    loading.value = false;
  }
}
async function remove(item: Conversation) {
  if (!auth.token) return;
  try {
    await deleteConversation(auth.token, item.id);
    conversations.value = conversations.value.filter(
      (current) => current.id !== item.id,
    );
    ElMessage.success("会话已删除");
  } catch (caught) {
    ElMessage.error(
      caught instanceof Error ? caught.message : "删除会话失败，请稍后重试。",
    );
  }
}
onMounted(initialize);
</script>
<template>
  <AppLayout
    ><section class="page-shell">
      <header class="page-header">
        <div>
          <p class="eyebrow">会话记录</p>
          <h1>历史会话</h1>
          <p>按知识库查看和管理历史问答，删除后无法恢复。</p>
        </div>
        <RouterLink to="/chat"
          ><el-button type="primary"
            ><MessageSquarePlus :size="16" />新建问答</el-button
          ></RouterLink
        >
      </header>
      <section class="table-surface">
        <div class="table-toolbar">
          <el-select
            v-model="selectedId"
            aria-label="选择知识库"
            @change="loadConversations"
            ><el-option
              v-for="item in knowledgeBases"
              :key="item.id"
              :label="item.name"
              :value="item.id" /></el-select
          ><span v-if="selectedKnowledgeBase" class="table-secondary"
            >当前范围：{{ selectedKnowledgeBase.name }}</span
          >
        </div>
        <el-alert
          v-if="error"
          type="error"
          :title="error"
          show-icon
          class="form-alert"
        /><el-skeleton v-if="loading" :rows="6" animated /><AppEmpty
          v-else-if="!selectedId"
          title="还没有可访问的知识库"
          description="创建或加入知识库后即可查看其中的会话记录。"
        /><AppEmpty
          v-else-if="conversations.length === 0"
          title="该知识库还没有会话"
          description="在智能问答中发起问题后，会话会显示在这里。"
        /><el-table v-else :data="conversations"
          ><el-table-column label="首个问题" min-width="360"
            ><template #default="{ row }"
              ><RouterLink
                class="table-link"
                :to="{
                  name: 'chat',
                  query: {
                    knowledge_base_id: String(selectedId),
                    conversation_id: String(row.id),
                  },
                }"
                >{{ title(row) }}</RouterLink
              ></template
            ></el-table-column
          ><el-table-column label="消息数" width="100"
            ><template #default="{ row }">{{
              row.messages.length
            }}</template></el-table-column
          ><el-table-column label="最后更新" min-width="165"
            ><template #default="{ row }">{{
              formatDate(row.updated_at)
            }}</template></el-table-column
          ><el-table-column label="操作" width="100"
            ><template #default="{ row }"
              ><el-popconfirm
                title="删除后无法恢复，确定继续吗？"
                confirm-button-text="删除"
                cancel-button-text="取消"
                @confirm="remove(row)"
                ><template #reference
                  ><el-button link type="danger">删除</el-button></template
                ></el-popconfirm
              ></template
            ></el-table-column
          ></el-table
        >
      </section>
    </section></AppLayout
  >
</template>
