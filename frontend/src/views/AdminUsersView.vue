<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Copy, Plus, RefreshCw, Send, Trash2 } from "lucide-vue-next";
import { createAdminUser, createPasswordResetLink, createUserInvitation, deleteAdminUser, getAdminUsers, getUserInvitations, revokeUserInvitation, setUserRole, setUserStatus, type UserInvitation } from "../api/admin";
import { useAdminAuthStore } from "../stores/adminAuth";
import type { User, UserRole } from "../types/api";
import AdminLayout from "../layouts/AdminLayout.vue";

const auth = useAdminAuthStore();
const users = ref<User[]>([]);
const nextCursor = ref<number | null>(null);
const loading = ref(false);
const saving = ref(false);
const error = ref("");
const query = ref("");
const roleFilter = ref<"all" | UserRole>("all");
const statusFilter = ref<"all" | "active" | "inactive">("all");
const createOpen = ref(false);
const form = ref({ username: "", email: "", password: "", role: "user" as UserRole });
const inviteOpen = ref(false);
const inviteForm = ref({ email: "", expiresInHours: 168 });
const invitations = ref<UserInvitation[]>([]);
const invitationUrl = ref("");
const passwordResetOpen = ref(false);
const resetTarget = ref<User | null>(null);
const resetExpiresInHours = ref(24);
const passwordResetUrl = ref("");

const filteredUsers = computed(() => users.value.filter((user) => {
  const keyword = query.value.trim().toLowerCase();
  return (!keyword || user.username.toLowerCase().includes(keyword) || user.email?.toLowerCase().includes(keyword))
    && (roleFilter.value === "all" || user.role === roleFilter.value)
    && (statusFilter.value === "all" || (statusFilter.value === "active" ? user.is_active : !user.is_active));
}));

async function load(more = false) {
  if (!auth.token) return;
  loading.value = true;
  error.value = "";
  try {
    const data = await getAdminUsers(auth.token, more ? nextCursor.value ?? undefined : undefined);
    users.value = more ? [...users.value, ...data.items] : data.items;
    nextCursor.value = data.page.next_cursor;
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "加载用户失败，请稍后重试。";
  } finally { loading.value = false; }
}
async function loadInvitations() {
  if (!auth.token) return;
  try {
    invitations.value = await getUserInvitations(auth.token);
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "加载邀请记录失败，请稍后重试。";
  }
}
async function createInvitation() {
  if (!auth.token || !inviteForm.value.email.trim()) return;
  saving.value = true;
  try {
    const invitation = await createUserInvitation(auth.token, {
      email: inviteForm.value.email.trim(),
      expires_in_hours: inviteForm.value.expiresInHours,
    });
    invitations.value = [invitation, ...invitations.value];
    invitationUrl.value = `${window.location.origin}/register?invite=${encodeURIComponent(invitation.invitation_token)}`;
    inviteForm.value = { email: "", expiresInHours: 168 };
    ElMessage.success("邀请链接已生成，请安全地发送给受邀人。");
  } catch (caught) {
    ElMessage.error(caught instanceof Error ? caught.message : "创建邀请失败。");
  } finally { saving.value = false; }
}
async function copyInvitation() {
  try {
    await navigator.clipboard.writeText(invitationUrl.value);
    ElMessage.success("邀请链接已复制");
  } catch {
    ElMessage.error("无法自动复制，请手动复制链接。");
  }
}
async function revokeInvitation(invitation: UserInvitation) {
  if (!auth.token) return;
  try {
    await ElMessageBox.confirm(`撤销发往 ${invitation.email} 的邀请后，该链接将立即失效。确认撤销吗？`, "撤销邀请", { type: "warning" });
    saving.value = true;
    await revokeUserInvitation(auth.token, invitation.id);
    invitation.revoked_at = new Date().toISOString();
    ElMessage.success("邀请已撤销");
  } catch (caught) {
    if (caught !== "cancel" && caught !== "close") ElMessage.error(caught instanceof Error ? caught.message : "撤销邀请失败。");
  } finally { saving.value = false; }
}
async function createPasswordReset() {
  if (!auth.token || !resetTarget.value) return;
  saving.value = true;
  try {
    const result = await createPasswordResetLink(auth.token, resetTarget.value.id, resetExpiresInHours.value);
    passwordResetUrl.value = `${window.location.origin}/password-reset?token=${encodeURIComponent(result.reset_token)}`;
    ElMessage.success("密码重置链接已生成，请通过受控渠道发送。");
  } catch (caught) {
    ElMessage.error(caught instanceof Error ? caught.message : "生成密码重置链接失败。");
  } finally { saving.value = false; }
}
async function copyPasswordResetLink() {
  try {
    await navigator.clipboard.writeText(passwordResetUrl.value);
    ElMessage.success("密码重置链接已复制");
  } catch {
    ElMessage.error("无法自动复制，请手动复制链接。");
  }
}
function openPasswordReset(user: User) {
  resetTarget.value = user;
  resetExpiresInHours.value = 24;
  passwordResetUrl.value = "";
  passwordResetOpen.value = true;
}
function invitationStatus(invitation: UserInvitation) {
  if (invitation.accepted_at) return "已接受";
  if (invitation.revoked_at) return "已撤销";
  if (new Date(invitation.expires_at).getTime() < Date.now()) return "已过期";
  return "待接受";
}
async function changeRole(user: User, role: UserRole) {
  if (!auth.token || role === user.role) return;
  try {
    await ElMessageBox.confirm(`确认将 ${user.username} 设置为${role === "admin" ? "管理员" : "普通用户"}吗？`, "变更角色", { type: "warning" });
    saving.value = true;
    Object.assign(user, await setUserRole(auth.token, user.id, role));
    ElMessage.success("角色已更新");
  } catch (caught) {
    if (caught !== "cancel" && caught !== "close") ElMessage.error(caught instanceof Error ? caught.message : "角色更新失败。");
  } finally { saving.value = false; }
}
async function changeStatus(user: User) {
  if (!auth.token) return;
  try {
    await ElMessageBox.confirm(`确认${user.is_active ? "停用" : "启用"} ${user.username} 吗？`, "变更账号状态", { type: "warning" });
    saving.value = true;
    Object.assign(user, await setUserStatus(auth.token, user.id, !user.is_active));
    ElMessage.success("账号状态已更新");
  } catch (caught) {
    if (caught !== "cancel" && caught !== "close") ElMessage.error(caught instanceof Error ? caught.message : "状态更新失败。");
  } finally { saving.value = false; }
}
async function createUser() {
  if (!auth.token || !form.value.username.trim() || !form.value.password) return;
  saving.value = true;
  try {
    const user = await createAdminUser(auth.token, { ...form.value, username: form.value.username.trim(), email: form.value.email.trim() || undefined });
    users.value = [user, ...users.value];
    createOpen.value = false;
    form.value = { username: "", email: "", password: "", role: "user" };
    ElMessage.success("用户已创建");
  } catch (caught) { ElMessage.error(caught instanceof Error ? caught.message : "创建用户失败。"); }
  finally { saving.value = false; }
}
async function removeUser(user: User) {
  if (!auth.token) return;
  try {
    await ElMessageBox.confirm(`删除 ${user.username} 后其账号将无法恢复。确认删除吗？`, "删除用户", { type: "error", confirmButtonText: "删除", cancelButtonText: "取消" });
    saving.value = true;
    await deleteAdminUser(auth.token, user.id);
    users.value = users.value.filter((item) => item.id !== user.id);
    ElMessage.success("用户已删除");
  } catch (caught) {
    if (caught !== "cancel" && caught !== "close") ElMessage.error(caught instanceof Error ? caught.message : "删除用户失败。");
  } finally { saving.value = false; }
}
onMounted(() => { load(); loadInvitations(); });
</script>

<template>
  <AdminLayout><section class="page-shell admin-page">
    <header class="page-header"><div><p class="eyebrow">访问控制</p><h1>用户管理</h1><p>邀请成员、授权、停用和清理平台账号。停用后该账号现有会话会立即失效。</p></div><div class="header-actions"><el-button @click="createOpen = true"><Plus :size="16" /> 直接新建</el-button><el-button type="primary" @click="inviteOpen = true"><Send :size="16" /> 邀请用户</el-button></div></header>
    <el-alert v-if="error" class="form-alert" type="error" :title="error" show-icon />
    <section class="table-surface"><div class="table-toolbar admin-toolbar"><el-input v-model="query" clearable placeholder="搜索账号或邮箱" /><el-select v-model="roleFilter" aria-label="角色筛选"><el-option label="全部角色" value="all"/><el-option label="管理员" value="admin"/><el-option label="普通用户" value="user"/></el-select><el-select v-model="statusFilter" aria-label="状态筛选"><el-option label="全部状态" value="all"/><el-option label="已启用" value="active"/><el-option label="已停用" value="inactive"/></el-select><el-button :icon="RefreshCw" circle title="刷新用户列表" :loading="loading" @click="load()" /></div>
      <el-table v-loading="loading" :data="filteredUsers" empty-text="没有符合条件的用户" class="data-table admin-users-table"><el-table-column prop="username" label="账号" min-width="160"/><el-table-column prop="email" label="邮箱" min-width="220"><template #default="{ row }">{{ row.email || "未填写" }}</template></el-table-column><el-table-column label="角色" width="150"><template #default="{ row }"><el-select :model-value="row.role" :disabled="saving || row.id === auth.user?.id" aria-label="修改用户角色" @change="changeRole(row, $event as UserRole)"><el-option label="普通用户" value="user"/><el-option label="管理员" value="admin"/></el-select></template></el-table-column><el-table-column label="状态" width="115"><template #default="{ row }"><el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? "已启用" : "已停用" }}</el-tag></template></el-table-column><el-table-column label="操作" width="260" fixed="right"><template #default="{ row }"><el-button link type="primary" :disabled="saving || !row.is_active" @click="openPasswordReset(row)">重置密码</el-button><el-button link type="primary" :disabled="saving || row.id === auth.user?.id" @click="changeStatus(row)">{{ row.is_active ? "停用" : "启用" }}</el-button><el-button link type="danger" :disabled="saving || row.id === auth.user?.id" @click="removeUser(row)"><Trash2 :size="15" /> 删除</el-button></template></el-table-column></el-table>
      <div class="table-load-more"><el-button v-if="nextCursor" :loading="loading" @click="load(true)">加载更多</el-button></div>
    </section>
    <section class="table-surface invitation-surface"><div class="section-heading"><div><h2>邀请记录</h2><p>链接只在创建时展示一次；请通过企业认可的渠道安全发送。</p></div><el-button :icon="RefreshCw" circle title="刷新邀请记录" :loading="loading" @click="loadInvitations" /></div><el-table :data="invitations" empty-text="暂无邀请记录" class="data-table"><el-table-column prop="email" label="受邀邮箱" min-width="220"/><el-table-column label="状态" width="110"><template #default="{ row }"><el-tag :type="invitationStatus(row) === '待接受' ? 'warning' : invitationStatus(row) === '已接受' ? 'success' : 'info'">{{ invitationStatus(row) }}</el-tag></template></el-table-column><el-table-column label="失效时间" min-width="180"><template #default="{ row }">{{ new Date(row.expires_at).toLocaleString() }}</template></el-table-column><el-table-column label="操作" width="110" fixed="right"><template #default="{ row }"><el-button v-if="invitationStatus(row) === '待接受'" link type="danger" :disabled="saving" @click="revokeInvitation(row)">撤销</el-button></template></el-table-column></el-table></section>
    <el-dialog v-model="createOpen" title="新建用户" width="min(92vw, 480px)" :close-on-click-modal="!saving"><el-form label-position="top" @submit.prevent="createUser"><el-form-item label="账号" required><el-input v-model="form.username" maxlength="50" autocomplete="off"/></el-form-item><el-form-item label="邮箱"><el-input v-model="form.email" type="email" autocomplete="off"/></el-form-item><el-form-item label="初始密码" required><el-input v-model="form.password" type="password" show-password minlength="6" autocomplete="new-password"/></el-form-item><el-form-item label="角色"><el-radio-group v-model="form.role"><el-radio-button value="user">普通用户</el-radio-button><el-radio-button value="admin">管理员</el-radio-button></el-radio-group></el-form-item></el-form><template #footer><el-button :disabled="saving" @click="createOpen = false">取消</el-button><el-button type="primary" :loading="saving" :disabled="!form.username.trim() || form.password.length < 6" @click="createUser">创建用户</el-button></template></el-dialog>
    <el-dialog v-model="inviteOpen" title="邀请用户" width="min(92vw, 520px)" :close-on-click-modal="!saving" @closed="invitationUrl = ''"><template v-if="!invitationUrl"><p class="dialog-hint">受邀用户将以普通成员身份注册。邀请默认七天有效，且可随时撤销。</p><el-form label-position="top" @submit.prevent="createInvitation"><el-form-item label="受邀邮箱" required><el-input v-model="inviteForm.email" type="email" autocomplete="email"/></el-form-item><el-form-item label="有效期"><el-select v-model="inviteForm.expiresInHours"><el-option label="24 小时" :value="24"/><el-option label="3 天" :value="72"/><el-option label="7 天" :value="168"/><el-option label="30 天" :value="720"/></el-select></el-form-item></el-form></template><template v-else><el-alert type="warning" :closable="false" title="请立即复制并通过安全渠道发送。关闭此窗口后，系统不会再次显示此链接。"/><el-input class="invitation-url" :model-value="invitationUrl" readonly><template #append><el-button :icon="Copy" title="复制邀请链接" @click="copyInvitation">复制</el-button></template></el-input></template><template #footer><el-button :disabled="saving" @click="inviteOpen = false">关闭</el-button><el-button v-if="!invitationUrl" type="primary" :loading="saving" :disabled="!inviteForm.email.trim()" @click="createInvitation">生成邀请链接</el-button></template></el-dialog>
    <el-dialog v-model="passwordResetOpen" title="生成密码重置链接" width="min(92vw, 520px)" :close-on-click-modal="!saving" @closed="passwordResetUrl = ''; resetTarget = null"><template v-if="!passwordResetUrl"><p class="dialog-hint">将为 {{ resetTarget?.username }} 生成一次性链接。生成新的链接会立即撤销该用户之前未使用的链接。</p><el-form label-position="top" @submit.prevent="createPasswordReset"><el-form-item label="有效期"><el-select v-model="resetExpiresInHours"><el-option label="1 小时" :value="1"/><el-option label="24 小时" :value="24"/><el-option label="3 天" :value="72"/><el-option label="7 天" :value="168"/></el-select></el-form-item></el-form></template><template v-else><el-alert type="warning" :closable="false" title="请立即复制并通过受控渠道发送。关闭此窗口后，系统不会再次显示此链接。"/><el-input class="invitation-url" :model-value="passwordResetUrl" readonly><template #append><el-button :icon="Copy" title="复制密码重置链接" @click="copyPasswordResetLink">复制</el-button></template></el-input></template><template #footer><el-button :disabled="saving" @click="passwordResetOpen = false">关闭</el-button><el-button v-if="!passwordResetUrl" type="primary" :loading="saving" @click="createPasswordReset">生成重置链接</el-button></template></el-dialog>
  </section></AdminLayout>
</template>
