<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { CheckCircle2, RefreshCw, Save, ServerCog } from "lucide-vue-next";
import { getModelProviders, saveModelProvider, type ModelProvider } from "../api/admin";
import { useAdminAuthStore } from "../stores/adminAuth";
import AdminLayout from "../layouts/AdminLayout.vue";

type ProviderForm = ModelProvider & { api_key: string };
const auth = useAdminAuthStore();
const providers = ref<ProviderForm[]>([]);
const loading = ref(false);
const savingSlug = ref("");
const error = ref("");
const defaults: ProviderForm[] = [
  { slug: "deepseek", display_name: "DeepSeek", base_url: "https://api.deepseek.com/v1", model_name: "deepseek-chat", api_key_configured: false, api_key_masked: null, is_active: false, api_key: "" },
  { slug: "openai", display_name: "OpenAI", base_url: "https://api.openai.com/v1", model_name: "gpt-4o-mini", api_key_configured: false, api_key_masked: null, is_active: false, api_key: "" },
  { slug: "ollama", display_name: "Ollama", base_url: "http://host.docker.internal:11434/v1", model_name: "llama3.1", api_key_configured: false, api_key_masked: null, is_active: false, api_key: "" },
  { slug: "custom", display_name: "自定义 OpenAI 兼容服务", base_url: "https://", model_name: "", api_key_configured: false, api_key_masked: null, is_active: false, api_key: "" },
];
const hasActiveProvider = computed(() => providers.value.some((provider) => provider.is_active));
async function load() {
  if (!auth.token) return;
  loading.value = true; error.value = "";
  try {
    const saved = await getModelProviders(auth.token);
    const savedBySlug = new Map(saved.map((item) => [item.slug, item]));
    providers.value = defaults.map((item) => ({ ...item, ...(savedBySlug.get(item.slug) ?? {}), api_key: "" }));
    for (const item of saved) if (!providers.value.some((provider) => provider.slug === item.slug)) providers.value.push({ ...item, api_key: "" });
  } catch (caught) { error.value = caught instanceof Error ? caught.message : "加载模型配置失败。"; }
  finally { loading.value = false; }
}
async function save(provider: ProviderForm) {
  if (!auth.token) return;
  if (provider.is_active && provider.slug !== "ollama" && !provider.api_key && !provider.api_key_configured) {
    ElMessage.error("启用该模型前必须填写 API Key。" );
    return;
  }
  savingSlug.value = provider.slug;
  try {
    const saved = await saveModelProvider(auth.token, provider.slug, { display_name: provider.display_name, base_url: provider.base_url, model_name: provider.model_name, api_key: provider.api_key || undefined, is_active: provider.is_active });
    Object.assign(provider, saved, { api_key: "" });
    ElMessage.success("模型配置已保存");
  } catch (caught) { ElMessage.error(caught instanceof Error ? caught.message : "保存模型配置失败。"); }
  finally { savingSlug.value = ""; }
}
onMounted(load);
</script>
<template>
  <AdminLayout><section class="page-shell admin-page model-provider-page" aria-labelledby="models-title">
    <header class="page-header"><div><p class="eyebrow">模型服务</p><h1 id="models-title">模型管理</h1><p>配置 OpenAI 兼容接口。密钥以加密形式保存，列表只显示掩码；启用一个模型后，新问答会立即使用该模型。</p></div><el-button :icon="RefreshCw" :loading="loading" @click="load">刷新</el-button></header>
    <el-alert v-if="error" type="error" :title="error" show-icon />
    <el-alert v-else-if="!hasActiveProvider" type="warning" title="当前使用 .env 中的 DeepSeek 默认配置。保存并启用一个模型后，运行时将改用管理端配置。" show-icon :closable="false" />
    <section class="model-provider-grid" v-loading="loading"><article v-for="provider in providers" :key="provider.slug" class="table-surface model-provider-card"><header><div><ServerCog :size="20" /><h2>{{ provider.display_name }}</h2></div><el-tag :type="provider.is_active ? 'success' : 'info'" effect="light">{{ provider.is_active ? "当前启用" : "未启用" }}</el-tag></header><el-form label-position="top"><el-form-item label="服务名称"><el-input v-model="provider.display_name" maxlength="80"/></el-form-item><el-form-item label="API Key"><el-input v-model="provider.api_key" type="password" show-password :placeholder="provider.api_key_configured ? `已配置（${provider.api_key_masked}），留空则不修改` : '请输入 API Key；Ollama 可留空'"/></el-form-item><el-form-item label="Base URL"><el-input v-model="provider.base_url"/></el-form-item><el-form-item label="默认模型"><el-input v-model="provider.model_name"/></el-form-item><div class="model-provider-actions"><el-switch v-model="provider.is_active" active-text="启用此模型"/><el-button type="primary" :loading="savingSlug === provider.slug" @click="save(provider)"><Save :size="15"/>保存</el-button></div></el-form></article></section>
    <p class="model-provider-note"><CheckCircle2 :size="15"/>仅支持 OpenAI 兼容的 Chat Completions 接口。测试连接应在保存配置后通过实际问答请求验证，避免额外消耗模型额度。</p>
  </section></AdminLayout>
</template>
