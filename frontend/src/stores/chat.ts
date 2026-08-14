import { computed, ref } from "vue";
import { defineStore } from "pinia";
import {
  deleteConversation,
  getKnowledgeBaseConversations,
  streamKnowledgeBaseAnswer,
  submitFeedback,
} from "../api/chat";
import { getKnowledgeBases } from "../api/knowledgeBases";
import { getDocuments } from "../api/documents";
import type {
  Citation,
  Conversation,
  ConversationMessage,
  KnowledgeBase,
} from "../types/api";
import { useAuthStore } from "./auth";

type PendingMessage = ConversationMessage & {
  pending?: boolean;
  local?: boolean;
};

export const useChatStore = defineStore("chat", () => {
  const auth = useAuthStore();
  const knowledgeBases = ref<KnowledgeBase[]>([]);
  const availableTags = ref<string[]>([]);
  const selectedKnowledgeBaseId = ref<number | null>(null);
  const conversations = ref<Conversation[]>([]);
  const selectedConversationId = ref<number | null>(null);
  const pendingMessages = ref<PendingMessage[]>([]);
  const activeSources = ref<Citation[]>([]);
  const isLoading = ref(false);
  const isAnswering = ref(false);
  const errorMessage = ref("");
  let abortController: AbortController | null = null;

  const selectedConversation = computed(
    () =>
      conversations.value.find(
        (item) => item.id === selectedConversationId.value,
      ) ?? null,
  );
  const messages = computed<PendingMessage[]>(() =>
    pendingMessages.value.length
      ? pendingMessages.value
      : (selectedConversation.value?.messages ?? []),
  );
  const selectedKnowledgeBase = computed(
    () =>
      knowledgeBases.value.find(
        (item) => item.id === selectedKnowledgeBaseId.value,
      ) ?? null,
  );

  async function initialize() {
    if (!auth.token) return;
    isLoading.value = true;
    errorMessage.value = "";
    try {
      knowledgeBases.value = await getKnowledgeBases(auth.token);
      if (!selectedKnowledgeBaseId.value && knowledgeBases.value[0])
        selectedKnowledgeBaseId.value = knowledgeBases.value[0].id;
      if (selectedKnowledgeBaseId.value) await loadConversations();
      await loadTags();
    } catch (error) {
      errorMessage.value =
        error instanceof Error
          ? error.message
          : "加载问答工作台失败，请稍后重试。";
    } finally {
      isLoading.value = false;
    }
  }

  async function selectKnowledgeBase(id: number) {
    if (selectedKnowledgeBaseId.value === id && conversations.value.length)
      return;
    isLoading.value = true;
    try {
      selectedKnowledgeBaseId.value = id;
      selectedConversationId.value = null;
      pendingMessages.value = [];
      activeSources.value = [];
      await loadConversations();
      await loadTags();
    } finally {
      isLoading.value = false;
    }
  }

  async function loadTags() {
    if (!auth.token || !selectedKnowledgeBaseId.value) return;
    try {
      const documents = await getDocuments(
        auth.token,
        selectedKnowledgeBaseId.value,
      );
      availableTags.value = [
        ...new Set(documents.flatMap((document) => document.tags)),
      ].sort();
    } catch {
      availableTags.value = [];
    }
  }

  async function loadConversations() {
    if (!auth.token || !selectedKnowledgeBaseId.value) return;
    try {
      conversations.value = await getKnowledgeBaseConversations(
        auth.token,
        selectedKnowledgeBaseId.value,
      );
    } catch (error) {
      conversations.value = [];
      errorMessage.value =
        error instanceof Error ? error.message : "加载会话失败，请稍后重试。";
    }
  }

  function startConversation() {
    selectedConversationId.value = null;
    pendingMessages.value = [];
    activeSources.value = [];
    errorMessage.value = "";
  }

  function selectConversation(conversationId: number) {
    selectedConversationId.value = conversationId;
    pendingMessages.value = [];
    const assistantMessages =
      selectedConversation.value?.messages.filter(
        (message) => message.role === "assistant",
      ) ?? [];
    activeSources.value =
      assistantMessages[assistantMessages.length - 1]?.sources ?? [];
  }

  async function ask(question: string, tags: string[]) {
    if (!auth.token || !selectedKnowledgeBaseId.value || isAnswering.value)
      return;
    const userMessage: PendingMessage = {
      id: -Date.now(),
      role: "user",
      content: question,
      sources: null,
      feedback: null,
      feedback_comment: null,
      created_at: new Date().toISOString(),
      pending: true,
      local: true,
    };
    const assistantMessage: PendingMessage = {
      id: userMessage.id - 1,
      role: "assistant",
      content: "",
      sources: [],
      feedback: null,
      feedback_comment: null,
      created_at: new Date().toISOString(),
      pending: true,
      local: true,
    };
    pendingMessages.value = [...messages.value, userMessage, assistantMessage];
    activeSources.value = [];
    errorMessage.value = "";
    isAnswering.value = true;
    abortController = new AbortController();
    try {
      await streamKnowledgeBaseAnswer(
        auth.token,
        {
          knowledge_base_id: selectedKnowledgeBaseId.value,
          question,
          conversation_id: selectedConversationId.value ?? undefined,
          tags,
        },
        {
          onMetadata: ({ conversation_id, sources }) => {
            selectedConversationId.value = conversation_id;
            activeSources.value = sources;
            pendingMessages.value = pendingMessages.value.map((message) =>
              message.id === assistantMessage.id
                ? { ...message, sources }
                : message,
            );
          },
          onToken: (text) => {
            pendingMessages.value = pendingMessages.value.map((message) =>
              message.id === assistantMessage.id
                ? { ...message, content: message.content + text }
                : message,
            );
          },
        },
        abortController.signal,
      );
      await loadConversations();
      pendingMessages.value = [];
    } catch (error) {
      const wasStopped = (error as DOMException).name === "AbortError";
      pendingMessages.value = pendingMessages.value.map((message) =>
        message.id === assistantMessage.id
          ? {
              ...message,
              pending: false,
              content:
                message.content ||
                (wasStopped ? "已停止生成。" : "回答生成失败，请重新提问。"),
            }
          : message,
      );
      if (!wasStopped)
        errorMessage.value =
          error instanceof Error ? error.message : "生成回答失败，请稍后重试。";
    } finally {
      isAnswering.value = false;
      abortController = null;
    }
  }

  function stopAnswer() {
    abortController?.abort();
  }

  async function removeConversation(conversationId: number) {
    if (!auth.token) return;
    try {
      await deleteConversation(auth.token, conversationId);
      conversations.value = conversations.value.filter(
        (item) => item.id !== conversationId,
      );
      if (selectedConversationId.value === conversationId) startConversation();
    } catch (error) {
      errorMessage.value =
        error instanceof Error ? error.message : "删除会话失败，请稍后重试。";
    }
  }

  async function saveFeedback(
    messageId: number,
    feedback: "helpful" | "unhelpful",
  ) {
    if (!auth.token) return;
    try {
      const updated = await submitFeedback(auth.token, messageId, feedback);
      const conversation = selectedConversation.value;
      if (!conversation) return;
      conversation.messages = conversation.messages.map((message) =>
        message.id === messageId ? updated : message,
      );
    } catch (error) {
      errorMessage.value =
        error instanceof Error ? error.message : "保存反馈失败，请稍后重试。";
    }
  }

  return {
    knowledgeBases,
    availableTags,
    selectedKnowledgeBaseId,
    selectedKnowledgeBase,
    conversations,
    selectedConversationId,
    selectedConversation,
    messages,
    activeSources,
    isLoading,
    isAnswering,
    errorMessage,
    initialize,
    selectKnowledgeBase,
    selectConversation,
    startConversation,
    ask,
    stopAnswer,
    removeConversation,
    saveFeedback,
  };
});
