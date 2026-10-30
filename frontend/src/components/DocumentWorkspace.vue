<template>
  <section id="document-workspace" class="document-workspace" aria-labelledby="document-workspace-title">
    <header class="workspace-heading">
      <div><span class="ll-eyebrow">下一步 · 填写文书</span><h2 id="document-workspace-title">填写并生成文书</h2><p>先按示例修改内容，再生成 Word。办理方式和材料要求在下方。</p></div>
      <a href="#regional-overview" v-if="guide?.source_id" class="workspace-guide-link">查看当地办理要求 <i class="fa-solid fa-arrow-down" aria-hidden="true"></i></a>
    </header>
    <div class="document-kind-switch" role="group" aria-label="选择文书">
      <button v-for="item in kinds" :key="item.kind" type="button" :aria-pressed="kind===item.kind" @click="kind=item.kind"><i :class="item.icon" aria-hidden="true"></i>{{ item.label }}</button>
    </div>
    <p v-if="loading" class="region-panel" role="status">正在核对文书来源…</p>
    <p v-else-if="error" class="region-notice danger" role="alert">暂时无法核对文书来源，请在下方重新读取指南。</p>
    <div v-else-if="guide?.source_id && !localTemplate" class="region-panel workspace-unavailable"><h3>当地文书尚未通过填写核验</h3><p>不会用其他区县的模板代替。{{ guide.templates?.some(t=>t.download_status==='downloaded')?'你可以先下载已核实的当地原文件参考填写。':'尚未核实可下载文件，请先查看官网材料栏目或向办理机构确认。' }}办理指南仍在下方。</p><a href="#regional-documents" class="ll-button secondary">查看当地文书核验情况</a></div>
    <div v-else-if="!guide?.source_id && (!legacyAvailable || hasSelectedPlace)" class="region-panel workspace-unavailable"><h3>该地区暂未开放这类文书生成</h3><p>尚未核验可填写的模板，不会套用其他地区的文书。已有历史文书可在单独的适用范围页面查看。</p><RouterLink :to="`/province/${region.province}/templates`" class="ll-button secondary">查看已有文书的适用范围</RouterLink></div>
    <div v-else-if="!guide?.source_id" class="workspace-scope" role="note"><i class="fa-solid fa-circle-info" aria-hidden="true"></i><p>当前文书来源：{{ province?.officialName }}。适用范围：{{ province?.scope || '请核对来源' }}。<strong>不代表所选区县的模板已经核验</strong>；提交前请向当地受理机构确认。<a :href="province?.officialUrl" target="_blank" rel="noopener noreferrer">查看来源 ↗</a></p></div>
    <KeepAlive :max="6"><component v-if="editor" :is="editor" :key="editorKey" v-bind="editorProps" /></KeepAlive>
  </section>
</template>
<script setup lang="ts">
import {computed,defineAsyncComponent,ref} from 'vue'
import {RouterLink} from 'vue-router'
import type {DocumentKind,Region,RegionalGuide} from '../../../packages/regional-contracts/src/index'
interface WorkspaceProvince {officialName?:string;scope?:string;officialUrl?:string;hasApplication?:boolean;hasEvidence?:boolean}
const props=withDefaults(defineProps<{region:Region;province?:WorkspaceProvince|null|undefined;guide?:RegionalGuide|null|undefined;loading?:boolean;error?:string}>(),{loading:false,error:''})
const Application=defineAsyncComponent(()=>import('@/views/Zhejiang/LA.vue'))
const Evidence=defineAsyncComponent(()=>import('@/views/Zhejiang/EL.vue'))
const Regional=defineAsyncComponent(()=>import('@/views/RegionalDocument.vue'))
const kind=ref<DocumentKind>('application'),kinds:{kind:DocumentKind;label:string;icon:string}[]=[{kind:'application',label:'仲裁申请书',icon:'fa-regular fa-file-lines'},{kind:'evidence',label:'证据清单',icon:'fa-solid fa-list-check'}]
const localTemplate=computed(()=>props.guide?.templates?.find(t=>t.can_generate&&t.document_types.includes(kind.value)))
const hasSelectedPlace=computed(()=>Boolean(props.region.city?.trim()||props.region.district?.trim()))
const legacyAvailable=computed(()=>kind.value==='application'?props.province?.hasApplication:props.province?.hasEvidence)
const editor=computed(()=>{
  if(props.loading||props.error)return null
  if(props.guide?.source_id)return localTemplate.value?Regional:null
  if(hasSelectedPlace.value)return null
  return legacyAvailable.value?(kind.value==='application'?Application:Evidence):null
})
const editorKey=computed(()=>`${props.guide?.source_id?`${props.guide.source_id}:${props.guide.version}`:`province:${props.region.province}`}:${kind.value}`)
const editorProps=computed(()=>props.guide?.source_id?{embedded:true,selectedRegion:props.region,selectedGuide:props.guide,documentKind:kind.value}:{embedded:true,province:props.region.province})
</script>
<style>
.document-workspace{margin:32px 0 48px;scroll-margin-top:100px}.workspace-heading{display:flex;align-items:center;justify-content:space-between;gap:20px;margin-bottom:20px}.workspace-heading h2{font-size:28px;margin:8px 0}.workspace-heading p{color:var(--ll-secondary);line-height:1.8;margin:0}.workspace-guide-link{display:inline-flex;gap:8px;align-items:center;min-height:44px;color:var(--ll-primary);font-size:14px;flex-shrink:0}.document-kind-switch{display:flex;gap:8px;padding:6px;background:var(--ll-wash);border:1px solid var(--ll-border);border-radius:12px;margin-bottom:20px;width:fit-content;max-width:100%}.document-kind-switch button{display:flex;justify-content:center;align-items:center;gap:10px;min-height:48px;padding:10px 24px;border:1px solid transparent;border-radius:8px;background:transparent;color:var(--ll-primary);font-size:16px;font-weight:650}.document-kind-switch button[aria-pressed=true]{background:var(--ll-surface);border-color:var(--ll-border-strong);box-shadow:0 2px 4px #183b3d0a}.workspace-scope{display:flex;align-items:start;gap:12px;border-left:3px solid var(--ll-primary);padding:14px 18px;margin-bottom:20px;background:var(--ll-wash);font-size:14px;color:var(--ll-secondary);line-height:1.85}.workspace-scope>i{margin-top:6px}.workspace-scope p{margin:0}.workspace-scope strong{font-weight:650}.workspace-scope a{color:var(--ll-primary);text-decoration:underline;text-underline-offset:3px}.document-workspace .embedded-document{background:transparent;min-height:0}.document-workspace .embedded-document .page-grid{display:block;max-width:none;padding:0}.document-workspace .regional-editor{min-width:0}.workspace-unavailable p{color:var(--ll-secondary);line-height:1.85}.document-workspace button:focus-visible,.workspace-guide-link:focus-visible{outline:3px solid var(--ll-focus);outline-offset:3px}
@media(max-width:600px){.document-workspace{margin-top:24px}.workspace-heading{display:block}.workspace-heading h2{font-size:24px}.workspace-guide-link{margin-top:8px}.document-kind-switch{width:100%}.document-kind-switch button{flex:1;padding:10px 8px}.document-workspace .embedded-document :is(.form-section,.form-card){padding:20px}.workspace-scope{padding:12px}}
/* Keep the locality picker short enough that filling remains the next visible task. */
.selector-panel.region-panel{padding:24px}.selector-panel .region-examples{margin-top:12px}
@media(min-width:360px) and (max-width:600px){.selector-panel .region-selectors{grid-template-columns:repeat(2,minmax(0,1fr))}.selector-panel .region-selectors>label:first-child{grid-column:1/-1}}
@media(max-width:600px){.selector-panel.region-panel{padding:20px}}
</style>
