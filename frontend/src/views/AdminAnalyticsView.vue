<script setup lang="ts">
import { onMounted, ref } from "vue";
import { RefreshCw } from "lucide-vue-next";
import { getAdminAuditLogs, getOverview, type AuditLog } from "../api/admin";
import { useAdminAuthStore } from "../stores/adminAuth";
import AdminLayout from "../layouts/AdminLayout.vue";
const auth = useAdminAuthStore();
const overview = ref<{ users: number; knowledge_bases: number; documents: number; ready_documents: number }>();
const auditLogs = ref<AuditLog[]>([]); const loading = ref(false); const error = ref("");
const formatDate = (value: string) => new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
const actionLabel = (action: string) => ({ "admin.user.created": "创建用户", "admin.user.deleted": "删除用户", "admin.user.role_updated": "更新用户角色", "admin.user.status_updated": "更新用户状态" }[action] ?? action);
async function load() { if (!auth.token) return; loading.value = true; error.value = ""; try { const [overviewData, logs] = await Promise.all([getOverview(auth.token), getAdminAuditLogs(auth.token)]); overview.value = overviewData; auditLogs.value = logs; } catch (caught) { error.value = caught instanceof Error ? caught.message : "加载运行概览失败，请稍后重试。"; } finally { loading.value = false; } }
onMounted(load);
</script>
<template>
  <AdminLayout><section class="page-shell admin-page"><header class="page-header"><div><p class="eyebrow">系统概览</p><h1>运行概览</h1><p>基于当前数据库和审计记录展示平台规模与管理操作。</p></div><el-button :icon="RefreshCw" :loading="loading" @click="load">刷新</el-button></header><el-alert v-if="error" class="form-alert" type="error" :title="error" show-icon />
    <section class="metric-grid" v-loading="loading"><article><span>用户</span><strong>{{ overview?.users ?? "-" }}</strong></article><article><span>知识库</span><strong>{{ overview?.knowledge_bases ?? "-" }}</strong></article><article><span>文档</span><strong>{{ overview?.documents ?? "-" }}</strong></article><article><span>已就绪文档</span><strong>{{ overview?.ready_documents ?? "-" }}</strong></article></section>
    <section class="table-surface admin-audit-table"><div class="section-heading"><div><p class="eyebrow">可追溯性</p><h2>最近管理操作</h2></div><span class="section-caption">最多显示 50 条</span></div><el-table v-loading="loading" :data="auditLogs" empty-text="暂无管理操作记录" class="data-table"><el-table-column prop="actor_username" label="操作人" min-width="130"/><el-table-column label="操作" min-width="180"><template #default="{ row }">{{ actionLabel(row.action) }}</template></el-table-column><el-table-column label="目标" min-width="160"><template #default="{ row }">{{ row.target_type }}{{ row.target_id ? ` #${row.target_id}` : "" }}</template></el-table-column><el-table-column label="详情" min-width="190"><template #default="{ row }">{{ row.details ? JSON.stringify(row.details) : "-" }}</template></el-table-column><el-table-column label="时间" min-width="175"><template #default="{ row }">{{ formatDate(row.created_at) }}</template></el-table-column></el-table></section>
  </section></AdminLayout>
</template>
