<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { RefreshCw } from "lucide-vue-next";
import { getAdminJobs, getWorkerStatus, type AdminJob } from "../api/admin";
import { useAdminAuthStore } from "../stores/adminAuth";
import AdminLayout from "../layouts/AdminLayout.vue";

const auth = useAdminAuthStore();
const jobs = ref<AdminJob[]>([]);
const counts = ref<Record<string, number>>({});
const worker = ref<{ registered_workers: string[]; active_tasks: number; reserved_tasks: number }>();
const loading = ref(false);
const error = ref("");
const totalDocuments = computed(() => Object.values(counts.value).reduce((sum, count) => sum + count, 0));
const statusLabel = (status: string) => ({ uploaded: "待处理", processing: "处理中", ready: "已就绪", failed: "失败" }[status] ?? status);
const statusType = (status: string) => ({ ready: "success", failed: "danger", processing: "warning" }[status] ?? "info");
const formatDate = (value: string) => new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
async function load() { if (!auth.token) return; loading.value = true; error.value = ""; try { const [jobData, workerData] = await Promise.all([getAdminJobs(auth.token), getWorkerStatus(auth.token)]); jobs.value = jobData.recent; counts.value = jobData.status_counts; worker.value = workerData; } catch (caught) { error.value = caught instanceof Error ? caught.message : "加载任务状态失败，请稍后重试。"; } finally { loading.value = false; } }
async function refresh() { await load(); if (!error.value) ElMessage.success("任务状态已刷新"); }
onMounted(load);
</script>
<template>
  <AdminLayout><section class="page-shell admin-page"><header class="page-header"><div><p class="eyebrow">异步任务</p><h1>任务状态</h1><p>查看文档解析队列、Worker 在线状态和近期需要处理的文档。</p></div><el-button :icon="RefreshCw" :loading="loading" @click="refresh">刷新</el-button></header><el-alert v-if="error" class="form-alert" type="error" :title="error" show-icon />
    <section class="metric-grid operation-metrics" v-loading="loading"><article><span>文档总数</span><strong>{{ totalDocuments }}</strong></article><article><span>待处理</span><strong>{{ counts.uploaded ?? 0 }}</strong></article><article><span>处理中</span><strong>{{ counts.processing ?? 0 }}</strong></article><article><span>处理失败</span><strong>{{ counts.failed ?? 0 }}</strong></article><article><span>在线 Worker</span><strong>{{ worker?.registered_workers.length ?? 0 }}</strong></article><article><span>运行中 / 等待中</span><strong>{{ worker ? `${worker.active_tasks} / ${worker.reserved_tasks}` : "-" }}</strong></article></section>
    <section class="table-surface"><div class="section-heading"><div><p class="eyebrow">需要关注</p><h2>近期未完成文档</h2></div><span class="section-caption">仅显示待处理、处理中和失败的文档</span></div><el-table v-loading="loading" :data="jobs" empty-text="当前没有待处理或失败的文档" class="data-table"><el-table-column prop="filename" label="文件名" min-width="230"/><el-table-column label="知识库" width="110"><template #default="{ row }">#{{ row.knowledge_base_id }}</template></el-table-column><el-table-column label="状态" width="120"><template #default="{ row }"><el-tag :type="statusType(row.status) as any">{{ statusLabel(row.status) }}</el-tag></template></el-table-column><el-table-column label="失败原因" min-width="280"><template #default="{ row }">{{ row.error_message || "-" }}</template></el-table-column><el-table-column label="上传时间" min-width="175"><template #default="{ row }">{{ formatDate(row.created_at) }}</template></el-table-column></el-table></section>
  </section></AdminLayout>
</template>
