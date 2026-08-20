<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { CircleDollarSign, Clock3, RefreshCw, Sigma, WandSparkles } from "lucide-vue-next";
import { getModelUsageAnalytics, type ModelUsageAnalytics } from "../api/admin";
import { useAdminAuthStore } from "../stores/adminAuth";
import AdminLayout from "../layouts/AdminLayout.vue";

const auth = useAdminAuthStore();
const days = ref(30);
const loading = ref(false);
const error = ref("");
const data = ref<ModelUsageAnalytics>();
const metrics = computed(() => [
  { label: "模型调用", value: data.value?.summary.requests ?? "-", icon: WandSparkles, tone: "blue" },
  { label: "累计 Token", value: data.value?.summary.total_tokens.toLocaleString() ?? "-", icon: Sigma, tone: "violet" },
  { label: "预估成本", value: data.value ? formatCost(data.value.summary.estimated_cost) : "-", icon: CircleDollarSign, tone: "green" },
  { label: "平均耗时", value: data.value ? `${data.value.summary.average_latency_ms} ms` : "-", icon: Clock3, tone: "cyan" },
]);
const operationLabels: Record<string, string> = { document_answer: "单文档问答", knowledge_base_answer: "知识库问答", query_rewrite: "查询改写", summarize: "文档总结", extract: "信息抽取", table_query: "表格问答" };
function formatCost(value: number) { return `${value.toFixed(6)} 元`; }
function formatDate(value: string) { return new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)); }
function operationLabel(value: string) { return operationLabels[value] ?? value; }
async function load() {
  if (!auth.token) return;
  loading.value = true; error.value = "";
  try { data.value = await getModelUsageAnalytics(auth.token, days.value); }
  catch (caught) { error.value = caught instanceof Error ? caught.message : "加载模型用量失败。"; }
  finally { loading.value = false; }
}
onMounted(load);
</script>

<template>
  <AdminLayout><section class="page-shell admin-page" aria-labelledby="usage-title">
    <header class="page-header"><div><p class="eyebrow">模型治理</p><h1 id="usage-title">模型用量与成本</h1><p>统计实际模型调用的 Token、耗时和按模型单价计算的预估成本，不保存问题、答案或密钥。</p></div><div class="page-header-actions"><el-select v-model="days" aria-label="统计时间范围" @change="load"><el-option :value="7" label="最近 7 天"/><el-option :value="30" label="最近 30 天"/><el-option :value="90" label="最近 90 天"/></el-select><el-button :icon="RefreshCw" :loading="loading" @click="load">刷新</el-button></div></header>
    <el-alert v-if="error" class="form-alert" type="error" :title="error" show-icon />
    <section class="dashboard-metric-grid" aria-label="模型用量指标" v-loading="loading"><article v-for="metric in metrics" :key="metric.label" class="dashboard-metric" :class="`metric-${metric.tone}`"><span class="metric-icon"><component :is="metric.icon" :size="21" /></span><div><span>{{ metric.label }}</span><strong>{{ metric.value }}</strong></div></article></section>
    <section class="table-surface" v-loading="loading"><div class="section-heading"><div><p class="eyebrow">按模型汇总</p><h2>调用质量与成本</h2></div><span class="section-caption">未配置单价或服务未返回 Token 的调用不会计入成本</span></div><el-table :data="data?.by_provider ?? []" empty-text="当前时间范围内没有模型调用"><el-table-column prop="provider_slug" label="服务" min-width="120"/><el-table-column prop="model_name" label="模型" min-width="160"/><el-table-column prop="successful_requests" label="成功" width="85"/><el-table-column prop="failed_requests" label="失败" width="85"/><el-table-column prop="total_tokens" label="Token" min-width="120"><template #default="{ row }">{{ row.total_tokens.toLocaleString() }}</template></el-table-column><el-table-column label="预估成本" min-width="130"><template #default="{ row }">{{ row.cost_known_requests ? formatCost(row.estimated_cost) : "未配置" }}</template></el-table-column><el-table-column prop="average_latency_ms" label="平均耗时" min-width="110"><template #default="{ row }">{{ row.average_latency_ms }} ms</template></el-table-column></el-table></section>
    <section class="table-surface" v-loading="loading"><div class="section-heading"><div><p class="eyebrow">调用明细</p><h2>最近调用记录</h2></div><span class="section-caption">仅管理员可见</span></div><el-table :data="data?.items ?? []" empty-text="暂无调用记录"><el-table-column label="时间" min-width="165"><template #default="{ row }">{{ formatDate(row.created_at) }}</template></el-table-column><el-table-column prop="username" label="用户" min-width="100"><template #default="{ row }">{{ row.username ?? "系统" }}</template></el-table-column><el-table-column prop="knowledge_base_name" label="知识库" min-width="120"><template #default="{ row }">{{ row.knowledge_base_name ?? "-" }}</template></el-table-column><el-table-column label="操作" min-width="120"><template #default="{ row }">{{ operationLabel(row.operation) }}</template></el-table-column><el-table-column label="模型" min-width="150"><template #default="{ row }">{{ row.provider_slug }} / {{ row.model_name }}</template></el-table-column><el-table-column label="Token" min-width="100"><template #default="{ row }">{{ row.total_tokens?.toLocaleString() ?? "未返回" }}</template></el-table-column><el-table-column label="成本" min-width="110"><template #default="{ row }">{{ row.estimated_cost === null ? "未配置" : formatCost(row.estimated_cost) }}</template></el-table-column><el-table-column label="结果" width="100"><template #default="{ row }"><el-tag :type="row.success ? 'success' : 'danger'">{{ row.success ? "成功" : "失败" }}</el-tag></template></el-table-column><el-table-column label="耗时" width="100"><template #default="{ row }">{{ row.latency_ms }} ms</template></el-table-column></el-table></section>
  </section></AdminLayout>
</template>
