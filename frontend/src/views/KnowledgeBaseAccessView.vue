<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { ArrowLeft, Search, ShieldCheck, UserPlus, Users } from "lucide-vue-next";
import { addKnowledgeBaseMember, getKnowledgeBaseMembers, removeKnowledgeBaseMember } from "../api/knowledgeBases";
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
const query = ref("");
const open = ref(false);
const saving = ref(false);
const form = ref({ username: "", role: "viewer" as "editor" | "viewer" });
const filteredMembers = computed(() => {
  const keyword = query.value.trim().toLocaleLowerCase();
  return keyword ? members.value.filter((member) => member.username.toLocaleLowerCase().includes(keyword)) : members.value;
});
const ownerCount = computed(() => members.value.filter((member) => member.role === "owner").length);
const editorCount = computed(() => members.value.filter((member) => member.role === "editor").length);
const viewerCount = computed(() => members.value.filter((member) => member.role === "viewer").length);

async function load() {
  if (!auth.token) return;
  loading.value = true;
  error.value = "";
  try { members.value = await getKnowledgeBaseMembers(auth.token, id.value); }
  catch (caught) { error.value = caught instanceof Error ? caught.message : "加载成员失败，请稍后重试。"; }
  finally { loading.value = false; }
}
async function add() {
  if (!auth.token || !form.value.username.trim()) return;
  saving.value = true;
  try {
    const member = await addKnowledgeBaseMember(auth.token, id.value, { username: form.value.username.trim(), role: form.value.role });
    members.value = [...members.value.filter((item) => item.user_id !== member.user_id), member].sort((left, right) => left.username.localeCompare(right.username, "zh-CN"));
    open.value = false;
    form.value = { username: "", role: "viewer" };
    ElMessage.success("成员权限已保存");
  } catch (caught) { ElMessage.error(caught instanceof Error ? caught.message : "保存成员失败，请稍后重试。"); }
  finally { saving.value = false; }
}
async function remove(member: KnowledgeBaseMember) {
  if (!auth.token) return;
  try {
    await removeKnowledgeBaseMember(auth.token, id.value, member.user_id);
    members.value = members.value.filter((item) => item.user_id !== member.user_id);
    ElMessage.success("成员已移除，立即失去该知识库的访问权限");
  } catch (caught) { ElMessage.error(caught instanceof Error ? caught.message : "移除成员失败，请稍后重试。"); }
}
async function changeRole(member: KnowledgeBaseMember, role: "editor" | "viewer") {
  if (!auth.token || member.role === role) return;
  try {
    await ElMessageBox.confirm(`确认将 ${member.username} 调整为${role === "editor" ? "编辑者" : "只读成员"}吗？权限会立即生效。`, "变更成员权限", { confirmButtonText: "确认变更", cancelButtonText: "取消", type: "warning" });
    saving.value = true;
    Object.assign(member, await addKnowledgeBaseMember(auth.token, id.value, { username: member.username, role }));
    ElMessage.success("成员权限已更新");
  } catch (caught) {
    if (caught !== "cancel" && caught !== "close") ElMessage.error(caught instanceof Error ? caught.message : "更新成员权限失败，请稍后重试。");
  } finally { saving.value = false; }
}
function roleLabel(role: KnowledgeBaseMember["role"]) { return { owner: "所有者", editor: "编辑者", viewer: "只读成员" }[role]; }
onMounted(load);
</script>

<template>
  <AppLayout>
    <section class="page-shell access-page" aria-labelledby="access-title">
      <header class="page-header">
        <div>
          <RouterLink class="back-link" :to="`/app/knowledge-bases/${id}`"><ArrowLeft :size="15" /> 返回知识库概览</RouterLink>
          <p class="eyebrow">知识库协作</p><h1 id="access-title">成员与权限</h1>
          <p>向已有账户授予最小必要访问权限。角色变更、添加和移除均会记录到知识库审计日志。</p>
        </div>
        <el-button type="primary" @click="open = true"><UserPlus :size="16" />添加成员</el-button>
      </header>
      <KnowledgeBaseTabs :knowledge-base-id="id" role="owner" />
      <el-alert v-if="error" type="error" :title="error" show-icon class="form-alert" />
      <section class="access-role-grid" aria-label="角色权限说明">
        <article class="access-role-card owner"><ShieldCheck :size="19" /><div><strong>所有者</strong><span>{{ ownerCount }} 人</span></div><p>管理成员、文档、检索测试及知识库删除。</p></article>
        <article class="access-role-card editor"><Users :size="19" /><div><strong>编辑者</strong><span>{{ editorCount }} 人</span></div><p>上传、标注、删除文档并重建索引。</p></article>
        <article class="access-role-card viewer"><Users :size="19" /><div><strong>只读成员</strong><span>{{ viewerCount }} 人</span></div><p>浏览知识库内容并基于它进行问答。</p></article>
      </section>
      <section class="table-surface access-members">
        <div class="section-heading"><div><p class="eyebrow">协作成员</p><h2>访问名单</h2></div><span class="table-secondary">共 {{ members.length }} 位成员</span></div>
        <div class="table-toolbar"><el-input v-model="query" :prefix-icon="Search" clearable placeholder="搜索用户名" aria-label="搜索成员" /></div>
        <el-skeleton v-if="loading" :rows="5" animated />
        <AppEmpty v-else-if="members.length === 0" title="尚无协作成员" description="添加企业账户后可授予编辑或只读权限。" />
        <AppEmpty v-else-if="filteredMembers.length === 0" title="没有匹配的成员" description="请调整用户名搜索条件后重试。" />
        <el-table v-else :data="filteredMembers" class="data-table">
          <el-table-column label="成员" min-width="260"><template #default="{ row }"><div class="member-identity"><span>{{ row.username.slice(0, 1).toUpperCase() }}</span><strong>{{ row.username }}</strong></div></template></el-table-column>
          <el-table-column label="角色" width="210"><template #default="{ row }"><el-tag v-if="row.role === 'owner'" type="primary" effect="plain">{{ roleLabel(row.role) }}</el-tag><el-select v-else :model-value="row.role" :disabled="saving" aria-label="成员权限" @change="changeRole(row, $event as 'editor' | 'viewer')"><el-option label="编辑者" value="editor" /><el-option label="只读成员" value="viewer" /></el-select></template></el-table-column>
          <el-table-column label="访问范围" min-width="240"><template #default="{ row }"><span class="table-secondary">{{ row.role === 'owner' ? '成员、文档、检索与设置' : row.role === 'editor' ? '文档与检索' : '浏览与问答' }}</span></template></el-table-column>
          <el-table-column label="操作" width="110" fixed="right"><template #default="{ row }"><el-popconfirm v-if="row.role !== 'owner'" title="确定移除此成员吗？此操作会立即生效。" confirm-button-text="移除" cancel-button-text="取消" @confirm="remove(row)"><template #reference><el-button link type="danger">移除</el-button></template></el-popconfirm><span v-else class="table-secondary">不可移除</span></template></el-table-column>
        </el-table>
      </section>
    </section>
    <el-dialog v-model="open" title="添加或更新成员" width="min(92vw, 460px)" :close-on-click-modal="false">
      <p class="dialog-description">输入已注册的用户名。若该用户已在成员列表中，保存后会更新其角色。</p>
      <el-form label-position="top" @submit.prevent="add"><el-form-item label="用户名" required><el-input v-model="form.username" autocomplete="off" maxlength="50" placeholder="输入已存在的用户名" /></el-form-item><el-form-item label="权限"><el-radio-group v-model="form.role"><el-radio-button value="viewer">只读成员</el-radio-button><el-radio-button value="editor">编辑者</el-radio-button></el-radio-group></el-form-item></el-form>
      <template #footer><el-button @click="open = false">取消</el-button><el-button type="primary" :loading="saving" :disabled="!form.username.trim()" @click="add">保存</el-button></template>
    </el-dialog>
  </AppLayout>
</template>
