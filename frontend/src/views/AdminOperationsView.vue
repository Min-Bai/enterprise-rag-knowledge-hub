<script setup lang="ts">
import { onMounted, ref } from "vue";
import { getOverview, getWorkerStatus } from "../api/admin";
import { useAdminAuthStore } from "../stores/adminAuth";
import AdminLayout from "../layouts/AdminLayout.vue";
const auth = useAdminAuthStore(); const overview = ref<{ users: number; knowledge_bases: number; documents: number; ready_documents: number }>(); const worker = ref<{ registered_workers: string[]; active_tasks: number; reserved_tasks: number }>(); const error = ref("");
onMounted(async () => { if (!auth.token) return; try { [overview.value, worker.value] = await Promise.all([getOverview(auth.token), getWorkerStatus(auth.token)]); } catch (cause) { error.value = cause instanceof Error ? cause.message : "加载失败"; } });
</script>
<template><AdminLayout><section class="page-shell"><header class="page-header"><div><h1>运行概览</h1><p>实时读取系统资源与任务队列状态</p></div></header><p v-if="error" class="form-error">{{ error }}</p><div v-else class="metric-grid"><article><span>用户</span><strong>{{ overview?.users ?? "-" }}</strong></article><article><span>知识库</span><strong>{{ overview?.knowledge_bases ?? "-" }}</strong></article><article><span>文档</span><strong>{{ overview?.documents ?? "-" }}</strong></article><article><span>已就绪文档</span><strong>{{ overview?.ready_documents ?? "-" }}</strong></article><article><span>在线 Worker</span><strong>{{ worker?.registered_workers.length ?? "-" }}</strong></article><article><span>执行中任务</span><strong>{{ worker?.active_tasks ?? "-" }}</strong></article></div></section></AdminLayout></template>
