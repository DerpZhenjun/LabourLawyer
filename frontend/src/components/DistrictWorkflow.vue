<template>
  <section class="district-workflow">
    <h2>其他地区怎么办</h2>
    <p class="hint">先选办理地区。填写前，请确认表格能在当地使用。</p>
    <p v-if="error" role="status">{{error}}</p>
    <label v-if="guides.length">选择办理地区与机构<select v-model="selected"><option v-for="guide in guides" :key="guide.id" :value="guide.id">{{guide.region_name || '页面未标明地区'}} · {{guide.authority || guide.service_name || '官方指南'}}</option></select></label>
    <article v-if="current">
      <a :href="current.guide_url" target="_blank" rel="noopener noreferrer">查看该地区官方指南 ↗</a>
      <p class="hint">记录时间：{{current.captured_at?.slice(0,10)}}</p>
      <ol v-if="current.plain_steps?.length"><li v-for="(step,index) in current.plain_steps" :key="index"><strong>{{step.title}}</strong><p>{{step.text}}</p></li></ol>
      <p v-else>还没查到具体步骤，请打开官方指南。</p>
      <details v-if="current.plain_materials?.length"><summary>需要哪些材料</summary><ul><li v-for="item in current.plain_materials" :key="item">{{item}}</li></ul></details>
    </article>
  </section>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import axios from 'axios'
import {API_BASE} from '../api/http.ts'
import {parseDistrictGuides} from '../../../packages/regional-contracts/src/workspace'
import type {WorkflowGuide} from '../../../packages/regional-contracts/src/workspace'
const props = defineProps<{slug:string}>()
const guides = ref<WorkflowGuide[]>([]), selected = ref(''), error = ref('')
const current = computed(() => guides.value.find(g => g.id === selected.value))
let revision = 0
watch(() => props.slug, async slug => {
  const request = ++revision
  guides.value = []; selected.value = ''; error.value = ''
  try {
    const { data } = await axios.get<unknown>(`${API_BASE}/api/portal-reports/workflows/${encodeURIComponent(slug)}`, { timeout: 15000 })
    if (request !== revision) return
    guides.value = parseDistrictGuides(data)
    selected.value = (guides.value.find(g => g.steps?.length) || guides.value[0])?.id || ''
    if (!guides.value.length) error.value = '本省本次暂无可展示的地区指南。'
  } catch {
    if (request === revision) error.value = '暂未取得地区流程，请通过下方官方链接查询。'
  }
}, { immediate: true })
</script>
<style scoped>
.district-workflow{padding:24px;margin:0 auto;max-width:1132px;border:1px solid #dce8e5;border-radius:16px;background:#f5faf8}.district-workflow h2{margin:0;font-size:20px}.hint{color:#64748b;font-size:12px;line-height:1.7}.district-workflow label{display:block;font-size:13px}.district-workflow select{display:block;width:100%;padding:12px;margin:10px 0 20px;border:1px solid #cbd5e1;border-radius:8px;background:white}.district-workflow a{color:#0f766e}.district-workflow li{margin:14px 0;font-size:13px;line-height:1.8}.district-workflow p{white-space:pre-wrap;overflow-wrap:anywhere}.district-workflow details{margin-top:20px}
</style>
<style scoped>
.district-workflow{max-width:none;padding:24px;background:var(--ll-wash);border:1px solid var(--ll-border);border-radius:12px}.district-workflow h2{font-size:22px}.district-workflow .hint{color:var(--ll-secondary);font-size:14px}.district-workflow label{font-size:14px;font-weight:650}.district-workflow select{min-height:48px;font-size:16px;border-color:var(--ll-border-strong)}.district-workflow li{font-size:15px;color:var(--ll-secondary)}.district-workflow a{color:var(--ll-primary);font-size:15px;text-decoration:underline;text-underline-offset:4px}@media(max-width:700px){.district-workflow{padding:20px 16px}}
</style>
