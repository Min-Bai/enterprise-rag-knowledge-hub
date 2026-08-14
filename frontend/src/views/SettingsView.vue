<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { deactivateUser, getUsers, updateUserRole } from "../api/users";
import AppEmpty from "../components/common/AppEmpty.vue";
import AppLayout from "../layouts/AppLayout.vue";
import { useAuthStore } from "../stores/auth";
import type { User, UserRole } from "../types/api";
const auth = useAuthStore();
const users = ref<User[]>([]);
const loading = ref(true);
const error = ref("");
async function load() {
  if (!auth.token) return;
  loading.value = true;
  try {
    users.value = await getUsers(auth.token);
  } catch (caught) {
    error.value =
      caught instanceof Error ? caught.message : "加载用户失败，请稍后重试。";
  } finally {
    loading.value = false;
  }
}
async function changeRole(user: User, role: UserRole) {
  if (!auth.token || user.role === role || user.id === auth.user?.id) return;
  try {
    const updated = await updateUserRole(auth.token, user.id, role);
    users.value = users.value.map((item) =>
      item.id === user.id ? updated : item,
    );
    ElMessage.success("用户角色已更新");
  } catch (caught) {
    ElMessage.error(
      caught instanceof Error ? caught.message : "更新角色失败，请稍后重试。",
    );
  }
}
async function deactivate(user: User) {
  if (!auth.token) return;
  try {
    const updated = await deactivateUser(auth.token, user.id);
    users.value = users.value.map((item) =>
      item.id === user.id ? updated : item,
    );
    ElMessage.success("账号已停用");
  } catch (caught) {
    ElMessage.error(
      caught instanceof Error ? caught.message : "停用账号失败，请稍后重试。",
    );
  }
}
onMounted(load);
</script>
<template>
  <AppLayout
    ><section class="page-shell">
      <header class="page-header">
        <div>
          <p class="eyebrow">系统设置</p>
          <h1>用户与角色</h1>
          <p>系统管理员可以调整企业账户的系统角色和启用状态。</p>
        </div>
      </header>
      <el-alert
        v-if="error"
        class="form-alert"
        type="error"
        :title="error"
        show-icon
      />
      <section class="table-surface">
        <el-skeleton v-if="loading" :rows="6" animated /><AppEmpty
          v-else-if="users.length === 0"
          title="没有用户数据"
          description="当前没有可管理的系统账户。"
        /><el-table v-else :data="users"
          ><el-table-column
            prop="username"
            label="用户名"
            min-width="180"
          /><el-table-column prop="email" label="邮箱" min-width="200"
            ><template #default="{ row }">{{
              row.email || "未设置"
            }}</template></el-table-column
          ><el-table-column label="系统角色" width="170"
            ><template #default="{ row }"
              ><el-select
                :model-value="row.role"
                size="small"
                :disabled="row.id === auth.user?.id"
                @update:model-value="changeRole(row, $event)"
                ><el-option label="系统管理员" value="admin" /><el-option
                  label="企业成员"
                  value="user" /></el-select></template></el-table-column
          ><el-table-column label="状态" width="110"
            ><template #default="{ row }"
              ><el-tag :type="row.is_active ? 'success' : 'info'">{{
                row.is_active ? "启用" : "已停用"
              }}</el-tag></template
            ></el-table-column
          ><el-table-column label="操作" width="110"
            ><template #default="{ row }"
              ><el-popconfirm
                v-if="row.is_active && row.id !== auth.user?.id"
                title="停用后该用户无法登录，确定继续吗？"
                confirm-button-text="停用"
                cancel-button-text="取消"
                @confirm="deactivate(row)"
                ><template #reference
                  ><el-button link type="danger">停用</el-button></template
                ></el-popconfirm
              ></template
            ></el-table-column
          ></el-table
        >
      </section>
    </section></AppLayout
  >
</template>
