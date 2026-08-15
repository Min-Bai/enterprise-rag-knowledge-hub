<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { getAdminUsers, setUserRole, setUserStatus } from "../api/admin";
import { useAdminAuthStore } from "../stores/adminAuth";
import type { User, UserRole } from "../types/api";
import AdminLayout from "../layouts/AdminLayout.vue";
const auth = useAdminAuthStore(); const users = ref<User[]>([]); const nextCursor = ref<number | null>(null); const loading = ref(false);
async function load(more = false) { if (!auth.token) return; loading.value = true; try { const data = await getAdminUsers(auth.token, more ? nextCursor.value ?? undefined : undefined); users.value = more ? [...users.value, ...data.items] : data.items; nextCursor.value = data.page.next_cursor; } finally { loading.value = false; } }
async function changeRole(user: User, role: UserRole) { if (!auth.token || role === user.role) return; await ElMessageBox.confirm(`确认将 ${user.username} 设为 ${role === "admin" ? "管理员" : "普通用户"}？`, "变更角色"); const updated = await setUserRole(auth.token, user.id, role); Object.assign(user, updated); ElMessage.success("角色已更新"); }
async function changeStatus(user: User) { if (!auth.token) return; await ElMessageBox.confirm(`确认${user.is_active ? "停用" : "启用"} ${user.username}？`, "变更状态"); const updated = await setUserStatus(auth.token, user.id, !user.is_active); Object.assign(user, updated); ElMessage.success("状态已更新"); }
onMounted(() => load());
</script>
<template><AdminLayout><section class="page-shell"><header class="page-header"><div><h1>用户管理</h1><p>管理系统访问状态与管理员权限</p></div></header><el-table v-loading="loading" :data="users" empty-text="暂无用户"><el-table-column prop="username" label="账号" /><el-table-column prop="email" label="邮箱" /><el-table-column label="角色"><template #default="{ row }"><el-select :model-value="row.role" @change="changeRole(row, $event as UserRole)"><el-option label="普通用户" value="user" /><el-option label="管理员" value="admin" /></el-select></template></el-table-column><el-table-column label="状态"><template #default="{ row }"><el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? "启用" : "停用" }}</el-tag></template></el-table-column><el-table-column label="操作"><template #default="{ row }"><button class="text-button" type="button" @click="changeStatus(row)">{{ row.is_active ? "停用" : "启用" }}</button></template></el-table-column></el-table><div class="table-footer"><button v-if="nextCursor" class="secondary-button" :disabled="loading" @click="load(true)">加载更多</button></div></section></AdminLayout></template>
