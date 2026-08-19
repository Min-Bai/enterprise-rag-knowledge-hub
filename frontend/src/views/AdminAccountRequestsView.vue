<script setup lang="ts">
import { onMounted, ref } from "vue";
import { RefreshCw, Trash2 } from "lucide-vue-next";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  approvePasswordResetRequest,
  approveRegistrationRequest,
  deletePasswordResetRequest,
  deletePasswordResetRequests,
  deleteRegistrationRequest,
  deleteRegistrationRequests,
  getPasswordResetRequests,
  getRegistrationRequests,
  rejectRegistrationRequest,
  type PasswordResetRequest,
  type RegistrationRequest,
} from "../api/admin";
import { useAdminAuthStore } from "../stores/adminAuth";
import AdminLayout from "../layouts/AdminLayout.vue";

const auth = useAdminAuthStore();
const registrations = ref<RegistrationRequest[]>([]);
const resets = ref<PasswordResetRequest[]>([]);
const loading = ref(false);
const saving = ref(false);
const error = ref("");
const selectedRegistrations = ref<RegistrationRequest[]>([]);
const selectedResets = ref<PasswordResetRequest[]>([]);

async function load() {
  if (!auth.token) return;
  loading.value = true;
  error.value = "";
  try {
    [registrations.value, resets.value] = await Promise.all([
      getRegistrationRequests(auth.token),
      getPasswordResetRequests(auth.token),
    ]);
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "加载申请失败，请稍后重试。";
  } finally {
    loading.value = false;
  }
}

function isCancelled(value: unknown) {
  return value === "cancel" || value === "close";
}

async function approveRegistration(item: RegistrationRequest) {
  if (!auth.token) return;
  try {
    await ElMessageBox.confirm(`批准后将为 ${item.username} 创建账号，确认继续吗？`, "批准注册申请", { type: "warning" });
    saving.value = true;
    await approveRegistrationRequest(auth.token, item.id);
    await load();
    ElMessage.success("注册申请已批准，账号已经创建。\n");
  } catch (caught) {
    if (!isCancelled(caught)) ElMessage.error(caught instanceof Error ? caught.message : "批准注册申请失败。\n");
  } finally {
    saving.value = false;
  }
}

async function rejectRegistration(item: RegistrationRequest) {
  if (!auth.token) return;
  try {
    const { value } = await ElMessageBox.prompt("可以填写拒绝原因，方便申请人修改后重新提交。", "拒绝注册申请", { inputPlaceholder: "例如：请使用企业邮箱重新提交" });
    saving.value = true;
    await rejectRegistrationRequest(auth.token, item.id, value || undefined);
    await load();
    ElMessage.success("注册申请已拒绝。\n");
  } catch (caught) {
    if (!isCancelled(caught)) ElMessage.error(caught instanceof Error ? caught.message : "拒绝注册申请失败。\n");
  } finally {
    saving.value = false;
  }
}

async function approveReset(item: PasswordResetRequest) {
  if (!auth.token) return;
  try {
    await ElMessageBox.confirm(`系统将向 ${item.email} 发送 24 小时有效的密码重置邮件，确认发送吗？`, "批准密码重置申请", { type: "warning" });
    saving.value = true;
    const result = await approvePasswordResetRequest(auth.token, item.id, 24);
    await load();
    ElMessage.success(`重置邮件已发送，有效期至 ${new Date(result.expires_at).toLocaleString("zh-CN")}。`);
  } catch (caught) {
    if (!isCancelled(caught)) ElMessage.error(caught instanceof Error ? caught.message : "重置邮件发送失败。\n");
  } finally {
    saving.value = false;
  }
}

async function removeRegistration(item: RegistrationRequest) {
  if (!auth.token) return;
  try {
    await ElMessageBox.confirm("删除后将不再显示这条注册申请，确认删除吗？", "删除注册申请", { type: "warning" });
    saving.value = true;
    await deleteRegistrationRequest(auth.token, item.id);
    registrations.value = registrations.value.filter((row) => row.id !== item.id);
    ElMessage.success("注册申请已删除。\n");
  } catch (caught) {
    if (!isCancelled(caught)) ElMessage.error(caught instanceof Error ? caught.message : "删除注册申请失败。\n");
  } finally {
    saving.value = false;
  }
}

async function removeReset(item: PasswordResetRequest) {
  if (!auth.token) return;
  try {
    await ElMessageBox.confirm("删除后将不再显示这条密码重置申请，确认删除吗？", "删除密码重置申请", { type: "warning" });
    saving.value = true;
    await deletePasswordResetRequest(auth.token, item.id);
    resets.value = resets.value.filter((row) => row.id !== item.id);
    ElMessage.success("密码重置申请已删除。\n");
  } catch (caught) {
    if (!isCancelled(caught)) ElMessage.error(caught instanceof Error ? caught.message : "删除密码重置申请失败。\n");
  } finally {
    saving.value = false;
  }
}

async function removeRegistrations() {
  if (!auth.token || selectedRegistrations.value.length === 0) return;
  try {
    await ElMessageBox.confirm(`将删除选中的 ${selectedRegistrations.value.length} 条注册申请记录，确认继续吗？`, "批量删除注册申请", { type: "warning" });
    saving.value = true;
    const ids = selectedRegistrations.value.map((item) => item.id);
    await deleteRegistrationRequests(auth.token, ids);
    registrations.value = registrations.value.filter((item) => !ids.includes(item.id));
    selectedRegistrations.value = [];
    ElMessage.success("注册申请已批量删除");
  } catch (caught) {
    if (!isCancelled(caught)) ElMessage.error(caught instanceof Error ? caught.message : "批量删除注册申请失败。");
  } finally { saving.value = false; }
}

async function removeResets() {
  if (!auth.token || selectedResets.value.length === 0) return;
  try {
    await ElMessageBox.confirm(`将删除选中的 ${selectedResets.value.length} 条密码重置申请记录，确认继续吗？`, "批量删除密码重置申请", { type: "warning" });
    saving.value = true;
    const ids = selectedResets.value.map((item) => item.id);
    await deletePasswordResetRequests(auth.token, ids);
    resets.value = resets.value.filter((item) => !ids.includes(item.id));
    selectedResets.value = [];
    ElMessage.success("密码重置申请已批量删除");
  } catch (caught) {
    if (!isCancelled(caught)) ElMessage.error(caught instanceof Error ? caught.message : "批量删除密码重置申请失败。");
  } finally { saving.value = false; }
}

function formatDate(value: string) { return new Date(value).toLocaleString("zh-CN"); }
onMounted(load);
</script>

<template>
  <AdminLayout>
    <section class="page-shell admin-page">
      <header class="page-header">
        <div><p class="eyebrow">访问控制</p><h1>账号审批</h1><p>审核注册和密码重置申请。已处理的记录可以删除，删除不会影响审计日志。</p></div>
        <el-button :icon="RefreshCw" circle title="刷新申请列表" :loading="loading" @click="load" />
      </header>
      <el-alert v-if="error" class="form-alert" type="error" :title="error" show-icon />

      <section class="table-surface">
        <div class="section-heading"><div><h2>注册申请</h2><p>批准后创建普通成员账号；拒绝后可删除历史记录。</p></div><el-button type="danger" :disabled="saving || selectedRegistrations.length === 0" @click="removeRegistrations"><Trash2 :size="15" />批量删除</el-button></div>
        <el-table v-loading="loading" :data="registrations" empty-text="暂无注册申请" class="data-table" @selection-change="selectedRegistrations = $event">
          <el-table-column type="selection" width="48" />
          <el-table-column prop="username" label="用户名" min-width="150" />
          <el-table-column prop="email" label="邮箱" min-width="220" />
          <el-table-column label="状态" width="110"><template #default="{ row }"><el-tag :type="row.status === 'pending' ? 'warning' : row.status === 'approved' ? 'success' : 'info'">{{ row.status === "pending" ? "待审批" : row.status === "approved" ? "已批准" : "已拒绝" }}</el-tag></template></el-table-column>
          <el-table-column label="申请时间" min-width="180"><template #default="{ row }">{{ formatDate(row.created_at) }}</template></el-table-column>
          <el-table-column label="操作" min-width="210" fixed="right"><template #default="{ row }"><el-button v-if="row.status === 'pending'" link type="primary" :disabled="saving" @click="approveRegistration(row)">批准</el-button><el-button v-if="row.status === 'pending'" link type="danger" :disabled="saving" @click="rejectRegistration(row)">拒绝</el-button><el-button link type="danger" :icon="Trash2" :disabled="saving" title="删除申请记录" @click="removeRegistration(row)">删除</el-button></template></el-table-column>
        </el-table>
      </section>

      <section class="table-surface invitation-surface">
        <div class="section-heading"><div><h2>密码重置申请</h2><p>批准后向申请邮箱发送一次性重置链接；已处理或无效申请可以删除。</p></div><el-button type="danger" :disabled="saving || selectedResets.length === 0" @click="removeResets"><Trash2 :size="15" />批量删除</el-button></div>
        <el-table v-loading="loading" :data="resets" empty-text="暂无密码重置申请" class="data-table" @selection-change="selectedResets = $event">
          <el-table-column type="selection" width="48" />
          <el-table-column prop="email" label="申请邮箱" min-width="220" />
          <el-table-column label="状态" width="110"><template #default="{ row }"><el-tag :type="row.status === 'pending' ? 'warning' : 'success'">{{ row.status === "pending" ? "待审批" : "已处理" }}</el-tag></template></el-table-column>
          <el-table-column label="申请时间" min-width="180"><template #default="{ row }">{{ formatDate(row.created_at) }}</template></el-table-column>
          <el-table-column label="操作" min-width="230" fixed="right"><template #default="{ row }"><el-button v-if="row.status === 'pending'" link type="primary" :disabled="saving" @click="approveReset(row)">批准并发送邮件</el-button><el-button link type="danger" :icon="Trash2" :disabled="saving" title="删除申请记录" @click="removeReset(row)">删除</el-button></template></el-table-column>
        </el-table>
      </section>
    </section>
  </AdminLayout>
</template>
