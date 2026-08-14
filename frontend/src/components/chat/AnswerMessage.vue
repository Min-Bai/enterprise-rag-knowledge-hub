<script setup lang="ts">
import { computed } from "vue";
import DOMPurify from "dompurify";
import MarkdownIt from "markdown-it";
import { Check, Copy, FileText, ThumbsDown, ThumbsUp } from "lucide-vue-next";
import { ElMessage } from "element-plus";
import type { ConversationMessage } from "../../types/api";

const props = defineProps<{
  message: ConversationMessage & { pending?: boolean; local?: boolean };
}>();
const emit = defineEmits<{
  feedback: [messageId: number, value: "helpful" | "unhelpful"];
  showSources: [];
}>();
const markdown = new MarkdownIt({ html: false, linkify: true, breaks: true });
const defaultLinkOpen = markdown.renderer.rules.link_open;
markdown.renderer.rules.link_open = (
  tokens,
  index,
  options,
  environment,
  self,
) => {
  tokens[index].attrSet("target", "_blank");
  tokens[index].attrSet("rel", "noopener noreferrer");
  return defaultLinkOpen
    ? defaultLinkOpen(tokens, index, options, environment, self)
    : self.renderToken(tokens, index, options);
};
const html = computed(() =>
  DOMPurify.sanitize(
    markdown.render(props.message.content || "正在生成回答..."),
    { ALLOWED_ATTR: ["href", "target", "rel"] },
  ),
);

async function copyAnswer() {
  try {
    await navigator.clipboard.writeText(props.message.content);
    ElMessage.success("回答已复制");
  } catch {
    ElMessage.error("复制失败，请手动选择文本复制。");
  }
}
</script>

<template>
  <article
    class="message"
    :class="[`message-${message.role}`, { pending: message.pending }]"
  >
    <header>
      <strong>{{ message.role === "user" ? "你" : "知识助手" }}</strong
      ><span
        v-if="message.pending && message.role === 'assistant'"
        class="streaming-label"
        >正在生成</span
      >
    </header>
    <div
      v-if="message.role === 'assistant'"
      class="markdown-content"
      v-html="html"
    />
    <p v-else>{{ message.content }}</p>
    <footer
      v-if="message.role === 'assistant' && !message.pending"
      class="message-actions"
    >
      <button
        v-if="message.sources?.length"
        class="text-button"
        type="button"
        @click="emit('showSources')"
      >
        <FileText :size="15" />查看 {{ message.sources.length }} 个来源
      </button>
      <button
        class="icon-button light"
        type="button"
        title="复制回答"
        aria-label="复制回答"
        @click="copyAnswer"
      >
        <Copy :size="16" />
      </button>
      <button
        v-if="!message.local"
        class="icon-button light"
        :class="{ selected: message.feedback === 'helpful' }"
        type="button"
        title="回答有帮助"
        aria-label="回答有帮助"
        @click="emit('feedback', message.id, 'helpful')"
      >
        <ThumbsUp :size="16" />
      </button>
      <button
        v-if="!message.local"
        class="icon-button light"
        :class="{ selected: message.feedback === 'unhelpful' }"
        type="button"
        title="回答无帮助"
        aria-label="回答无帮助"
        @click="emit('feedback', message.id, 'unhelpful')"
      >
        <ThumbsDown :size="16" />
      </button>
      <span
        v-if="!message.local && message.feedback === 'helpful'"
        class="feedback-text"
        ><Check :size="14" />已记录反馈</span
      >
    </footer>
  </article>
</template>
