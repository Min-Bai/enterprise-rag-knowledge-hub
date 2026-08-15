<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Plus, RefreshCw, Trash2 } from "lucide-vue-next";
import { createAdminUser, deleteAdminUser, getAdminUsers, setUserRole, setUserStatus } from "../api/admin";
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
onMounted(() => load());
</script>

<template>
  <AdminLayout><section class="page-shell admin-page">
    <header class="page-header"><div><p class="eyebrow">访问控制</p><h1>用户管理</h1><p>创建、授权、停用和清理平台账号。停用后该账号现有会话会立即失效。</p></div><el-button type="primary" @click="createOpen = true"><Plus :size="16" /> 新建用户</el-button></header>
    <el-alert v-if="error" class="form-alert" type="error" :title="error" show-icon />
    <section class="table-surface"><div class="table-toolbar admin-toolbar"><el-input v-model="query" clearable placeholder="搜索账号或邮箱" /><el-select v-model="roleFilter" aria-label="角色筛选"><el-option label="全部角色" value="all"/><el-option label="管理员" value="admin"/><el-option label="普通用户" value="user"/></el-select><el-select v-model="statusFilter" aria-label="状态筛选"><el-option label="全部状态" value="all"/><el-option label="已启用" value="active"/><el-option label="已停用" value="inactive"/></el-select><el-button :icon="RefreshCw" circle title="刷新用户列表" :loading="loading" @click="load()" /></div>
      <el-table v-loading="loading" :data="filteredUsers" empty-text="没有符合条件的用户" class="data-table admin-users-table"><el-table-column prop="username" label="账号" min-width="160"/><el-table-column prop="email" label="邮箱" min-width="220"><template #default="{ row }">{{ row.email || "未填写" }}</template></el-table-column><el-table-column label="角色" width="150"><template #default="{ row }"><el-select :model-value="row.role" :disabled="saving || row.id === auth.user?.id" aria-label="修改用户角色" @change="changeRole(row, $event as UserRole)"><el-option label="普通用户" value="user"/><el-option label="管理员" value="admin"/></el-select></template></el-table-column><el-table-column label="状态" width="115"><template #default="{ row }"><el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? "已启用" : "已停用" }}</el-tag></template></el-table-column><el-table-column label="操作" width="190" fixed="right"><template #default="{ row }"><el-button link type="primary" :disabled="saving || row.id === auth.user?.id" @click="changeStatus(row)">{{ row.is_active ? "停用" : "启用" }}</el-button><el-button link type="danger" :disabled="saving || row.id === auth.user?.id" @click="removeUser(row)"><Trash2 :size="15" /> 删除</el-button></template></el-table-column></el-table>
      <div class="table-load-more"><el-button v-if="nextCursor" :loading="loading" @click="load(true)">加载更多</el-button></div>
    </section>
    <el-dialog v-model="createOpen" title="新建用户" width="min(92vw, 480px)" :close-on-click-modal="!saving"><el-form label-position="top" @submit.prevent="createUser"><el-form-item label="账号" required><el-input v-model="form.username" maxlength="50" autocomplete="off"/></el-form-item><el-form-item label="邮箱"><el-input v-model="form.email" type="email" autocomplete="off"/></el-form-item><el-form-item label="初始密码" required><el-input v-model="form.password" type="password" show-password minlength="6" autocomplete="new-password"/></el-form-item><el-form-item label="角色"><el-radio-group v-model="form.role"><el-radio-button value="user">普通用户</el-radio-button><el-radio-button value="admin">管理员</el-radio-button></el-radio-group></el-form-item></el-form><template #footer><el-button :disabled="saving" @click="createOpen = false">取消</el-button><el-button type="primary" :loading="saving" :disabled="!form.username.trim() || form.password.length < 6" @click="createUser">创建用户</el-button></template></el-dialog>
  </section></AdminLayout>
</template>
