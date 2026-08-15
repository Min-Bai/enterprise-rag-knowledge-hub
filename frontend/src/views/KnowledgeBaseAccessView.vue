<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { ArrowLeft, UserPlus } from "lucide-vue-next";
import {
  addKnowledgeBaseMember,
  getKnowledgeBaseMembers,
  removeKnowledgeBaseMember,
} from "../api/knowledgeBases";
import KnowledgeBaseTabs from "../components/knowledge-base/KnowledgeBaseTabs.vue";
import AppEmpty from "../components/common/AppEmpty.vue";
import AppLayout from "../layouts/AppLayout.vue";
import { useAuthStore } from "../stores/auth";
import { useRoute } from "vue-router";
import type { KnowledgeBaseMember } from "../types/api";
const route = useRoute();
const auth = useAuthStore();
const id = computed(() => Number(route.params.id));
const members = ref<KnowledgeBaseMember[]>([]);
const loading = ref(true);
const error = ref("");
const open = ref(false);
const saving = ref(false);
const form = ref({ username: "", role: "viewer" as "editor" | "viewer" });
async function load() {
  if (!auth.token) return;
  loading.value = true;
  try {
    members.value = await getKnowledgeBaseMembers(auth.token, id.value);
  } catch (caught) {
    error.value =
      caught instanceof Error ? caught.message : "加载成员失败，请稍后重试。";
  } finally {
    loading.value = false;
  }
}
async function add() {
  if (!auth.token || !form.value.username.trim()) return;
  saving.value = true;
  try {
    const member = await addKnowledgeBaseMember(auth.token, id.value, {
      username: form.value.username.trim(),
      role: form.value.role,
    });
    members.value = [
      ...members.value.filter((item) => item.user_id !== member.user_id),
      member,
    ];
    open.value = false;
    form.value = { username: "", role: "viewer" };
    ElMessage.success("成员权限已保存");
  } catch (caught) {
    ElMessage.error(
      caught instanceof Error ? caught.message : "保存成员失败，请稍后重试。",
    );
  } finally {
    saving.value = false;
  }
}
async function remove(member: KnowledgeBaseMember) {
  if (!auth.token) return;
  try {
    await removeKnowledgeBaseMember(auth.token, id.value, member.user_id);
    members.value = members.value.filter(
      (item) => item.user_id !== member.user_id,
    );
    ElMessage.success("成员已移除");
  } catch (caught) {
    ElMessage.error(
      caught instanceof Error ? caught.message : "移除成员失败，请稍后重试。",
    );
  }
}
async function changeRole(member: KnowledgeBaseMember, role: "editor" | "viewer") {
  if (!auth.token || member.role === role) return;
  try {
    await ElMessageBox.confirm(
      `确认将 ${member.username} 的权限调整为${role === "editor" ? "编辑者" : "只读成员"}吗？`,
      "变更成员权限",
      { confirmButtonText: "确认", cancelButtonText: "取消", type: "warning" },
    );
    saving.value = true;
    const updated = await addKnowledgeBaseMember(auth.token, id.value, {
      username: member.username,
      role,
    });
    Object.assign(member, updated);
    ElMessage.success("成员权限已更新");
  } catch (caught) {
    if (caught !== "cancel" && caught !== "close") {
      ElMessage.error(caught instanceof Error ? caught.message : "更新成员权限失败，请稍后重试。");
    }
  } finally {
    saving.value = false;
  }
}
function roleLabel(role: KnowledgeBaseMember["role"]) {
  return { owner: "所有者", editor: "编辑者", viewer: "只读成员" }[role];
}
onMounted(load);
</script>
<template>
  <AppLayout
    ><section class="page-shell">
      <header class="page-header">
        <div>
          <RouterLink class="back-link" :to="`/app/knowledge-bases/${id}`">
            <ArrowLeft :size="15" /> 返回知识库概览
          </RouterLink>
          <p class="eyebrow">知识库协作</p>
          <h1>成员与权限</h1>
          <p>
            所有者可管理成员；编辑者可上传与维护文档；只读成员可检索和问答。
          </p>
        </div>
        <el-button type="primary" @click="open = true"
          ><UserPlus :size="16" />添加成员</el-button
        >
      </header>
      <KnowledgeBaseTabs :knowledge-base-id="id" role="owner" /><el-alert
        v-if="error"
        type="error"
        :title="error"
        show-icon
        class="form-alert"
      />
      <section class="table-surface">
        <el-skeleton v-if="loading" :rows="5" animated /><AppEmpty
          v-else-if="members.length === 0"
          title="尚无协作成员"
          description="添加企业账户后可授予编辑或只读权限。"
        /><el-table v-else :data="members"
          ><el-table-column
            label="成员"
            min-width="220"
          ><template #default="{ row }"><RouterLink class="table-link" :to="`/app/members/${row.user_id}`">{{ row.username }}</RouterLink></template></el-table-column
          ><el-table-column label="角色" width="180"
            ><template #default="{ row }">
              <el-tag v-if="row.role === 'owner'" effect="plain">{{ roleLabel(row.role) }}</el-tag>
              <el-select
                v-else
                :model-value="row.role"
                :disabled="saving"
                aria-label="成员权限"
                @change="changeRole(row, $event as 'editor' | 'viewer')"
              >
                <el-option label="编辑者" value="editor" />
                <el-option label="只读成员" value="viewer" />
              </el-select>
            </template></el-table-column
          ><el-table-column label="操作" width="120"
            ><template #default="{ row }"
              ><el-popconfirm
                v-if="row.role !== 'owner'"
                title="确定移除此成员吗？"
                confirm-button-text="移除"
                cancel-button-text="取消"
                @confirm="remove(row)"
                ><template #reference
                  ><el-button link type="danger">移除</el-button></template
                ></el-popconfirm
              ></template
            ></el-table-column
          ></el-table
        >
      </section>
    </section>
    <el-dialog v-model="open" title="添加或更新成员" width="min(92vw, 440px)"
      ><el-form label-position="top"
        ><el-form-item label="用户名" required
          ><el-input
            v-model="form.username"
            placeholder="输入已存在的用户名" /></el-form-item
        ><el-form-item label="权限"
          ><el-radio-group v-model="form.role"
            ><el-radio-button value="viewer">只读成员</el-radio-button
            ><el-radio-button value="editor"
              >编辑者</el-radio-button
            ></el-radio-group
          ></el-form-item
        ></el-form
      ><template #footer
        ><el-button @click="open = false">取消</el-button
        ><el-button
          type="primary"
          :loading="saving"
          :disabled="!form.username.trim()"
          @click="add"
          >保存</el-button
        ></template
      ></el-dialog
    ></AppLayout
  >
</template>
