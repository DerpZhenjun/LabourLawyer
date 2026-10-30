<template>
  <RouterLink :to="'/province/'+province.slug" class="province-card">
    <div class="province-card-copy"><span class="province-availability"><i :class="province.status==='ready'?'fa-regular fa-file-lines':'fa-solid fa-route'" aria-hidden="true"></i>{{ province.status==='ready'?'文书 + 办理指南':'官方办理指南' }}</span><h3>{{ province.name }}</h3><p>{{ services }}</p><span class="province-card-action">开始准备 <i class="fa-solid fa-arrow-right" aria-hidden="true"></i></span></div>
    <img :src="theme.art" alt="" width="140" height="100" loading="lazy">
  </RouterLink>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import themes from '../../../config/province_themes.json'
import type {ProvinceDefinition} from '@/data/provinces'
const props=defineProps<{province:ProvinceDefinition}>()
const themeCatalog:Record<string,typeof themes.zhejiang>=themes
const theme=computed(()=>themeCatalog[props.province.slug]||themes.zhejiang)
const services=computed(()=>[props.province.hasApplication?'仲裁申请书':'',props.province.hasEvidence?'证据清单':''].filter(Boolean).join(' · ')||'查看申请入口与材料要求')
</script>
<style scoped>
.province-card{position:relative;isolation:isolate;min-width:0;min-height:204px;padding:24px;background:var(--ll-surface);border:1px solid var(--ll-border);border-radius:var(--ll-radius);display:flex;align-items:center;overflow:hidden;transition:border-color 160ms,box-shadow 160ms}.province-card:hover{border-color:var(--ll-primary);box-shadow:var(--ll-shadow)}.province-card-copy{z-index:1;min-width:0}.province-availability{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--ll-primary);font-weight:600}.province-card h3{margin:16px 0 8px;font-size:25px;font-weight:700;color:var(--ll-text)}.province-card p{margin:0;font-size:14px;color:var(--ll-secondary);max-width:210px}.province-card-action{margin-top:20px;display:inline-flex;align-items:center;gap:16px;font-size:14px;color:var(--ll-primary);font-weight:650}.province-card img{position:absolute;z-index:-1;right:12px;bottom:28px;width:140px;height:100px;object-fit:contain;opacity:.55}.province-card:hover .province-card-action i{transform:translateX(4px)}.province-card-action i{transition:transform 160ms}
@media(max-width:700px){.province-card{min-height:170px;padding:20px}.province-card h3{font-size:24px;margin:12px 0 8px}.province-card-action{margin-top:16px}.province-card img{right:12px;bottom:20px;width:116px;height:84px}}
</style>
