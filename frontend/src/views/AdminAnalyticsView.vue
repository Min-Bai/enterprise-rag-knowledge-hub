<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { CircleAlert, Database, FileCheck2, FileText, RefreshCw, UsersRound } from "lucide-vue-next";
import { getAdminAuditLogs, getAdminJobs, getOverview, type AdminJob, type AuditLog } from "../api/admin";
import { useAdminAuthStore } from "../stores/adminAuth";
import AdminLayout from "../layouts/AdminLayout.vue";

const auth = useAdminAuthStore();
const overview = ref<{ users: number; knowledge_bases: number; documents: number; ready_documents: number }>();
const auditLogs = ref<AuditLog[]>([]);
const jobs = ref<{ status_counts: Record<string, number>; recent: AdminJob[] }>({ status_counts: {}, recent: [] });
const loading = ref(false);
const error = ref("");

const metrics = computed(() => [
  { label: "平台用户", value: overview.value?.users ?? "-", icon: UsersRound, tone: "blue" },
  { label: "知识库", value: overview.value?.knowledge_bases ?? "-", icon: Database, tone: "cyan" },
  { label: "已入库文档", value: overview.value?.documents ?? "-", icon: FileText, tone: "violet" },
  { label: "可检索文档", value: overview.value?.ready_documents ?? "-", icon: FileCheck2, tone: "green" },
]);
const totalJobs = computed(() => Object.values(jobs.value.status_counts).reduce((total, count) => total + count, 0));
const processingJobs = computed(() => (jobs.value.status_counts.uploaded ?? 0) + (jobs.value.status_counts.processing ?? 0));
const failedJobs = computed(() => jobs.value.status_counts.failed ?? 0);
const readyRate = computed(() => {
  const total = overview.value?.documents ?? 0;
  return total ? `${Math.round(((overview.value?.ready_documents ?? 0) / total) * 100)}%` : "-";
});

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}
function actionLabel(action: string) {
  return ({
    "admin.user.created": "创建用户",
    "admin.user.deleted": "删除用户",
    "admin.user.role_updated": "更新用户角色",
    "admin.user.status_updated": "更新用户状态",
  } as Record<string, string>)[action] ?? action;
}
function jobStatusLabel(status: string) {
  return ({ uploaded: "等待处理", processing: "处理中", ready: "已完成", failed: "处理失败" } as Record<string, string>)[status] ?? status;
}
function jobStatusType(status: string) {
  return ({ uploaded: "info", processing: "warning", ready: "success", failed: "danger" } as Record<string, "info" | "warning" | "success" | "danger">)[status] ?? "info";
}
async function load() {
  if (!auth.token) return;
  loading.value = true;
  error.value = "";
  try {
    const [overviewData, logData, jobData] = await Promise.all([
      getOverview(auth.token),
      getAdminAuditLogs(auth.token),
      getAdminJobs(auth.token),
    ]);
    overview.value = overviewData;
    auditLogs.value = logData;
    jobs.value = jobData;
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "加载运行概览失败，请稍后重试。";
  } finally {
    loading.value = false;
  }
}
onMounted(load);
</script>

<template>
  <AdminLayout>
    <section class="page-shell admin-page admin-dashboard" aria-labelledby="analytics-title">
      <header class="page-header">
        <div>
          <p class="eyebrow">系统概览</p>
          <h1 id="analytics-title">运行概述</h1>
          <p>查看平台规模、文档处理状态与最近管理操作。</p>
        </div>
        <el-button :icon="RefreshCw" :loading="loading" @click="load">刷新数据</el-button>
      </header>
      <el-alert v-if="error" class="form-alert" type="error" :title="error" show-icon />

      <section class="dashboard-metric-grid" aria-label="平台指标" v-loading="loading">
        <article v-for="metric in metrics" :key="metric.label" class="dashboard-metric" :class="`metric-${metric.tone}`">
          <span class="metric-icon"><component :is="metric.icon" :size="21" /></span>
          <div><span>{{ metric.label }}</span><strong>{{ metric.value }}</strong></div>
        </article>
      </section>

      <section class="dashboard-detail-grid" aria-label="文档处理概况">
        <article class="table-surface processing-summary" v-loading="loading">
          <div class="section-heading">
            <div><p class="eyebrow">文档处理</p><h2>索引运行状态</h2></div>
            <span class="section-caption">当前后台任务</span>
          </div>
          <div class="processing-kpis">
            <div><span>任务总数</span><strong>{{ totalJobs }}</strong></div>
            <div><span>处理中</span><strong class="warning-value">{{ processingJobs }}</strong></div>
            <div><span>处理失败</span><strong class="danger-value">{{ failedJobs }}</strong></div>
            <div><span>文档就绪率</span><strong class="success-value">{{ readyRate }}</strong></div>
          </div>
          <div v-if="jobs.recent.length" class="processing-list">
            <div v-for="job in jobs.recent.slice(0, 5)" :key="job.id" class="processing-row">
              <span class="processing-file" :title="job.filename">{{ job.filename }}</span>
              <el-tag size="small" :type="jobStatusType(job.status)" effect="light">{{ jobStatusLabel(job.status) }}</el-tag>
            </div>
          </div>
          <div v-else class="dashboard-empty"><CircleAlert :size="18" />暂无文档处理任务</div>
        </article>

        <article class="table-surface activity-summary" v-loading="loading">
          <div class="section-heading"><div><p class="eyebrow">风险提示</p><h2>管理关注项</h2></div></div>
          <div class="activity-stat"><span>失败任务</span><strong>{{ failedJobs }}</strong><p>失败文档可在“任务状态”中查看原因并重新处理。</p></div>
          <div class="activity-stat"><span>待处理任务</span><strong>{{ processingJobs }}</strong><p>文档解析和索引由后台任务异步执行，完成后才会参与检索。</p></div>
        </article>
      </section>

      <section class="table-surface admin-audit-table" v-loading="loading">
        <div class="section-heading"><div><p class="eyebrow">可追溯性</p><h2>最近管理操作</h2></div><span class="section-caption">最多显示 50 条</span></div>
        <el-table :data="auditLogs" empty-text="暂无管理操作记录" class="data-table">
          <el-table-column prop="actor_username" label="操作人" min-width="130" />
          <el-table-column label="操作" min-width="180"><template #default="{ row }">{{ actionLabel(row.action) }}</template></el-table-column>
          <el-table-column label="目标" min-width="160"><template #default="{ row }">{{ row.target_type }}{{ row.target_id ? ` #${row.target_id}` : "" }}</template></el-table-column>
          <el-table-column label="时间" min-width="175"><template #default="{ row }">{{ formatDate(row.created_at) }}</template></el-table-column>
        </el-table>
      </section>
    </section>
  </AdminLayout>
</template>
