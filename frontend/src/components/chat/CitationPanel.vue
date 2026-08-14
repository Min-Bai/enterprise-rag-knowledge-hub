<script setup lang="ts">
import { computed } from "vue";
import { Download, FileText, PanelRightClose } from "lucide-vue-next";
import type { Citation } from "../../types/api";

const props = defineProps<{ sources: Citation[]; open: boolean }>();
const emit = defineEmits<{ close: []; download: [source: Citation] }>();
const groupedSources = computed(() => {
  const groups = new Map<number, Citation[]>();
  for (const source of props.sources)
    groups.set(source.document_id, [
      ...(groups.get(source.document_id) ?? []),
      source,
    ]);
  return [...groups.values()];
});
</script>

<template>
  <aside
    class="evidence-panel"
    :class="{ 'is-open': open }"
    aria-label="来源证据"
  >
    <div class="panel-toolbar">
      <strong>来源证据</strong
      ><button
        class="icon-button evidence-close"
        type="button"
        title="关闭来源面板"
        aria-label="关闭来源面板"
        @click="emit('close')"
      >
        <PanelRightClose :size="17" />
      </button>
    </div>
    <div v-if="sources.length === 0" class="empty-list">
      回答生成后，来源文档会显示在这里。
    </div>
    <ol v-else class="citation-list">
      <li v-for="(group, index) in groupedSources" :key="group[0].document_id">
        <div class="citation-heading">
          <span class="citation-number">{{ index + 1 }}</span
          ><FileText :size="16" /><strong>{{ group[0].filename }}</strong>
        </div>
        <p>
          命中 {{ group.length }} 个文本块：{{
            group.map((source) => source.chunk_index).join("、")
          }}<span v-if="group.some((source) => source.page)">
            · 包含页码信息</span
          >
        </p>
        <button
          class="text-button"
          type="button"
          @click="emit('download', group[0])"
        >
          <Download :size="15" />下载原文
        </button>
      </li>
    </ol>
  </aside>
</template>
