<script setup lang="ts">
import { computed } from "vue";
const props = defineProps<{ status: string }>();
const statuses = {
  uploaded: { label: "等待处理", type: "warning" },
  processing: { label: "解析中", type: "warning" },
  ready: { label: "已完成", type: "success" },
  failed: { label: "失败", type: "danger" },
} as const;
const display = computed(
  () =>
    statuses[props.status as keyof typeof statuses] ?? {
      label: "状态未知",
      type: "info" as const,
    },
);
</script>
<template>
  <el-tag :type="display.type" effect="plain">{{ display.label }}</el-tag>
</template>
