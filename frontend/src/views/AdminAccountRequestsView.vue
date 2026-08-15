<script setup lang="ts">
import { onMounted, ref } from "vue";
import { Copy, RefreshCw } from "lucide-vue-next";
import { ElMessage, ElMessageBox } from "element-plus";
import { approvePasswordResetRequest, approveRegistrationRequest, getPasswordResetRequests, getRegistrationRequests, rejectRegistrationRequest, type PasswordResetRequest, type RegistrationRequest } from "../api/admin";
import { useAdminAuthStore } from "../stores/adminAuth";
import AdminLayout from "../layouts/AdminLayout.vue";

const auth = useAdminAuthStore();
const registrations = ref<RegistrationRequest[]>([]);
const resets = ref<PasswordResetRequest[]>([]);
const loading = ref(false);
const saving = ref(false);
const error = ref("");
const resetUrl = ref("");
const resetDialogOpen = ref(false);

async function load() {
  if (!auth.token) return;
  loading.value = true; error.value = "";
  try {
    [registrations.value, resets.value] = await Promise.all([
      getRegistrationRequests(auth.token), getPasswordResetRequests(auth.token),
    ]);
  } catch (caught) { error.value = caught instanceof Error ? caught.message : "加载账户申请失败。"; }
  finally { loading.value = false; }
}
async function approveRegistration(item: RegistrationRequest) {
  if (!auth.token) return;
  try {
    await ElMessageBox.confirm(`批准 ${item.username} 的注册申请后会立即创建账号。确认批准吗？`, "批准注册申请", { type: "warning" });
    saving.value = true;
    await approveRegistrationRequest(auth.token, item.id);
    item.status = "approved"; item.reviewed_at = new Date().toISOString();
    ElMessage.success("账号已创建，用户现在可以登录。");
  } catch (caught) { if (caught !== "cancel" && caught !== "close") ElMessage.error(caught instanceof Error ? caught.message : "批准失败。"); }
  finally { saving.value = false; }
}
async function rejectRegistration(item: RegistrationRequest) {
  if (!auth.token) return;
  try {
    const { value } = await ElMessageBox.prompt("可选填写拒绝原因。", "拒绝注册申请", { inputPlaceholder: "例如：请使用企业邮箱重新提交" });
    saving.value = true;
    await rejectRegistrationRequest(auth.token, item.id, value || undefined);
    item.status = "rejected"; item.rejection_reason = value || null; item.reviewed_at = new Date().toISOString();
    ElMessage.success("注册申请已拒绝");
  } catch (caught) { if (caught !== "cancel" && caught !== "close") ElMessage.error(caught instanceof Error ? caught.message : "拒绝失败。"); }
  finally { saving.value = false; }
}
async function approveReset(item: PasswordResetRequest) {
  if (!auth.token) return;
  try {
    await ElMessageBox.confirm(`为 ${item.email} 生成 24 小时有效的一次性密码重置链接吗？`, "批准重置申请", { type: "warning" });
    saving.value = true;
    const result = await approvePasswordResetRequest(auth.token, item.id, 24);
    item.status = "approved"; item.reviewed_at = new Date().toISOString();
    resetUrl.value = `${window.location.origin}/password-reset?token=${encodeURIComponent(result.reset_token)}`;
    resetDialogOpen.value = true;
  } catch (caught) { if (caught !== "cancel" && caught !== "close") ElMessage.error(caught instanceof Error ? caught.message : "生成链接失败。"); }
  finally { saving.value = false; }
}
async function copyResetUrl() { try { await navigator.clipboard.writeText(resetUrl.value); ElMessage.success("密码重置链接已复制"); } catch { ElMessage.error("无法自动复制，请手动复制链接。"); } }
onMounted(load);
</script>
<template><AdminLayout><section class="page-shell admin-page"><header class="page-header"><div><p class="eyebrow">访问控制</p><h1>账户审批</h1><p>审核客户端注册和密码重置申请。重置链接只会显示一次，应通过受控渠道发送。</p></div><el-button :icon="RefreshCw" circle title="刷新申请列表" :loading="loading" @click="load" /></header><el-alert v-if="error" class="form-alert" type="error" :title="error" show-icon/><section class="table-surface"><div class="section-heading"><div><h2>注册申请</h2><p>批准后创建普通成员账号和默认知识库。</p></div></div><el-table v-loading="loading" :data="registrations" empty-text="暂无注册申请" class="data-table"><el-table-column prop="username" label="用户名" min-width="150"/><el-table-column prop="email" label="邮箱" min-width="220"/><el-table-column label="状态" width="110"><template #default="{ row }"><el-tag :type="row.status === 'pending' ? 'warning' : row.status === 'approved' ? 'success' : 'info'">{{ row.status === 'pending' ? '待审批' : row.status === 'approved' ? '已批准' : '已拒绝' }}</el-tag></template></el-table-column><el-table-column label="申请时间" min-width="180"><template #default="{ row }">{{ new Date(row.created_at).toLocaleString() }}</template></el-table-column><el-table-column label="操作" width="150" fixed="right"><template #default="{ row }"><template v-if="row.status === 'pending'"><el-button link type="primary" :disabled="saving" @click="approveRegistration(row)">批准</el-button><el-button link type="danger" :disabled="saving" @click="rejectRegistration(row)">拒绝</el-button></template></template></el-table-column></el-table></section><section class="table-surface invitation-surface"><div class="section-heading"><div><h2>密码重置申请</h2><p>批准后生成一次性限时链接；新链接会自动撤销该用户旧的未使用链接。</p></div></div><el-table v-loading="loading" :data="resets" empty-text="暂无密码重置申请" class="data-table"><el-table-column prop="email" label="注册邮箱" min-width="220"/><el-table-column label="状态" width="110"><template #default="{ row }"><el-tag :type="row.status === 'pending' ? 'warning' : 'success'">{{ row.status === 'pending' ? '待审批' : '已处理' }}</el-tag></template></el-table-column><el-table-column label="申请时间" min-width="180"><template #default="{ row }">{{ new Date(row.created_at).toLocaleString() }}</template></el-table-column><el-table-column label="操作" width="120" fixed="right"><template #default="{ row }"><el-button v-if="row.status === 'pending'" link type="primary" :disabled="saving" @click="approveReset(row)">生成链接</el-button></template></el-table-column></el-table></section><el-dialog v-model="resetDialogOpen" title="密码重置链接" width="min(92vw, 560px)" @closed="resetUrl = ''"><el-alert type="warning" :closable="false" title="请立即复制并通过受控渠道发送。关闭此窗口后，系统不会再次显示此链接。"/><el-input class="invitation-url" :model-value="resetUrl" readonly><template #append><el-button :icon="Copy" title="复制密码重置链接" @click="copyResetUrl">复制</el-button></template></el-input><template #footer><el-button @click="resetDialogOpen = false">关闭</el-button></template></el-dialog></section></AdminLayout></template>
