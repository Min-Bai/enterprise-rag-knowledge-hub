<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage, ElMessageBox, genFileId } from "element-plus";
import type { UploadFile, UploadInstance, UploadRawFile } from "element-plus";
import { ArrowLeft, RefreshCw, Search, Trash2, Upload } from "lucide-vue-next";
import {
  deleteDocument,
  downloadDocument,
  getDocuments,
  reindexDocument,
  reindexDocuments,
  retryDocument,
  updateDocumentTags,
  uploadDocument,
} from "../api/documents";
import { getDocumentProcessingErrorMessage } from "../api/client";
import AppEmpty from "../components/common/AppEmpty.vue";
import DocumentStatusTag from "../components/common/DocumentStatusTag.vue";
import AppLayout from "../layouts/AppLayout.vue";
import KnowledgeBaseTabs from "../components/knowledge-base/KnowledgeBaseTabs.vue";
import { useAuthStore } from "../stores/auth";
import { useRoute } from "vue-router";
import { getKnowledgeBases } from "../api/knowledgeBases";
import type { DocumentItem } from "../types/api";
const route = useRoute();
const auth = useAuthStore();
const documents = ref<DocumentItem[]>([]);
const hasMore = ref(false);
const loadingMore = ref(false);
const selectedDocuments = ref<DocumentItem[]>([]);
const query = ref("");
const statusFilter = ref("all");
const tagFilter = ref<string[]>([]);
const loading = ref(true);
const error = ref("");
const uploadOpen = ref(false);
const file = ref<File | null>(null);
const tags = ref("");
const uploading = ref(false);
const fileUploadRef = ref<UploadInstance>();
const editTagsOpen = ref(false);
const editingDocument = ref<DocumentItem | null>(null);
const editTags = ref("");
const savingTags = ref(false);
const knowledgeBaseId = computed(() => Number(route.params.id));
const pageSize = 20;
const maxUploadBytes = 10 * 1024 * 1024;
const canManage = ref(false);
const knowledgeBaseRole = ref<"owner" | "editor" | "viewer" | null>(null);
const knowledgeBaseName = ref("加载中");
const availableTags = computed(() =>
  [...new Set(documents.value.flatMap((document) => document.tags))].sort(),
);
function rolePermission(role: "owner" | "editor" | "viewer") {
  return {
    owner: "当前权限：所有者，可管理成员、文档与检索测试。",
    editor: "当前权限：编辑者，可上传、编辑、删除文档和执行检索测试。",
    viewer: "当前权限：查看者，可浏览、检索和问答，不能修改文档。",
  }[role];
}
const filteredDocuments = computed(() =>
  documents.value.filter(
    (document) =>
      (statusFilter.value === "all" ||
        document.status === statusFilter.value) &&
      (!query.value.trim() ||
        document.filename
          .toLowerCase()
          .includes(query.value.trim().toLowerCase())) &&
      (tagFilter.value.length === 0 ||
        tagFilter.value.every((tag) => document.tags.includes(tag))),
  ),
);
const selectedReadyDocuments = computed(() =>
  selectedDocuments.value.filter((document) => document.status === "ready"),
);
async function load() {
  if (!auth.token) return;
  loading.value = true;
  try {
    const [loadedDocuments, knowledgeBases] = await Promise.all([
      getDocuments(auth.token, knowledgeBaseId.value, pageSize),
      getKnowledgeBases(auth.token),
    ]);
    documents.value = loadedDocuments;
    hasMore.value = loadedDocuments.length === pageSize;
    const knowledgeBase = knowledgeBases.find(
      (item) => item.id === knowledgeBaseId.value,
    );
    knowledgeBaseRole.value = knowledgeBase?.role ?? null;
    knowledgeBaseName.value = knowledgeBase?.name ?? "未找到知识库";
    canManage.value =
      knowledgeBaseRole.value === "owner" ||
      knowledgeBaseRole.value === "editor";
  } catch (caught) {
    error.value =
      caught instanceof Error ? caught.message : "加载文档失败，请稍后重试。";
  } finally {
    loading.value = false;
  }
}
async function loadMore() {
  if (!auth.token || !hasMore.value || loadingMore.value) return;
  loadingMore.value = true;
  try {
    const nextItems = await getDocuments(
      auth.token,
      knowledgeBaseId.value,
      pageSize,
      documents.value.length,
    );
    documents.value = [...documents.value, ...nextItems];
    hasMore.value = nextItems.length === pageSize;
  } catch (caught) {
    ElMessage.error(
      caught instanceof Error
        ? caught.message
        : "加载更多文档失败，请稍后重试。",
    );
  } finally {
    loadingMore.value = false;
  }
}
async function upload() {
  if (!auth.token || !file.value) return;
  uploading.value = true;
  try {
    const item = await uploadDocument(
      auth.token,
      knowledgeBaseId.value,
      file.value,
      tags.value
        .split(",")
        .map((tag) => tag.trim())
        .filter(Boolean),
    );
    documents.value = [item, ...documents.value];
    resetUpload();
    uploadOpen.value = false;
    ElMessage.success("文件已上传，正在等待处理。");
  } catch (caught) {
    ElMessage.error(
      caught instanceof Error ? caught.message : "上传失败，请稍后重试。",
    );
  } finally {
    uploading.value = false;
  }
}
function openTagEditor(item: DocumentItem) {
  editingDocument.value = item;
  editTags.value = item.tags.join(", ");
  editTagsOpen.value = true;
}
async function saveTags() {
  if (!auth.token || !editingDocument.value) return;
  savingTags.value = true;
  try {
    const updated = await updateDocumentTags(
      auth.token,
      editingDocument.value.id,
      editTags.value
        .split(",")
        .map((tag) => tag.trim())
        .filter(Boolean),
    );
    documents.value = documents.value.map((item) =>
      item.id === updated.id ? updated : item,
    );
    editTagsOpen.value = false;
    ElMessage.success("文档标签已保存");
  } catch (caught) {
    ElMessage.error(
      caught instanceof Error ? caught.message : "保存标签失败，请稍后重试。",
    );
  } finally {
    savingTags.value = false;
  }
}
function resetUpload() {
  file.value = null;
  tags.value = "";
  fileUploadRef.value?.clearFiles();
}
async function run(action: "retry" | "reindex", item: DocumentItem) {
  if (!auth.token) return;
  try {
    const updated =
      action === "retry"
        ? await retryDocument(auth.token, item.id)
        : await reindexDocument(auth.token, item.id);
    documents.value = documents.value.map((current) =>
      current.id === item.id ? updated : current,
    );
    ElMessage.success(
      action === "retry" ? "已重新加入处理队列" : "已重新加入索引队列",
    );
  } catch (caught) {
    ElMessage.error(
      caught instanceof Error ? caught.message : "操作失败，请稍后重试。",
    );
  }
}
async function remove(item: DocumentItem) {
  if (!auth.token) return false;
  try {
    await deleteDocument(auth.token, item.id);
    documents.value = documents.value.filter(
      (current) => current.id !== item.id,
    );
    ElMessage.success("文档已删除");
    return true;
  } catch (caught) {
    ElMessage.error(
      caught instanceof Error ? caught.message : "删除失败，请稍后重试。",
    );
    return false;
  }
}
async function removeSelected() {
  const items = [...selectedDocuments.value];
  if (!items.length) return;
  try {
    await ElMessageBox.confirm(
      `将永久删除选中的 ${items.length} 份文档，相关索引也会一并删除。此操作无法恢复。`,
      "删除文档",
      {
        confirmButtonText: "删除",
        cancelButtonText: "取消",
        type: "warning",
      },
    );
  } catch {
    return;
  }
  const outcomes = await Promise.all(items.map((item) => remove(item)));
  selectedDocuments.value = [];
  if (outcomes.some((outcome) => !outcome))
    ElMessage.warning("部分文档删除失败，请稍后重试。");
}
async function reindexSelected() {
  if (!auth.token || !selectedReadyDocuments.value.length) return;
  const items = [...selectedReadyDocuments.value];
  try {
    await ElMessageBox.confirm(
      `将重新建立 ${items.length} 份已就绪文档的索引。原有向量会替换，文档将在后台重新处理。`,
      "批量重建索引",
      { confirmButtonText: "重建索引", cancelButtonText: "取消", type: "warning" },
    );
  } catch {
    return;
  }
  try {
    const updated = await reindexDocuments(auth.token, items.map((item) => item.id));
    const updatedById = new Map(updated.map((item) => [item.id, item]));
    documents.value = documents.value.map((item) => updatedById.get(item.id) ?? item);
    selectedDocuments.value = [];
    ElMessage.success(`已将 ${updated.length} 份文档加入索引队列`);
  } catch (caught) {
    ElMessage.error(caught instanceof Error ? caught.message : "批量重建索引失败，请稍后重试。");
  }
}
function selectFile(uploadFile: UploadFile) {
  const selectedFile = uploadFile.raw;
  if (!selectedFile) return;
  if (
    selectedFile.type !== "application/pdf" &&
    !selectedFile.name.toLowerCase().endsWith(".pdf")
  ) {
    ElMessage.error("仅支持上传 PDF 文件。");
    file.value = null;
    fileUploadRef.value?.clearFiles();
    return;
  }
  if (selectedFile.size > maxUploadBytes) {
    ElMessage.error("文件不能超过 10 MB，请压缩或拆分后再上传。");
    file.value = null;
    fileUploadRef.value?.clearFiles();
    return;
  }
  file.value = selectedFile;
}
function replaceFile(files: UploadRawFile[]) {
  const selectedFile = files[0];
  if (!selectedFile || !fileUploadRef.value) return;
  file.value = null;
  fileUploadRef.value.clearFiles();
  selectedFile.uid = genFileId();
  fileUploadRef.value.handleStart(selectedFile);
}
function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
function fileType(filename: string) {
  return filename.toLowerCase().endsWith(".pdf") ? "PDF" : "文件";
}
function formatDocumentError(errorMessage: string) {
  return getDocumentProcessingErrorMessage(errorMessage);
}
async function download(item: DocumentItem) {
  if (!auth.token) return;
  try {
    await downloadDocument(auth.token, item.id, item.filename);
  } catch (caught) {
    ElMessage.error(
      caught instanceof Error ? caught.message : "下载文档失败，请稍后重试。",
    );
  }
}
onMounted(load);
</script>
<template>
  <AppLayout
    ><section class="page-shell" aria-labelledby="documents-title">
      <header class="page-header">
        <div>
          <RouterLink class="back-link" :to="`/app/knowledge-bases/${knowledgeBaseId}`">
            <ArrowLeft :size="15" /> 返回知识库概览
          </RouterLink>
          <p class="eyebrow">知识库文档</p>
          <h1 id="documents-title">{{ knowledgeBaseName }}</h1>
          <p>上传后将由后台异步解析和建立索引。</p>
          <p v-if="knowledgeBaseRole" class="role-permission">
            {{ rolePermission(knowledgeBaseRole) }}
          </p>
        </div>
        <div class="page-header-actions">
          <el-button :loading="loading" @click="load"
            ><RefreshCw :size="16" />刷新列表</el-button
          ><el-button v-if="canManage" type="primary" @click="uploadOpen = true"
            ><Upload :size="16" />上传文档</el-button
          >
        </div>
      </header>
      <KnowledgeBaseTabs
        :knowledge-base-id="knowledgeBaseId"
        :role="knowledgeBaseRole"
      />
      <el-alert
        v-if="error"
        class="form-alert"
        type="error"
        :title="error"
        show-icon
      />
      <section class="table-surface">
        <div class="table-toolbar">
          <el-input
            v-model="query"
            :prefix-icon="Search"
            clearable
            placeholder="搜索文档名称"
          /><el-select v-model="statusFilter" aria-label="解析状态"
            ><el-option label="全部状态" value="all" /><el-option
              label="等待处理"
              value="uploaded" /><el-option
              label="解析中"
              value="processing" /><el-option
              label="已完成"
              value="ready" /><el-option
              label="失败"
              value="failed" /></el-select
          ><el-select
            v-model="tagFilter"
            multiple
            clearable
            collapse-tags
            placeholder="按标签筛选"
            aria-label="标签筛选"
            ><el-option
              v-for="tag in availableTags"
              :key="tag"
              :label="tag"
              :value="tag" /></el-select
          ><el-button
            v-if="canManage && selectedReadyDocuments.length"
            type="primary"
            plain
            @click="reindexSelected"
            ><RefreshCw :size="16" />重建索引 {{ selectedReadyDocuments.length }} 项</el-button
          ><el-button
            v-if="canManage && selectedDocuments.length"
            type="danger"
            plain
            @click="removeSelected"
            ><Trash2 :size="16" />删除已选
            {{ selectedDocuments.length }} 项</el-button
          >
        </div>
        <el-skeleton v-if="loading" :rows="7" animated /><AppEmpty
          v-else-if="documents.length === 0"
          title="知识库中还没有文档"
          description="上传 PDF 文档后，系统会自动解析并建立检索索引。"
        /><AppEmpty
          v-else-if="filteredDocuments.length === 0"
          title="没有符合条件的文档"
          description="请调整文件名、解析状态或标签筛选条件后重试。"
        /><el-table
          v-else
          :data="filteredDocuments"
          class="data-table"
          :default-sort="{ prop: 'created_at', order: 'descending' }"
          @selection-change="selectedDocuments = $event"
          ><el-table-column v-if="canManage" type="selection" width="44" />
          <el-table-column
            prop="filename"
            label="文档名称"
            min-width="220"
          /><el-table-column label="类型" width="90">
            <template #default="{ row }">{{ fileType(row.filename) }}</template>
          </el-table-column>
          <el-table-column label="标签" min-width="160"
            ><template #default="{ row }"
              ><el-tag
                v-for="tag in row.tags"
                :key="tag"
                size="small"
                effect="plain"
                class="document-tag"
                >{{ tag }}</el-tag
              ><span v-if="!row.tags.length" class="table-secondary"
                >无</span
              ></template
            ></el-table-column
          ><el-table-column label="解析状态" width="120"
            ><template #default="{ row }"
              ><DocumentStatusTag :status="row.status" />
              <p v-if="row.error_message" class="table-error">
                {{ formatDocumentError(row.error_message) }}
              </p></template
            ></el-table-column
          ><el-table-column prop="chunk_count" label="分段数" width="90" />
          <el-table-column
            prop="created_at"
            label="上传时间"
            min-width="165"
            sortable
          >
            <template #default="{ row }">{{
              formatDate(row.created_at)
            }}</template>
          </el-table-column>
          <el-table-column label="操作" width="220" fixed="right"
            ><template #default="{ row }"
              ><el-button link type="primary" @click="download(row)"
                >下载</el-button
              ><el-button
                v-if="canManage && row.status === 'failed'"
                link
                type="primary"
                @click="run('retry', row)"
                >重试</el-button
              ><el-button
                v-if="canManage && row.status === 'ready'"
                link
                type="primary"
                @click="run('reindex', row)"
                >重建索引</el-button
              ><el-button
                v-if="canManage"
                link
                type="primary"
                :disabled="row.status === 'processing'"
                @click="openTagEditor(row)"
                >编辑标签</el-button
              ><el-popconfirm
                v-if="canManage"
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
        <div v-if="hasMore" class="table-load-more">
          <el-button :loading="loadingMore" @click="loadMore"
            >加载更多</el-button
          >
        </div>
      </section>
    </section>
    <el-drawer
      v-model="uploadOpen"
      title="上传文档"
      direction="rtl"
      size="min(100%, 460px)"
      @closed="resetUpload"
      ><el-form label-position="top"
        ><el-form-item label="文件" required
          ><el-upload
            ref="fileUploadRef"
            :auto-upload="false"
            :limit="1"
            accept="application/pdf"
            :on-change="selectFile"
            :on-exceed="replaceFile"
            :on-remove="() => (file = null)"
            ><el-button>选择 PDF 文件</el-button
            ><template #tip
              ><div class="el-upload__tip">
                仅支持 PDF，文件不能超过 10 MB。
              </div></template
            ></el-upload
          ></el-form-item
        ><el-form-item label="标签"
          ><el-input
            v-model="tags"
            placeholder="例如：制度、2026，使用逗号分隔" /></el-form-item></el-form
      ><template #footer
        ><el-button @click="uploadOpen = false">取消</el-button
        ><el-button
          type="primary"
          :disabled="!file"
          :loading="uploading"
          @click="upload"
          >开始上传</el-button
        ></template
      ></el-drawer
    ><el-dialog
      v-model="editTagsOpen"
      title="编辑文档标签"
      width="min(92vw, 460px)"
      ><p class="table-secondary">{{ editingDocument?.filename }}</p>
      <el-input
        v-model="editTags"
        placeholder="例如：制度、2026，使用逗号分隔"
      /><template #footer
        ><el-button @click="editTagsOpen = false">取消</el-button
        ><el-button type="primary" :loading="savingTags" @click="saveTags"
          >保存</el-button
        ></template
      ></el-dialog
    ></AppLayout
  >
</template>
