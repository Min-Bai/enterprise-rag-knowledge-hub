<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { ApiError } from "../api/client";
import { getDocuments } from "../api/documents";
import { MoreHorizontal, Plus, Search } from "lucide-vue-next";
import {
  createKnowledgeBase,
  deleteKnowledgeBase,
  getKnowledgeBases,
} from "../api/knowledgeBases";
import AppEmpty from "../components/common/AppEmpty.vue";
import AppLayout from "../layouts/AppLayout.vue";
import { useAuthStore } from "../stores/auth";
import type { KnowledgeBase } from "../types/api";

const auth = useAuthStore();
const items = ref<KnowledgeBase[]>([]);
const loading = ref(true);
const error = ref("");
const query = ref("");
const statusFilter = ref("all");
const createOpen = ref(false);
const saving = ref(false);
const form = ref({ name: "", description: "" });
type KnowledgeBaseSummary = {
  documentCount: number;
  status: string;
  lastDocumentAt: string | null;
};
const summaries = ref<Record<number, KnowledgeBaseSummary>>({});
const filteredItems = computed(() =>
  items.value.filter(
    (item) =>
      item.name.toLowerCase().includes(query.value.trim().toLowerCase()) &&
      (statusFilter.value === "all" ||
        summaryType(summaries.value[item.id]?.status ?? "") ===
          statusFilter.value),
  ),
);

async function load() {
  if (!auth.token) return;
  loading.value = true;
  error.value = "";
  try {
    items.value = await getKnowledgeBases(auth.token);
    const results = await Promise.all(
      items.value.map(async (item) => {
        const documents = await getDocuments(auth.token!, item.id);
        const status = documents.some(
          (document) => document.status === "failed",
        )
          ? "存在失败"
          : documents.some(
                (document) =>
                  document.status === "processing" ||
                  document.status === "uploaded",
              )
            ? "处理中"
            : documents.length
              ? "已完成"
              : "暂无文档";
        const lastDocumentAt =
          documents
            .map((document) => document.created_at)
            .sort()
            .at(-1) ?? null;
        return [
          item.id,
          { documentCount: documents.length, status, lastDocumentAt },
        ] as const;
      }),
    );
    summaries.value = Object.fromEntries(results);
  } catch (caught) {
    error.value =
      caught instanceof Error ? caught.message : "加载知识库失败，请稍后重试。";
  } finally {
    loading.value = false;
  }
}
async function create() {
  if (!auth.token || !form.value.name.trim()) return;
  saving.value = true;
  try {
    const item = await createKnowledgeBase(auth.token, {
      name: form.value.name.trim(),
      description: form.value.description.trim() || undefined,
    });
    items.value = [item, ...items.value];
    createOpen.value = false;
    form.value = { name: "", description: "" };
    ElMessage.success("知识库已创建");
  } catch (caught) {
    ElMessage.error(
      caught instanceof Error ? caught.message : "创建知识库失败，请稍后重试。",
    );
  } finally {
    saving.value = false;
  }
}
async function remove(item: KnowledgeBase) {
  if (!auth.token) return;
  try {
    await ElMessageBox.confirm(
      "删除后无法恢复。知识库内有文档时必须先删除全部文档。",
      "删除知识库",
      { confirmButtonText: "删除", cancelButtonText: "取消", type: "warning" },
    );
    await deleteKnowledgeBase(auth.token, item.id);
    items.value = items.value.filter((current) => current.id !== item.id);
    ElMessage.success("知识库已删除");
  } catch (caught) {
    if (caught === "cancel" || caught === "close") return;
    ElMessage.error(
      caught instanceof ApiError && caught.status === 409
        ? "知识库内仍有文档，请先在文档管理中删除全部文档。"
        : caught instanceof Error
          ? caught.message
          : "删除知识库失败，请稍后重试。",
    );
  }
}
function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
function roleLabel(role: KnowledgeBase["role"]) {
  return { owner: "所有者", editor: "可编辑", viewer: "只读" }[role];
}
function summaryType(status: string) {
  return status === "已完成"
    ? "success"
    : status === "存在失败"
      ? "danger"
      : status === "处理中"
        ? "warning"
        : "info";
}
onMounted(load);
</script>

<template>
  <AppLayout
    ><section class="page-shell" aria-labelledby="knowledge-base-title">
      <header class="page-header">
        <div>
          <p class="eyebrow">知识库</p>
          <h1 id="knowledge-base-title">知识库管理</h1>
          <p>创建并维护团队可检索的企业知识。</p>
        </div>
        <el-button type="primary" @click="createOpen = true"
          ><Plus :size="16" />新建知识库</el-button
        >
      </header>
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
            placeholder="搜索知识库"
            :prefix-icon="Search"
            clearable
          />
          <el-select v-model="statusFilter" aria-label="文档解析状态">
            <el-option label="全部状态" value="all" />
            <el-option label="存在失败" value="danger" />
            <el-option label="处理中" value="warning" />
            <el-option label="已完成" value="success" />
            <el-option label="暂无文档" value="info" />
          </el-select>
        </div>
        <el-skeleton v-if="loading" :rows="7" animated /><AppEmpty
          v-else-if="filteredItems.length === 0"
          title="还没有可访问的知识库"
          description="创建知识库后即可上传文档并开始问答。"
        /><el-table v-else :data="filteredItems" class="data-table"
          ><el-table-column prop="name" label="知识库名称" min-width="200"
            ><template #default="{ row }"
              ><RouterLink
                class="table-link"
                :to="`/knowledge-bases/${row.id}/documents`"
                >{{ row.name }}</RouterLink
              >
              <p v-if="row.description" class="table-secondary">
                {{ row.description }}
              </p></template
            ></el-table-column
          ><el-table-column label="权限" width="110"
            ><template #default="{ row }"
              ><el-tag effect="plain">{{
                roleLabel(row.role)
              }}</el-tag></template
            ></el-table-column
          ><el-table-column label="已加载文档" width="110"
            ><template #default="{ row }">{{
              summaries[row.id]?.documentCount ?? "-"
            }}</template></el-table-column
          ><el-table-column label="已加载状态" width="120"
            ><template #default="{ row }"
              ><el-tag
                :type="summaryType(summaries[row.id]?.status ?? '暂无文档')"
                effect="plain"
                >{{ summaries[row.id]?.status ?? "加载中" }}</el-tag
              ></template
            ></el-table-column
          ><el-table-column label="最近文档上传" min-width="165"
            ><template #default="{ row }">{{
              summaries[row.id]?.lastDocumentAt
                ? formatDate(summaries[row.id].lastDocumentAt!)
                : "暂无文档"
            }}</template></el-table-column
          ><el-table-column label="创建时间" min-width="165"
            ><template #default="{ row }">{{
              formatDate(row.created_at)
            }}</template></el-table-column
          ><el-table-column label="操作" width="150" fixed="right"
            ><template #default="{ row }"
              ><el-button
                link
                type="primary"
                @click="$router.push(`/knowledge-bases/${row.id}/documents`)"
                >文档</el-button
              ><el-dropdown v-if="row.role === 'owner'"
                ><button
                  class="icon-button light"
                  type="button"
                  title="更多操作"
                  aria-label="更多操作"
                >
                  <MoreHorizontal :size="18" /></button
                ><template #dropdown
                  ><el-dropdown-menu
                    ><el-dropdown-item
                      ><RouterLink
                        class="menu-link"
                        :to="`/knowledge-bases/${row.id}/access`"
                        >成员权限</RouterLink
                      ></el-dropdown-item
                    ><el-dropdown-item divided @click="remove(row)"
                      >删除知识库</el-dropdown-item
                    ></el-dropdown-menu
                  ></template
                ></el-dropdown
              ></template
            ></el-table-column
          ></el-table
        >
      </section>
    </section>
    <el-dialog
      v-model="createOpen"
      title="新建知识库"
      width="min(92vw, 480px)"
      :close-on-click-modal="false"
      ><el-form label-position="top"
        ><el-form-item label="名称" required
          ><el-input
            v-model="form.name"
            maxlength="100"
            show-word-limit
            placeholder="例如：人力资源制度" /></el-form-item
        ><el-form-item label="说明"
          ><el-input
            v-model="form.description"
            type="textarea"
            :rows="4"
            maxlength="2000"
            show-word-limit
            placeholder="可选，说明此知识库的内容范围" /></el-form-item></el-form
      ><template #footer
        ><el-button @click="createOpen = false">取消</el-button
        ><el-button
          type="primary"
          :loading="saving"
          :disabled="!form.name.trim()"
          @click="create"
          >创建</el-button
        ></template
      ></el-dialog
    ></AppLayout
  >
</template>
