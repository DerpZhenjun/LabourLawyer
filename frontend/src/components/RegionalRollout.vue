<template>
  <section class="region-panel rollout" data-national-rollout aria-labelledby="rollout-title" :aria-busy="loading">
    <div class="rollout-heading"><div><h2 id="rollout-title">全国区县接入进度</h2><p>名单、指南、填写生成分别统计。候选资料通过验收后才会开放。</p></div><span class="rollout-state">全国尚未完成</span></div>
    <p v-if="loading" role="status">正在读取各省实际进度…</p>
    <div v-else-if="error" class="region-notice danger" role="alert"><p>{{ error }}</p><button class="ll-button secondary" @click="load">重新读取进度</button></div>
    <template v-else-if="status">
      <dl class="rollout-totals"><div><dt>已核验并发布指南</dt><dd>{{ number(status.published_guides) }} <small>地</small></dd></div><div><dt>可填写生成文书</dt><dd>{{ number(status.generatable_localities) }} <small>地</small></dd></div><div><dt>候选资料待验收</dt><dd>{{ number(status.unpublished_candidates) }} <small>地</small></dd></div></dl>
      <p class="rollout-scope">当前追踪 {{ number(status.targets_total) }} 个精确地点，来自已收录目录与独立候选；这不是全国区县和功能区的完整普查。</p>
      <label class="rollout-search">查找省份<input v-model="query" type="search" placeholder="输入省份名称，如四川" /></label>
      <p role="status" class="rollout-results">显示 {{ filtered.length }} 个省级地区</p>
      <table v-if="filtered.length" class="rollout-table"><caption class="visually-hidden">各省区县指南及文书接入状态，所有省份仍有待完成项目</caption><thead><tr><th scope="col">省份</th><th scope="col">追踪地点</th><th scope="col">已发布指南</th><th scope="col">可填写生成</th><th scope="col">候选待验收</th><th scope="col">未采集</th><th scope="col">查看</th></tr></thead><tbody>
        <tr v-for="p in filtered" :key="p.slug" :data-province="p.slug"><th scope="row"><strong>{{ p.name }}</strong><small>仍在接入中</small></th><td data-label="追踪地点">{{ number(p.targets_total) }}</td><td data-label="已发布指南">{{ number(p.published_guides) }}</td><td data-label="可填写生成">{{ number(p.generatable_localities) }}</td><td data-label="候选待验收">{{ number(p.candidates) }}</td><td data-label="未采集">{{ number(p.uncollected) }}</td><td><RouterLink :to="`/province/${p.slug}`" :aria-label="`选择${p.name}办理地区`">选择地区 <span aria-hidden="true">→</span></RouterLink></td></tr>
      </tbody></table>
      <p v-else class="region-notice">没有匹配的省份，请缩短名称后重试。</p>
    </template>
  </section>
</template>
<script setup>
import {computed,onMounted,onUnmounted,ref} from 'vue'
import {RouterLink} from 'vue-router'
import {regionalAPI} from '@/composables/useRegionalGuide'
const status=ref(null),loading=ref(false),error=ref(''),query=ref('')
let request
const number=value=>new Intl.NumberFormat('zh-CN').format(value)
const filtered=computed(()=>status.value?.provinces.filter(p=>p.name.includes(query.value.trim()))||[])
async function load(){
  request?.abort();const own=new AbortController();request=own;loading.value=true;error.value=''
  try{const response=await fetch(`${regionalAPI}/rollout-status`,{signal:own.signal});if(!response.ok)throw new Error('接入进度暂时无法读取，请确认后端已经更新并启动。');const data=await response.json();if(!Array.isArray(data.provinces)||data.directory_is_not_guide_coverage!==true)throw new Error('进度数据格式已变化，请稍后重试。');status.value=data}
  catch(e){if(!own.signal.aborted)error.value=e.message}
  finally{if(request===own)loading.value=false}
}
defineExpose({refresh:load})
onMounted(load);onUnmounted(()=>request?.abort())
</script>
<style scoped>
.rollout-heading{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap}.rollout-heading h2{margin-bottom:8px}.rollout-state{color:var(--ll-primary);border:1px solid var(--ll-border);background:var(--ll-background);border-radius:6px;padding:8px 12px;font-size:14px;font-weight:600;white-space:nowrap}.rollout-totals{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:24px;margin:24px 0}.rollout-totals>div{border-left:3px solid var(--ll-border);padding-left:16px}.rollout-totals dt{color:var(--ll-secondary);font-weight:500;font-size:14px}.rollout-totals dd{font-size:30px;font-weight:700;color:var(--ll-primary);margin:8px 0 0;font-variant-numeric:tabular-nums}.rollout-totals small{font-size:14px;font-weight:400}.rollout-scope{font-size:14px;color:var(--ll-secondary);max-width:65ch}.rollout-search{display:grid;gap:8px;max-width:360px;font-weight:600;margin-top:24px}.rollout-search input{width:100%;min-height:44px;background:var(--ll-surface,#fff);border:1px solid var(--ll-border);border-radius:6px;padding:10px 12px;color:var(--ll-text);font:inherit;font-weight:400}.rollout-results{font-size:14px;margin:12px 0;color:var(--ll-secondary)}.rollout-table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums;font-size:14px}.rollout-table th,.rollout-table td{padding:16px 8px;border-bottom:1px solid var(--ll-border);text-align:left}.rollout-table thead{background:var(--ll-background);color:var(--ll-secondary)}.rollout-table tbody th{font-weight:500}.rollout-table small{display:block;font-size:12px;color:var(--ll-secondary);margin-top:4px;font-weight:400}.rollout-table a{display:inline-flex;min-height:44px;align-items:center;gap:8px;color:var(--ll-primary);font-weight:600}.rollout :is(a,button,input):focus-visible{outline:3px solid var(--ll-primary);outline-offset:3px}.rollout td:last-child{min-width:100px}.rollout :is(p,th,td){overflow-wrap:anywhere}
@media(max-width:1000px){.rollout-table thead{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}.rollout-table,.rollout-table tbody{display:block}.rollout-table tr{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));border:1px solid var(--ll-border);border-radius:8px;padding:16px;margin-bottom:12px;gap:8px 16px}.rollout-table th,.rollout-table td{display:block;padding:0;border:0}.rollout-table tbody th,.rollout-table td:last-child{grid-column:1/-1}.rollout-table td[data-label]::before{content:attr(data-label);display:block;color:var(--ll-secondary);font-size:12px;margin-bottom:4px}.rollout-table strong{font-size:17px}.rollout-table td:last-child{border-top:1px solid var(--ll-border);padding-top:8px;margin-top:8px}.rollout-totals{gap:12px}.rollout-totals>div{padding-left:10px}}
@media(max-width:500px){.rollout-totals{grid-template-columns:1fr;gap:16px}.rollout-totals>div{display:flex;justify-content:space-between;align-items:center}.rollout-totals dd{margin:0;font-size:25px}.rollout-heading p{font-size:14px}}
</style>
