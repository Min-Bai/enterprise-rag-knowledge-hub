<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { ArrowLeft, FileText, Search, Shield, Upload } from "lucide-vue-next";
import { getDocuments } from "../api/documents";
import { getKnowledgeBases } from "../api/knowledgeBases";
import AppEmpty from "../components/common/AppEmpty.vue";
import DocumentStatusTag from "../components/common/DocumentStatusTag.vue";
import KnowledgeBaseTabs from "../components/knowledge-base/KnowledgeBaseTabs.vue";
import AppLayout from "../layouts/AppLayout.vue";
import { useAuthStore } from "../stores/auth";
import { useRoute } from "vue-router";
import type { DocumentItem, KnowledgeBase } from "../types/api";

const route = useRoute();
const auth = useAuthStore();
const knowledgeBase = ref<KnowledgeBase | null>(null);
const documents = ref<DocumentItem[]>([]);
const loading = ref(true);
const error = ref("");
const id = computed(() => Number(route.params.id));

const readyCount = computed(
  () => documents.value.filter((item) => item.status === "ready").length,
);
const processingCount = computed(
  () =>
    documents.value.filter(
      (item) => item.status === "uploaded" || item.status === "processing",
    ).length,
);
const failedCount = computed(
  () => documents.value.filter((item) => item.status === "failed").length,
);
const chunkCount = computed(() =>
  documents.value.reduce((total, item) => total + item.chunk_count, 0),
);
const latestDocument = computed(
  () =>
    [...documents.value].sort((left, right) =>
      right.created_at.localeCompare(left.created_at),
    )[0],
);

async function load() {
  if (!auth.token) return;
  loading.value = true;
  error.value = "";
  try {
    const [knowledgeBases, loadedDocuments] = await Promise.all([
      getKnowledgeBases(auth.token),
      getDocuments(auth.token, id.value, 100),
    ]);
    knowledgeBase.value =
      knowledgeBases.find((item) => item.id === id.value) ?? null;
    documents.value = loadedDocuments;
    if (!knowledgeBase.value) error.value = "没有找到可访问的知识库。";
  } catch (caught) {
    error.value =
      caught instanceof Error
        ? caught.message
        : "加载知识库概览失败，请稍后重试。";
  } finally {
    loading.value = false;
  }
}

function formatDate(value?: string | null) {
  if (!value) return "暂无";
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function roleLabel(role: KnowledgeBase["role"]) {
  return { owner: "所有者", editor: "编辑者", viewer: "只读成员" }[role];
}

function rolePermission(role: KnowledgeBase["role"]) {
  return {
    owner: "当前权限：所有者，可管理成员、文档与检索测试。",
    editor: "当前权限：编辑者，可上传、编辑、删除文档和执行检索测试。",
    viewer: "当前权限：查看者，可浏览、检索和问答，不能修改文档或成员。",
  }[role];
}

onMounted(load);
</script>

<template>
  <AppLayout>
    <section class="page-shell" aria-labelledby="knowledge-base-overview-title">
      <header class="page-header">
        <div>
          <RouterLink class="back-link" to="/app/knowledge-bases">
            <ArrowLeft :size="15" /> 返回知识库列表
          </RouterLink>
          <p class="eyebrow">知识库概览</p>
          <h1 id="knowledge-base-overview-title">
            {{ knowledgeBase?.name ?? "加载中" }}
          </h1>
          <p>{{ knowledgeBase?.description || "暂无描述。" }}</p>
        </div>
        <div class="page-header-actions" v-if="knowledgeBase">
          <RouterLink :to="`/app/knowledge-bases/${id}/documents`">
            <el-button type="primary"
              ><FileText :size="16" />管理文档</el-button
            >
          </RouterLink>
        </div>
      </header>

      <KnowledgeBaseTabs
        v-if="knowledgeBase"
        :knowledge-base-id="id"
        :role="knowledgeBase.role"
      />
      <el-alert
        v-if="error"
        class="form-alert"
        type="error"
        :title="error"
        show-icon
      />

      <el-skeleton v-if="loading" :rows="8" animated />
      <template v-else-if="knowledgeBase">
        <section class="overview-grid" aria-label="知识库状态摘要">
          <section class="table-surface overview-summary">
            <div class="section-heading">
              <div>
                <p class="eyebrow">当前状态</p>
                <h2>解析与检索概况</h2>
              </div>
              <el-tag effect="plain">{{
                roleLabel(knowledgeBase.role)
              }}</el-tag>
            </div>
            <dl class="overview-metrics">
              <div>
                <dt>已加载文档</dt>
                <dd>{{ documents.length }}</dd>
              </div>
              <div>
                <dt>解析完成</dt>
                <dd>{{ readyCount }}</dd>
              </div>
              <div>
                <dt>处理中</dt>
                <dd>{{ processingCount }}</dd>
              </div>
              <div>
                <dt>处理失败</dt>
                <dd>{{ failedCount }}</dd>
              </div>
              <div>
                <dt>已生成分段</dt>
                <dd>{{ chunkCount }}</dd>
              </div>
              <div>
                <dt>最近上传</dt>
                <dd>{{ formatDate(latestDocument?.created_at) }}</dd>
              </div>
            </dl>
            <p class="contract-note">
              统计基于当前接口返回的最多 100
              份文档，后端暂未提供知识库聚合总数接口。
            </p>
            <p class="role-permission">{{ rolePermission(knowledgeBase.role) }}</p>
          </section>

          <section class="table-surface overview-actions">
            <div class="section-heading">
              <div>
                <p class="eyebrow">常用操作</p>
                <h2>进入工作区</h2>
              </div>
            </div>
            <RouterLink :to="`/app/knowledge-bases/${id}/documents`">
              <el-button plain><Upload :size="16" />上传或管理文档</el-button>
            </RouterLink>
            <RouterLink
              v-if="
                knowledgeBase.role === 'owner' ||
                knowledgeBase.role === 'editor'
              "
              :to="`/app/knowledge-bases/${id}/retrieval-test`"
            >
              <el-button plain><Search :size="16" />检索质量测试</el-button>
            </RouterLink>
            <RouterLink
              v-if="knowledgeBase.role === 'owner'"
              :to="`/app/knowledge-bases/${id}/access`"
            >
              <el-button plain><Shield :size="16" />成员与权限</el-button>
            </RouterLink>
          </section>
        </section>

        <section class="table-surface overview-recent">
          <div class="section-heading">
            <div>
              <p class="eyebrow">最近数据</p>
              <h2>文档处理状态</h2>
            </div>
            <RouterLink
              class="table-link"
              :to="`/app/knowledge-bases/${id}/documents`"
            >
              查看全部文档
            </RouterLink>
          </div>
          <AppEmpty
            v-if="documents.length === 0"
            title="知识库中还没有文档"
            description="进入文档管理后上传 PDF，系统会自动解析并建立检索索引。"
          />
          <el-table v-else :data="documents.slice(0, 5)" class="data-table">
            <el-table-column prop="filename" label="文档名称" min-width="260" />
            <el-table-column label="解析状态" width="130">
              <template #default="{ row }"
                ><DocumentStatusTag :status="row.status"
              /></template>
            </el-table-column>
            <el-table-column prop="chunk_count" label="分段数" width="100" />
            <el-table-column label="上传时间" min-width="170">
              <template #default="{ row }">{{
                formatDate(row.created_at)
              }}</template>
            </el-table-column>
          </el-table>
        </section>
      </template>
    </section>
  </AppLayout>
</template>
