<script setup lang="ts">
defineProps<{ title: string; description: string }>();
</script>

<template>
  <div class="app-empty" role="status">
    <slot name="icon" />
    <h2>{{ title }}</h2>
    <p>{{ description }}</p>
    <slot />
  </div>
</template>
