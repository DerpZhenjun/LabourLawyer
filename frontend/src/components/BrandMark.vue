<template>
  <img
    class="brand-mark"
    :src="source"
    :alt="label"
    :aria-hidden="label ? undefined : 'true'"
    :width="size"
    :height="size"
    :style="{ width: `${size}px`, height: `${size}px` }"
    draggable="false"
  />
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  variant: { type: String, default: 'brand', validator: value => ['brand', 'assistant'].includes(value) },
  size: { type: Number, default: 32, validator: value => Number.isFinite(value) && value > 0 },
  label: { type: String, default: '' },
})

const source = computed(() => `${import.meta.env.BASE_URL}brand/${props.variant === 'assistant' ? 'counsel-mark.svg' : 'labourlawyer-mark.svg'}`)
</script>

<style scoped>
.brand-mark{display:inline-block;flex:0 0 auto;max-width:none;object-fit:contain;vertical-align:middle;user-select:none}
</style>
