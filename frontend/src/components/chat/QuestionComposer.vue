<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { Send, Square } from "lucide-vue-next";
import type { KnowledgeBase } from "../../types/api";

const props = defineProps<{
  knowledgeBases: KnowledgeBase[];
  availableTags: string[];
  selectedKnowledgeBaseId: number | null;
  isAnswering: boolean;
  isStopping: boolean;
  isLoading: boolean;
}>();
const emit = defineEmits<{
  selectKnowledgeBase: [id: number];
  submit: [question: string, tags: string[]];
  stop: [];
}>();
const question = ref("");
const tags = ref<string[]>([]);
const canSubmit = computed(() =>
  Boolean(
    question.value.trim() &&
    props.selectedKnowledgeBaseId &&
    !props.isAnswering &&
    !props.isStopping &&
    !props.isLoading,
  ),
);

function submit() {
  if (!canSubmit.value) return;
  emit("submit", question.value.trim(), tags.value);
  question.value = "";
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key !== "Enter" || event.shiftKey || event.isComposing) return;
  event.preventDefault();
  submit();
}

watch(
  () => props.selectedKnowledgeBaseId,
  () => {
    tags.value = [];
  },
);
</script>

<template>
  <form class="composer" @submit.prevent="submit">
    <div class="composer-controls">
      <el-select
        :model-value="selectedKnowledgeBaseId"
        :disabled="isLoading || isStopping"
        placeholder="选择知识库"
        aria-label="选择知识库"
        @update:model-value="emit('selectKnowledgeBase', Number($event))"
        ><el-option
          v-for="knowledgeBase in knowledgeBases"
          :key="knowledgeBase.id"
          :label="knowledgeBase.name"
          :value="knowledgeBase.id" /></el-select
      ><el-select
        v-model="tags"
        multiple
        collapse-tags
        clearable
        :disabled="isLoading || isStopping || availableTags.length === 0"
        placeholder="按标签筛选（可选）"
        aria-label="按标签筛选"
        ><el-option
          v-for="tag in availableTags"
          :key="tag"
          :label="tag"
          :value="tag"
      /></el-select>
    </div>
    <el-input
      v-model="question"
      type="textarea"
      :disabled="isLoading || isStopping"
      :rows="3"
      maxlength="2000"
      show-word-limit
      placeholder="输入问题，例如：差旅报销的审批流程是什么？"
      aria-label="问题"
      @keydown="handleKeydown"
    />
    <div class="composer-actions">
      <span>Enter 发送，Shift+Enter 换行</span
      ><el-button v-if="isAnswering || isStopping" type="danger" plain :disabled="isStopping" @click="emit('stop')"
        ><Square :size="15" />{{ isStopping ? "正在停止" : "停止生成" }}</el-button
      ><el-button
        v-else
        native-type="submit"
        type="primary"
        :disabled="!canSubmit"
        ><Send :size="15" />发送问题</el-button
      >
    </div>
  </form>
</template>
