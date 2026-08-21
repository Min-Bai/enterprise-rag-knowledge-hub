<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import {
  BookOpenCheck,
  FileSearch,
  PanelRightOpen,
  Plus,
} from "lucide-vue-next";
import { downloadDocument } from "../api/documents";
import AnswerMessage from "../components/chat/AnswerMessage.vue";
import CitationPanel from "../components/chat/CitationPanel.vue";
import ConversationSidebar from "../components/chat/ConversationSidebar.vue";
import QuestionComposer from "../components/chat/QuestionComposer.vue";
import AppEmpty from "../components/common/AppEmpty.vue";
import AppLayout from "../layouts/AppLayout.vue";
import { useAuthStore } from "../stores/auth";
import { useChatStore } from "../stores/chat";
import { useRoute, useRouter } from "vue-router";
import type { Citation } from "../types/api";

const auth = useAuthStore();
const chat = useChatStore();
const route = useRoute();
const router = useRouter();
const citationsOpen = ref(false);
const messageList = ref<HTMLElement>();
const hasMessages = computed(() => chat.messages.length > 0);

async function scrollToLatestMessage() {
  await nextTick();
  if (messageList.value) messageList.value.scrollTop = messageList.value.scrollHeight;
}

async function restoreConversationFromRoute() {
  const knowledgeBaseId = Number(route.query.knowledge_base_id);
  const conversationId = Number(route.query.conversation_id);
  if (!Number.isInteger(knowledgeBaseId) || !Number.isInteger(conversationId))
    return;
  if (!chat.knowledgeBases.some((item) => item.id === knowledgeBaseId)) return;
  if (chat.selectedKnowledgeBaseId !== knowledgeBaseId)
    await chat.selectKnowledgeBase(knowledgeBaseId);
  if (chat.conversations.some((item) => item.id === conversationId))
    chat.selectConversation(conversationId);
}

async function startConversation() {
  chat.startConversation();
  await router.replace({ name: "chat" });
}

async function selectKnowledgeBase(id: number) {
  await chat.selectKnowledgeBase(id);
  await router.replace({ name: "chat" });
}

onMounted(async () => {
  await chat.initialize();
  await restoreConversationFromRoute();
});

watch(
  () => [route.query.knowledge_base_id, route.query.conversation_id],
  () => {
    if (chat.knowledgeBases.length) void restoreConversationFromRoute();
  },
);

watch(
  () => chat.messages.map((message) => `${message.id}:${message.content.length}`).join("|"),
  () => void scrollToLatestMessage(),
);

async function handleDownload(source: Citation) {
  if (!auth.token) return;
  try {
    await downloadDocument(auth.token, source.document_id, source.filename);
  } catch (error) {
    ElMessage.error(
      error instanceof Error ? error.message : "下载文档失败，请稍后重试。",
    );
  }
}
</script>

<template>
  <AppLayout>
    <section class="chat-page" aria-labelledby="chat-title">
      <header class="chat-page-header">
        <div>
          <p class="eyebrow">智能问答</p>
          <h1 id="chat-title">企业知识问答</h1>
          <p class="page-description">仅基于你已获授权的知识库内容生成回答。</p>
        </div>
        <div class="chat-header-actions">
          <button
            class="icon-button source-toggle"
            type="button"
            title="查看来源证据"
            aria-label="查看来源证据"
            @click="citationsOpen = true"
          >
            <PanelRightOpen :size="18" />
          </button>
          <el-button type="primary" @click="startConversation">
            <Plus :size="16" />新建对话
          </el-button>
        </div>
      </header>

      <el-alert
        v-if="chat.errorMessage"
        class="chat-alert"
        type="error"
        :title="chat.errorMessage"
        show-icon
        :closable="true"
        @close="chat.errorMessage = ''"
      />

      <main class="chat-workspace" :aria-busy="chat.isLoading">
        <ConversationSidebar
          :conversations="chat.conversations"
          :selected-id="chat.selectedConversationId"
          :loading="chat.isLoading"
          @create="startConversation"
          @select="chat.selectConversation"
          @remove="chat.removeConversation"
        />

        <section class="chat-panel" aria-label="当前会话">
          <div class="chat-panel-heading">
            <div>
              <strong>{{
                chat.selectedKnowledgeBase?.name ?? "选择知识库"
              }}</strong>
              <span>当前问答范围</span>
            </div>
          </div>

          <div
            v-if="chat.isLoading"
            class="message-list message-loading"
            aria-label="正在加载会话"
          >
            <el-skeleton :rows="4" animated />
            <el-skeleton :rows="5" animated />
          </div>
          <div v-else-if="hasMessages" ref="messageList" class="message-list" aria-live="polite">
            <AnswerMessage
              v-for="message in chat.messages"
              :key="message.id"
              :message="message"
              @feedback="chat.saveFeedback"
              @show-sources="citationsOpen = true"
            />
          </div>
          <AppEmpty
            v-else
            class="chat-empty"
            title="从企业知识开始提问"
            description="选择知识库后输入问题。回答会显示可追溯的文档来源和页码。"
          >
            <template #icon><FileSearch :size="32" /></template>
          </AppEmpty>

          <QuestionComposer
            :knowledge-bases="chat.knowledgeBases"
            :available-tags="chat.availableTags"
            :selected-knowledge-base-id="chat.selectedKnowledgeBaseId"
            :is-answering="chat.isAnswering"
            :is-stopping="chat.isStopping"
            :is-loading="chat.isLoading"
            @select-knowledge-base="selectKnowledgeBase"
            @submit="chat.ask"
            @stop="chat.stopAnswer"
          />
        </section>

        <CitationPanel
          :sources="chat.activeSources"
          :open="citationsOpen"
          @close="citationsOpen = false"
          @download="handleDownload"
        />
      </main>
      <p class="citation-contract-note">
        <BookOpenCheck
          :size="15"
        />来源信息由知识库检索接口返回；当前接口仅提供文档名、页码和文本块序号。
      </p>
    </section>
  </AppLayout>
</template>
