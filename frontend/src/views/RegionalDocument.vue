<template>
  <component :is="embedded ? 'section' : 'main'" :id="embedded ? undefined : 'main-content'" :tabindex="embedded ? undefined : -1" :class="embedded ? 'regional-editor' : 'regional-page ll-container'">
    <nav v-if="!embedded" class="region-breadcrumb" aria-label="当前位置"><RouterLink :to="back">返回当地办事指南</RouterLink><span>/</span><span>{{ title }}</span></nav>
    <header v-if="!embedded" class="region-heading"><div><span class="ll-eyebrow">{{ region.city }} · {{ region.district }}</span><h1>{{ title }}</h1><p>一项一项填写，也可以生成后在 Word 中继续补充。</p></div></header>
    <p v-if="loading" role="status" class="region-panel">正在核对当地文书来源…</p>
    <div v-else-if="error" role="alert" class="region-notice danger">{{ error }}</div>
    <section v-else-if="!template" class="region-panel"><h2>当地文书尚未通过填写核验</h2><p>不会用其他地区的模板代替。</p><RouterLink :to="back" class="ll-button secondary">返回指南核对来源</RouterLink></section>
    <p v-else-if="contractLoading" role="status" class="region-panel">正在核对本区表单栏目与来源版本…</p>
    <div v-else-if="contractError" class="region-notice danger" role="alert"><p>{{ contractError }}</p><button type="button" class="ll-button secondary" @click="reload">重试加载本区表单</button></div>
    <p v-else-if="!contract" class="region-notice danger" role="alert">当前地区表单尚未完成核对，请返回指南确认来源后重试。</p>
    <form v-else @submit.prevent="requestConfirmation">
      <div class="sample-note"><i class="fa-regular fa-lightbulb" aria-hidden="true"></i><span><strong>已填入虚构示例，请替换为你的真实信息</strong>姓名、地址、金额和证据仅用于演示。未确定的受理机构和日期可以留空，再向受理机关核对。</span></div>
      <details class="reference-source-note"><summary>文书来源与使用说明：{{ isHunan?'依据当地官方DOC的平台转换副本':isBlank?'当地官方空白表格':'当地官方参考样表，非空白模板' }}</summary><p>{{ sourceDescription }}生成内容属于辅助填写，不保证受理。签名需本人手写，请核对后自行保存并提交。</p></details>
      <fieldset class="regional-controls" :disabled="generating">
        <FeidongApplicationFields v-if="isFeidong" :key="draftKey" v-model="draft" />
        <HunanApplicationFields v-else-if="isHunan" :key="draftKey" v-model="draft" />
        <JiangsuOwnFields v-else-if="isJiangsuOwn" :key="draftKey" v-model="draft" :kind="contract.context.kind" />
        <ZhejiangOwnFields v-else-if="isZhejiangOwn" :key="draftKey" v-model="draft" :kind="contract.context.kind" />
        <RegionalContractFields v-else :key="draftKey" v-model="draft" :contract="contract" />
      </fieldset>
      <div v-if="generationError" class="region-notice danger" role="alert"><p>{{ generationError }}</p><button v-if="validation.valid && ready" type="button" class="ll-button secondary" @click="reload">重新核对本区表单</button></div>
      <p v-if="downloaded" class="region-notice" role="status">文书已生成并下载。请核对空白处、份数和当地要求，打印后本人签名。</p>
      <section class="region-panel region-generation"><div><h2>生成 Word 文档</h2><p>按当前地区{{ isHunan?'官方DOC的平台转换副本':isBlank?'官方空白表格':'参考样表' }}填写，未填写的位置留空。</p></div><button class="ll-button" :disabled="generating || !ready">{{ generating?'正在生成…':'生成并下载'+title }}</button></section>
    </form>
    <Teleport to="body"><div v-if="confirmOpen" class="reference-dialog" @click.self="cancelConfirmation"><section ref="dialog" role="dialog" aria-modal="true" :aria-labelledby="`${dialogId}-title`" :aria-describedby="`${dialogId}-description`" tabindex="-1"><h2 :id="`${dialogId}-title`">确认生成{{ title }}？</h2><p :id="`${dialogId}-description`">{{ sourceDescription }}默认内容是虚构示例，未替换时只能作参考，不能直接提交；未填写的位置留空。请核对内容、受理机构并本人签字，不会代你提交申请。</p><div class="region-actions"><button type="button" class="ll-button secondary" @click="cancelConfirmation">取消</button><button type="button" class="ll-button" :disabled="generating" v-on="{click: confirmationAction}">确认生成</button></div></section></div></Teleport>
  </component>
</template>
<script setup lang="ts">
import {computed,ref,useId} from 'vue'
import {useRoute,RouterLink} from 'vue-router'
import FeidongApplicationFields from '@/components/FeidongApplicationFields.vue'
import HunanApplicationFields from '@/components/HunanApplicationFields.vue'
import JiangsuOwnFields from '@/components/JiangsuOwnFields.vue'
import ZhejiangOwnFields from '@/components/ZhejiangOwnFields.vue'
import RegionalContractFields from '@/components/RegionalContractFields.vue'
import {JIANGSU_OWN_ADAPTER,createJiangsuOwnExample,validateJiangsuOwn} from '@/data/jiangsuOwnFields'
import {ZHEJIANG_OWN_ADAPTER,createZhejiangOwnExample,validateZhejiangOwn} from '@/data/zhejiangOwnFields'
import {createHunanApplicationExample,validateHunanApplication} from '@/data/hunanApplicationFields'
import {FEIDONG_ADAPTER_KEY,createFeidongApplicationExample,validateFeidongApplication} from '@/data/feidongApplicationFields'
import {useRegionalGuide,regionalClient} from '@/composables/useRegionalGuide'
import {useRegionalForm} from '@/composables/useRegionalForm'
import {useDialogFocus} from '@/composables/useDialogFocus'
import {downloadDocument} from '@/composables/downloadDocument'
import {createExampleForm} from '../../../packages/regional-contracts/src/index.ts'
import type {Region,RegionalGuide,DocumentKind,FormContext,FormContract} from '../../../packages/regional-contracts/src/index.ts'
import '@/regional-guide.css'
import '@/document-forms.css'

const props=defineProps<{embedded?:boolean;selectedRegion?:Region;selectedGuide?:RegionalGuide|null;documentKind?:DocumentKind}>()
const route=useRoute(),region=computed<Region>(()=>props.selectedRegion||({province:String(route.params.slug),city:String(route.query.city||''),district:String(route.query.district||'')}))
const kind=computed<DocumentKind|null>(()=>{const value=props.documentKind||route.params.kind;return value==='application'||value==='evidence'?value:null}),title=computed(()=>kind.value==='evidence'?'证据清单':'仲裁申请书')
const back=computed(()=>({path:`/province/${region.value.province}`,query:{city:region.value.city,district:region.value.district}}))
const {guide,loading,error}=props.embedded?{guide:computed(()=>props.selectedGuide??null),loading:ref(false),error:ref('')}:useRegionalGuide(region)
const template=computed(()=>{
  const selected=kind.value
  return selected&&Array.isArray(guide.value?.templates)?guide.value.templates.find(t=>t&&t.can_generate&&Array.isArray(t.document_types)&&t.document_types.includes(selected)):undefined
})
const context=computed<FormContext|null>(()=>{
  const g=guide.value,t=template.value,r=region.value,k=kind.value
  if(!g||!t||!k||typeof g.version!=='number'||!Number.isSafeInteger(g.version)||g.version<1||typeof g.source_id!=='string'||!g.source_id||typeof g.region_code!=='string'||!g.region_code||typeof t.adapter!=='string'||!t.adapter)return null
  if((['province','city','district'] as const).some(key=>g[key]!==r[key]))return null
  return{province:r.province,city:r.city,district:r.district,region_code:g.region_code,source_id:g.source_id,version:g.version,template_id:t.id,kind:k,mode:t.official_kind==='blank'?'blank':'reference_adaptation',adapter:t.adapter}
})
const identity=computed(()=>JSON.stringify([template.value?.sha256,template.value?.source_url,guide.value?.content_hash]))
const specialization=(contract:FormContract)=>{
  const {adapter,kind}=contract.context
  if(adapter===JIANGSU_OWN_ADAPTER)return'jiangsu'
  if([ZHEJIANG_OWN_ADAPTER,'zhejiang_own_worker_oct29e_v1'].includes(adapter))return'zhejiang'
  if(kind==='application'&&['hunan_own_legacy_worker_oct29b_v1','hunan_own_legacy_worker_oct29c_v1'].includes(adapter))return'hunan'
  if(kind==='application'&&adapter===FEIDONG_ADAPTER_KEY)return'feidong'
  return'generic'
}
const formState=useRegionalForm(context,{client:regionalClient,identity,download:downloadDocument,
  example:contract=>{
    const type=specialization(contract),kind=contract.context.kind
    return type==='jiangsu'?createJiangsuOwnExample(kind):type==='zhejiang'?createZhejiangOwnExample(kind):type==='hunan'?createHunanApplicationExample():type==='feidong'?createFeidongApplicationExample():createExampleForm(contract)
  },
  validateSpecial:(contract,raw)=>{
    const type=specialization(contract),kind=contract.context.kind
    return type==='jiangsu'?validateJiangsuOwn(raw,kind):type==='zhejiang'?validateZhejiangOwn(raw,kind):type==='hunan'?validateHunanApplication(raw):type==='feidong'?validateFeidongApplication(raw):{valid:true,errors:[]}
  },
})
const {contract,draft,draftKey,loading:contractLoading,error:contractError,generationError,generating,downloaded,confirmOpen,confirmationAction,ready,validation,reload,requestConfirmation,cancelConfirmation}=formState
const special=computed(()=>contract.value?specialization(contract.value):'')
const isJiangsuOwn=computed(()=>special.value==='jiangsu'),isZhejiangOwn=computed(()=>special.value==='zhejiang')
const isHunan=computed(()=>special.value==='hunan'),isFeidong=computed(()=>special.value==='feidong')
const isBlank=computed(()=>contract.value?.context.mode==='blank')
const sourceDescription=computed(()=>isHunan.value?'将依据本区官方 DOC 空白表的平台转换副本填写。下载结果是平台生成的 DOCX，官方原件保留 DOC 格式。':isBlank.value?`将根据${contract.value?.context.district||''}官网提供的空白表格辅助填写。`:`将根据${contract.value?.context.district||''}官方参考样表辅助填写。它不是官方空白模板。`)
const dialog=ref<HTMLElement|null>(null),dialogId=`regional-confirm-${useId()}`
useDialogFocus(()=>confirmOpen.value,dialog,cancelConfirmation)
</script>
<style scoped>
.regional-controls{margin:0;padding:0;border:0;min-width:0}.reference-source-note{margin:0 0 20px;font-size:14px}.reference-source-note p{margin:0;padding:12px 16px;line-height:1.85;background:var(--ll-wash);color:var(--ll-secondary);border-radius:8px}
</style>
