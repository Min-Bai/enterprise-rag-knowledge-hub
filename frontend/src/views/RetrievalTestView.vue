<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { Search } from "lucide-vue-next";
import { getDocuments, searchDocuments } from "../api/documents";
import { getKnowledgeBases } from "../api/knowledgeBases";
import AppEmpty from "../components/common/AppEmpty.vue";
import AppLayout from "../layouts/AppLayout.vue";
import KnowledgeBaseTabs from "../components/knowledge-base/KnowledgeBaseTabs.vue";
import { useAuthStore } from "../stores/auth";
import { useRoute } from "vue-router";
import type { DocumentChunk } from "../types/api";

const route = useRoute();
const auth = useAuthStore();
const question = ref("");
const tags = ref<string[]>([]);
const availableTags = ref<string[]>([]);
const results = ref<DocumentChunk[]>([]);
const loading = ref(false);
const knowledgeBaseId = computed(() => Number(route.params.id));
const knowledgeBaseRole = ref<"owner" | "editor" | "viewer" | null>(null);
onMounted(async () => {
  if (!auth.token) return;
  try {
    const [documents, knowledgeBases] = await Promise.all([
      getDocuments(auth.token, knowledgeBaseId.value),
      getKnowledgeBases(auth.token),
    ]);
    knowledgeBaseRole.value =
      knowledgeBases.find((item) => item.id === knowledgeBaseId.value)?.role ??
      null;
    availableTags.value = [
      ...new Set(documents.flatMap((document) => document.tags)),
    ].sort();
  } catch {
    ElMessage.error("加载文档标签失败，请稍后重试。");
  }
});
async function search() {
  if (!auth.token || question.value.trim().length < 2) return;
  loading.value = true;
  try {
    results.value = (
      await searchDocuments(auth.token, knowledgeBaseId.value, {
        question: question.value.trim(),
        tags: tags.value,
      })
    ).items;
  } catch (caught) {
    ElMessage.error(
      caught instanceof Error ? caught.message : "检索测试失败，请稍后重试。",
    );
  } finally {
    loading.value = false;
  }
}
</script>
<template>
  <AppLayout
    ><section class="page-shell" aria-labelledby="retrieval-title">
      <header class="page-header">
        <div>
          <p class="eyebrow">知识库质量</p>
          <h1 id="retrieval-title">检索测试</h1>
          <p>仅用于验证知识库的召回结果，不会生成 AI 回答。</p>
        </div>
      </header>
      <KnowledgeBaseTabs
        :knowledge-base-id="knowledgeBaseId"
        :role="knowledgeBaseRole"
      />
      <section class="table-surface">
        <form class="retrieval-form" @submit.prevent="search">
          <el-input
            v-model="question"
            maxlength="300"
            placeholder="输入至少两个字的问题"
            aria-label="检索问题"
          /><el-select
            v-model="tags"
            multiple
            clearable
            collapse-tags
            placeholder="按标签筛选（可选）"
            aria-label="标签筛选"
            ><el-option
              v-for="tag in availableTags"
              :key="tag"
              :label="tag"
              :value="tag" /></el-select
          ><el-button
            native-type="submit"
            type="primary"
            :loading="loading"
            :disabled="question.trim().length < 2"
            ><Search :size="16" />开始检索</el-button
          >
        </form>
        <el-skeleton v-if="loading" :rows="6" animated /><AppEmpty
          v-else-if="results.length === 0"
          title="尚无检索结果"
          description="输入问题并开始检索，结果会显示命中的文档块和相似度分数。"
        />
        <ol v-else class="retrieval-results">
          <li
            v-for="item in results"
            :key="`${item.document_id}-${item.chunk_index}`"
          >
            <header>
              <strong>{{ item.filename }}</strong
              ><el-tag effect="plain">分数 {{ item.score.toFixed(3) }}</el-tag>
            </header>
            <p>
              文本块 {{ item.chunk_index
              }}<span v-if="item.page"> · 第 {{ item.page }} 页</span>
            </p>
            <blockquote>{{ item.text }}</blockquote>
          </li>
        </ol>
      </section>
    </section></AppLayout
  >
</template>
