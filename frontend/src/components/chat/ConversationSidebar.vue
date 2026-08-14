<script setup lang="ts">
import { MessageSquare, Plus, Trash2 } from "lucide-vue-next";
import type { Conversation } from "../../types/api";

defineProps<{
  conversations: Conversation[];
  selectedId: number | null;
  loading: boolean;
}>();
const emit = defineEmits<{
  select: [id: number];
  create: [];
  remove: [id: number];
}>();

function getTitle(conversation: Conversation) {
  const question = conversation.messages
    .find((message) => message.role === "user")
    ?.content.trim();
  if (!question) return "未命名对话";
  return question.length > 26 ? `${question.slice(0, 26)}...` : question;
}
</script>

<template>
  <aside class="conversation-panel" aria-label="会话历史">
    <div class="panel-toolbar">
      <strong>会话历史</strong
      ><button
        class="icon-button"
        type="button"
        title="新建对话"
        aria-label="新建对话"
        @click="emit('create')"
      >
        <Plus :size="17" />
      </button>
    </div>
    <el-skeleton
      v-if="loading"
      :rows="5"
      animated
      class="conversation-skeleton"
    />
    <div v-else-if="conversations.length === 0" class="empty-list">
      还没有历史对话。
    </div>
    <ul v-else class="conversation-list">
      <li
        v-for="conversation in conversations"
        :key="conversation.id"
        :class="{ active: selectedId === conversation.id }"
      >
        <button
          class="conversation-select"
          type="button"
          @click="emit('select', conversation.id)"
        >
          <MessageSquare :size="16" /><span>{{ getTitle(conversation) }}</span>
        </button>
        <el-popconfirm
          title="删除后无法恢复此对话，确定继续吗？"
          confirm-button-text="删除"
          cancel-button-text="取消"
          @confirm="emit('remove', conversation.id)"
          ><template #reference
            ><button
              class="icon-button conversation-more"
              type="button"
              title="删除对话"
              :aria-label="`删除对话：${getTitle(conversation)}`"
            >
              <Trash2 :size="15" /></button></template
        ></el-popconfirm>
      </li>
    </ul>
  </aside>
</template>
