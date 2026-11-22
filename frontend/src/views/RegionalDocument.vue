<template>
  <component :is="embedded ? 'section' : 'main'" :id="embedded ? undefined : 'main-content'" :tabindex="embedded ? undefined : -1" :class="embedded ? 'regional-editor' : 'regional-page ll-container'">
    <nav v-if="!embedded" class="region-breadcrumb" aria-label="当前位置"><RouterLink :to="back">返回当地办事指南</RouterLink><span>/</span><span>{{ title }}</span></nav>
    <header v-if="!embedded" class="region-heading"><div><span class="ll-eyebrow">{{ region.city }} · {{ region.district }}</span><h1>{{ title }}</h1><p>一项一项填写，也可以下载后继续补充。</p></div></header>
    <label v-if="!loading && !error && templateCandidates.length > 1" class="regional-form-label applicant-selector">
      按申请人身份选择文书
      <select aria-label="按申请人身份选择文书" :value="template?.id" @change="selectTemplate">
        <option v-for="item in templateCandidates" :key="item.id" :value="item.id">{{ item.original_name || item.id }}</option>
      </select>
    </label>
    <p v-if="loading" role="status" class="region-panel">正在核对当地文书来源…</p>
    <div v-else-if="error" role="alert" class="region-notice danger">{{ error }}</div>
    <section v-else-if="!template" class="region-panel"><h2>当地文书尚未通过填写核验</h2><p>不会用其他地区的模板代替。</p><RouterLink :to="back" class="ll-button secondary">返回指南核对来源</RouterLink></section>
    <p v-else-if="contractLoading" role="status" class="region-panel">正在核对本区表单栏目与来源版本…</p>
    <div v-else-if="contractError" class="region-notice danger" role="alert"><p>{{ contractError }}</p><button type="button" class="ll-button secondary" @click="reload">重试加载本区表单</button></div>
    <p v-else-if="!contract" class="region-notice danger" role="alert">当前地区表单尚未完成核对，请返回指南确认来源后重试。</p>
    <form v-else @submit.prevent="requestConfirmation">
      <p v-if="pilotBuild" class="region-notice" role="note">本试点已验收劳动者申请、单一被申请人的情形。<template v-if="contract.fields.some(field=>field.key==='agentName')">代理人姓名栏用于录入原表字段。请向办理机构核对代理资格、授权手续和相应材料。</template></p>
      <p v-if="tongguanBodyOnly || xianHighTechBodyOnly" class="region-notice" role="note">{{ signInstruction }}</p>
      <p v-else-if="employerOnly" class="region-notice" role="note">此表适用于用人单位作为申请人。{{ signInstruction }}</p>
      <p v-else-if="workerManualRecipient" class="region-notice" role="note">此表适用于劳动者作为申请人。用人单位填写版待核验。{{ signInstruction }}</p>
      <div class="sample-note"><i class="fa-regular fa-lightbulb" aria-hidden="true"></i><span><strong>已填入虚构示例，请替换为你的真实信息</strong>姓名、地址、金额和证据仅用于演示。未确定的受理机构和日期可以留空，再向受理机关核对。</span></div>
      <details class="reference-source-note"><summary>文书来源与使用说明：{{ isMetadataSanitized?'依据当地官方原件制作的空白填写版':isConverted?('依据当地官方 '+convertedFormat+' 的空白转换版'):isBlank?'当地官方空白表格':'当地官方参考样表，非空白模板' }}</summary><p>{{ sourceDescription }}生成内容属于辅助填写，不保证受理。{{ signInstruction }}请核对后自行保存并提交。</p></details>
      <fieldset class="regional-controls" :disabled="generating">
        <FeidongApplicationFields v-if="isFeidong" :key="draftKey" v-model="draft" />
        <HunanApplicationFields v-else-if="isHunan" :key="draftKey" v-model="draft" />
        <JiangsuOwnFields v-else-if="isJiangsuOwn" :key="draftKey" v-model="draft" :kind="contract.context.kind" />
        <ZhejiangOwnFields v-else-if="isZhejiangOwn" :key="draftKey" v-model="draft" :kind="contract.context.kind" />
        <RegionalContractFields v-else :key="draftKey" v-model="draft" :contract="contract" />
      </fieldset>
      <div v-if="generationError" class="region-notice danger" role="alert"><p>{{ generationError }}</p><button v-if="validation.valid && ready" type="button" class="ll-button secondary" @click="reload">重新核对本区表单</button></div>
      <p v-if="downloaded" class="region-notice" role="status">文书已生成并下载。请核对空白处、份数和当地要求。{{ signInstruction }}</p>
      <section class="region-panel region-generation"><div><h2>{{ isWorkbook?'生成 Excel 工作簿':'生成 Word 文档' }}</h2><p>按当前地区{{ isConverted?('官方 '+convertedFormat+' 的空白转换版'):isBlank?'官方空白表格':'参考样表' }}填写，未填写的位置留空。</p></div><button class="ll-button" :disabled="generating || !ready">{{ generating?'正在生成…':'生成并下载'+title }}</button></section>
    </form>
    <Teleport to="body"><div v-if="confirmOpen" class="reference-dialog" @click.self="cancelConfirmation"><section ref="dialog" role="dialog" aria-modal="true" :aria-labelledby="`${dialogId}-title`" :aria-describedby="`${dialogId}-description`" tabindex="-1"><h2 :id="`${dialogId}-title`">确认生成{{ title }}？</h2><p :id="`${dialogId}-description`">{{ sourceDescription }}默认内容是虚构示例，未替换时只能作参考，不能直接提交；未填写的位置留空。请核对内容和受理机构。{{ signInstruction }}平台不会代你提交申请。</p><div class="region-actions"><button type="button" class="ll-button secondary" @click="cancelConfirmation">取消</button><button type="button" class="ll-button" :disabled="generating" v-on="{click: confirmationAction}">确认生成</button></div></section></div></Teleport>
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
import {publicEditorIdentity} from '@/api/publicDraftScope'
import {useDialogFocus} from '@/composables/useDialogFocus'
import {downloadDocument} from '@/composables/downloadDocument'
import {createExampleForm} from '../../../packages/regional-contracts/src/index.ts'
import type {Region,RegionalGuide,DocumentKind,FormContext,FormContract} from '../../../packages/regional-contracts/src/index.ts'
import '@/regional-guide.css'
import '@/document-forms.css'

const props=defineProps<{embedded?:boolean;selectedRegion?:Region;selectedGuide?:RegionalGuide|null;documentKind?:DocumentKind}>()
const pilotBuild=import.meta.env?.VITE_LABOURLAWYER_PILOT==='1'
const route=useRoute(),region=computed<Region>(()=>props.selectedRegion||({province:String(route.params.slug),city:String(route.query.city||''),district:String(route.query.district||''),...(route.query.case_scope==='collective'?{case_scope:'collective' as const}:{})}))
const kind=computed<DocumentKind|null>(()=>{const value=props.documentKind||route.params.kind;return value==='application'||value==='evidence'?value:null}),title=computed(()=>kind.value==='evidence'?'证据清单':'仲裁申请书')
const back=computed(()=>({path:`/province/${region.value.province}`,query:{city:region.value.city,district:region.value.district,case_scope:region.value.case_scope}}))
const {guide,loading,error}=props.embedded?{guide:computed(()=>props.selectedGuide??null),loading:ref(false),error:ref('')}:useRegionalGuide(region)
const templateCandidates=computed(()=>{
  const selected=kind.value
  return selected&&Array.isArray(guide.value?.templates)?guide.value.templates.filter(t=>t&&t.can_generate&&Array.isArray(t.document_types)&&t.document_types.includes(selected)):[]
})
const selectedTemplateId=ref('')
const template=computed(()=>templateCandidates.value.find(item=>item.id===selectedTemplateId.value)??templateCandidates.value[0])
function selectTemplate(event:Event) {
  const control=event.target
  if(control instanceof HTMLSelectElement)selectedTemplateId.value=control.value
}
const context=computed<FormContext|null>(()=>{
  const g=guide.value,t=template.value,r=region.value,k=kind.value
  if(!g||!t||!k||typeof g.version!=='number'||!Number.isSafeInteger(g.version)||g.version<1||typeof g.source_id!=='string'||!g.source_id||typeof g.region_code!=='string'||!g.region_code||typeof t.adapter!=='string'||!t.adapter)return null
  if((['province','city','district','case_scope'] as const).some(key=>g[key]!==r[key]))return null
  return{...r,region_code:g.region_code,source_id:g.source_id,version:g.version,template_id:t.id,kind:k,mode:t.official_kind==='blank'?'blank':'reference_adaptation',adapter:t.adapter,...(t.output_format==='xlsx'?{output_format:'xlsx' as const}:{})}
})
const identity=computed(()=>JSON.stringify([template.value?.sha256,template.value?.source_url,guide.value?.content_hash]))
const specialization=(contract:FormContract)=>{
  const {adapter,kind}=contract.context
  if(adapter===JIANGSU_OWN_ADAPTER)return'jiangsu'
  if([ZHEJIANG_OWN_ADAPTER,'zhejiang_own_worker_oct29e_v1','zhejiang_chunan_own_worker_oct30_v1'].includes(adapter))return'zhejiang'
  if(kind==='application'&&['hunan_own_legacy_worker_oct29b_v1','hunan_own_legacy_worker_oct29c_v1'].includes(adapter))return'hunan'
  if(kind==='application'&&adapter===FEIDONG_ADAPTER_KEY)return'feidong'
  return'generic'
}
const documentClient={...regionalClient,generate:(contract:FormContract,form:unknown,signal?:AbortSignal)=>{
  const current=template.value
  if(current?.generation_origin!=='official-blank-metadata-sanitized-filled')return regionalClient.generate(contract,form,signal)
  if(typeof current.sha256!=='string'||typeof current.official_sha256!=='string')throw new Error('空白填写版来源摘要缺失，请重新核对当地指南。')
  return regionalClient.generate(contract,form,signal,{layoutSha256:current.sha256,officialSha256:current.official_sha256})
}}
const formState=useRegionalForm(context,{client:documentClient,identity,ownerIdentity:publicEditorIdentity,download:downloadDocument,
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
const employerOnly=computed(()=>template.value?.service_object==='用人单位')
const workerManualRecipient=computed(()=>['shaanxi_danfeng_worker_application_v1','shaanxi_shangnan_worker_application_v1','shaanxi_shanyang_worker_application_v1','shaanxi_heyang_worker_application_v1','shaanxi_huayin_worker_application_v1','shaanxi_shenmu_worker_evidence_v1','shaanxi_mizhi_worker_application_v1','shaanxi_qingjian_worker_application_v1'].includes(contract.value?.context.adapter??''))
const tongguanBodyOnly=computed(()=>contract.value?.context.adapter==='shaanxi_tongguan_role_application_v1')
const xianHighTechBodyOnly=computed(()=>contract.value?.context.adapter==='shaanxi_xian_high_tech_application_v1')
const signInstruction=computed(()=>{
  if(contract.value?.context.adapter==='shaanxi_xian_high_tech_evidence_xlsx_v1')return'请按原表填写案号、提交人签名和日期。'
  if(xianHighTechBodyOnly.value)return'此处填写请求事项和事实理由。下载后请补全当事人信息和日期，按原表要求亲笔签名捺印。'
  if(['shaanxi_mizhi_worker_application_v1','shaanxi_qingjian_worker_application_v1'].includes(contract.value?.context.adapter??''))return'此处填写仲裁请求和事实理由。下载后请补全当事人信息、申请人署名和日期。'
  if(contract.value?.context.adapter==='shaanxi_shenmu_worker_evidence_v1')return'下载后请在原表填写提交人和提交时间。'
  if(contract.value?.context.adapter==='shaanxi_huayin_worker_application_v1')return'此处填写仲裁请求以及事实和理由。下载后请补全双方信息、仲裁委员会名称、签名和日期。'
  if(contract.value?.context.adapter==='shaanxi_heyang_worker_application_v1')return'此处填写三行请求。下载后请补全双方信息、事实与理由、受理机关、签名和日期。'
  if(tongguanBodyOnly.value)return'下载后请补全双方信息和受理机关，按原表签名或盖章，并在第二页填写日期。'
  if(workerManualRecipient.value)return'请核对并补齐文末仲裁委员会名称，再手写签名和日期。'
  if(template.value?.manual_signing==='signature_fingerprint')return'请按原件要求签名、按手印并填写日期。'
  if(employerOnly.value&&isConverted.value)return'请由申请单位盖章并填写日期。'
  return'签名需本人手写。'
})
const isConverted=computed(()=>isHunan.value||template.value?.file_origin==='official-blank-converted-layout')
const convertedFormat=computed(()=>template.value?.original_format==='WPS'?'WPS':'DOC')
const isMetadataSanitized=computed(()=>template.value?.file_origin==='official-blank-metadata-sanitized-layout')
const isWorkbook=computed(()=>contract.value?.context.output_format==='xlsx')
const sourceDescription=computed(()=>contract.value?.context.adapter==='shaanxi_xian_high_tech_evidence_xlsx_v1'?'按西安高新区官方证据目录填写 12 个空白行。':isWorkbook.value?'按留坝县官方证据清单生成 XLSX。表格有 9 行，页数填写正整数，签署栏留空。':isMetadataSanitized.value?'将依据所选地区官方空白表格的填写版生成。原件可从当地指南的官方附件链接下载。':isConverted.value?`${region.value.case_scope?'仅用于本区集体案。':''}将依据本区官方 ${convertedFormat.value} 空白表的平台转换副本填写。下载结果为 DOCX。`:isBlank.value?`将根据${contract.value?.context.district||''}官网提供的空白表格辅助填写。`:`将根据${contract.value?.context.district||''}官方参考样表辅助填写。它不是官方空白模板。`)
const dialog=ref<HTMLElement|null>(null),dialogId=`regional-confirm-${useId()}`
useDialogFocus(()=>confirmOpen.value,dialog,cancelConfirmation)
</script>
<style scoped>
.applicant-selector{display:grid;gap:8px;margin:0 0 20px}.applicant-selector select{max-width:100%;min-width:0}.regional-controls{margin:0;padding:0;border:0;min-width:0}.reference-source-note{margin:0 0 20px;font-size:14px}.reference-source-note p{margin:0;padding:12px 16px;line-height:1.85;background:var(--ll-wash);color:var(--ll-secondary);border-radius:8px}
</style>
