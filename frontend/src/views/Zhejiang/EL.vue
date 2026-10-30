<template>
  <component :is="embedded ? 'section' : 'main'" class="evidence-page" :class="{'embedded-document':embedded}" :id="embedded ? undefined : 'main-content'" :tabindex="embedded ? undefined : -1">
    <header v-if="!embedded" class="page-hero">
      <div class="hero-inner">
        <RouterLink :to="config.backRoute" class="back-link"><i aria-hidden="true" class="fa-solid fa-arrow-left"></i> 返回{{ config.shortName }}办理页</RouterLink>
        <div class="title-row"><span><i aria-hidden="true" class="fa-solid fa-list-check"></i></span><div><small>{{ config.name }}官方格式</small><h1>证据清单</h1><p>把准备提交的材料逐项列出来，我们会生成可直接检查和打印的 Word 清单。</p></div></div>
        <button type="button" class="blank-template-action" :disabled="isSubmitting" @click="requestGeneration(true)"><i aria-hidden="true" class="fa-solid fa-download"></i> 只需要表格？下载空白模板</button>
      </div>
    </header>

    <div class="page-grid">
      <form :class="{'sample-values':usingExample}" novalidate @input="usingExample=false" @change="usingExample=false" @submit.prevent="requestGeneration">
        <div class="sample-note"><i aria-hidden="true" class="fa-solid fa-wand-magic-sparkles"></i><span><strong>已填入一项示例，请换成你的实际证据</strong>证据与同省申请书案例相互对应，可以直接生成，也可以逐项修改。</span></div>
        <section class="form-card basic-card">
          <div class="section-title"><span>1</span><div><h2>填写清单信息</h2><p>案件编号还没有时可以留空。</p></div></div>
          <div class="field-grid">
            <label v-if="hasField('committeeName')" class="field full"><span>仲裁委员会 <em>必填</em></span><input v-model.trim="form.committeeName" placeholder="例如：杭州市劳动人事争议仲裁委员会"></label>
            <label v-if="hasField('submitterName')" class="field"><span>提交人姓名 <em>必填</em></span><input v-model.trim="form.submitterName" placeholder="你的姓名"></label>
            <label v-if="hasField('caseNumber')" class="field"><span>案件编号</span><input v-model.trim="form.caseNumber" placeholder="尚未立案可留空"></label>
            <label v-if="hasField('submitDate')" class="field"><span>提交日期</span><input v-model="form.submitDate" type="date"></label>
            <label v-if="hasField('copyCount')" class="field"><span>清单份数</span><input v-model.number="form.copyCount" type="number" min="1" max="20"><small>{{ config.copyHint }}</small></label>
          </div>
        </section>

        <section class="form-card evidence-card">
          <div class="section-title"><span>2</span><div><h2>添加你的证据</h2><p>一份材料填写一行，按你准备提交的顺序排列。</p></div><b>{{ evidenceList.length }} 项</b></div>
          <div class="tip"><i aria-hidden="true" class="fa-regular fa-lightbulb"></i><span><strong>怎么写“能说明什么”？</strong>例如工资流水可以写“说明每月工资金额和公司发薪情况”。</span></div>

          <div class="evidence-list">
            <article v-for="(item,index) in evidenceList" :key="item.id" class="evidence-item">
              <div class="item-number"><b>{{ index + 1 }}</b><span>第 {{ index + 1 }} 项</span></div>
              <div class="item-fields">
                <label v-if="hasField('name')" class="field wide"><span>材料名称 <em>必填</em></span><input v-model.trim="item.name" placeholder="例如：劳动合同、工资流水、考勤记录"></label>
                <label v-if="hasField('pageCount')" class="field short"><span>页数</span><input v-model.trim="item.pageCount" placeholder="例如：3页"></label>
                <label v-if="hasField('source')" class="field"><span>材料从哪里取得 <em>必填</em></span><input v-model.trim="item.source" placeholder="例如：本人保存、银行下载、公司提供"></label>
                <label v-if="hasField('purpose')" class="field wide"><span>这份材料能说明什么 <em>必填</em></span><textarea v-model.trim="item.purpose" rows="2" placeholder="用一句话说明这份材料与哪项要求有关"></textarea></label>
                <label v-for="[key,label] in extraFields" :key="key" class="field"><span>{{ label }}</span><input v-model.trim="item[key]"></label>
              </div>
              <button v-if="evidenceList.length > 1" type="button" class="remove" aria-label="删除这一项" @click="removeItem(index)"><i aria-hidden="true" class="fa-regular fa-trash-can"></i></button>
            </article>
          </div>
          <button type="button" class="add-evidence" :disabled="evidenceList.length >= 30" @click="addItem"><i aria-hidden="true" class="fa-solid fa-plus"></i> 添加一项证据</button>
        </section>

        <div v-if="status.message" class="message" :class="status.type" role="status"><i aria-hidden="true" :class="status.type==='success'?'fa-solid fa-circle-check':'fa-solid fa-circle-exclamation'"></i>{{ status.message }}</div>
        <div class="submit-bar"><div><strong>生成{{ config.name }}官方格式证据清单</strong><small><i aria-hidden="true" class="fa-solid fa-circle-info"></i> 提交人签名和接收人栏保留空白，打印后人工填写。</small></div><button type="submit" :disabled="isSubmitting"><i aria-hidden="true" :class="isSubmitting?'fa-solid fa-spinner fa-spin':'fa-regular fa-file-word'"></i>{{ isSubmitting ? '正在生成…' : '生成并下载证据清单' }}</button></div>
      </form>

      <aside v-if="!embedded">
        <div class="side-card">
          <span class="side-label"><i aria-hidden="true" class="fa-regular fa-folder-open"></i> 常见证据</span>
          <h2>不知道从哪里开始？</h2>
          <p>点一下即可添加，再按你的实际情况修改。</p>
          <button v-for="preset in presets" :key="preset.name" type="button" @click="addPreset(preset)"><i aria-hidden="true" :class="preset.icon"></i><span><strong>{{ preset.name }}</strong>{{ preset.help }}</span><i aria-hidden="true" class="fa-solid fa-plus"></i></button>
        </div>
        <div class="notice-card"><i aria-hidden="true" class="fa-solid fa-circle-info"></i><div><strong>别只留截图</strong><p>聊天、邮件、考勤等电子材料尽量保留原始设备和完整上下文，提交要求以当地仲裁委员会为准。</p></div></div>
        <div class="draft-card"><i aria-hidden="true" class="fa-regular fa-floppy-disk"></i><span>已自动保存在这台设备</span><button type="button" @click="clearDraft">清除</button></div>
      </aside>
    </div>
  </component>

  <GenerateConfirmation :open="showConfirm" :template-only="templateOnly" :missing-fields="missingFields" :province-name="config.name" document-name="证据清单" @cancel="showConfirm=false" @confirm="confirmGeneration" />
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
import {postProvincialDocument,provincialError,readProvincialDraft,saveProvincialDraft} from '@/api/provincial'
import { RouterLink } from 'vue-router'
import GenerateConfirmation from '@/components/GenerateConfirmation.vue'
import { downloadDocument } from '@/composables/downloadDocument'
import { findProvince, makeEvidenceExample, evidenceExtraFields, evidenceSupportedFields } from '@/data/provinces'

const props=withDefaults(defineProps<{province?:string;embedded?:boolean}>(),{province:'zhejiang',embedded:false})
const foundProvince=findProvince(props.province)
if(!foundProvince)throw new Error('未找到该省份的办事资料，请返回省份选择页。')
const province=foundProvince
const hasField=(key:string)=>(evidenceSupportedFields[props.province]||[]).includes(key)
const config=computed(()=>({...province,backRoute:`/province/${province.slug}`,apiPath:`/api/province-documents/${province.slug}/evidence/generate`,downloadName:`${province.name}劳动仲裁证据清单.docx`}))
const DRAFT_KEY=`labourlawyer-${props.province}-evidence-draft-v6`
const extraFields=evidenceExtraFields[props.province]||[]
const makeItem=(data:Record<string,unknown>={})=>({id:`${Date.now()}-${Math.random()}`,name:'',pageCount:'',source:'',purpose:'',kind:'',originalType:'',hasOriginal:'',pageRange:'',itemCount:'',notes:'',...data})
const completeExample=makeEvidenceExample(province)
const defaults={...completeExample,evidenceList:completeExample.evidenceList.slice(0,1)}
const loadedDraft=readProvincialDraft(DRAFT_KEY,defaults)
const hasSavedDraft=loadedDraft.saved
const draftBlocked=ref(loadedDraft.blocked)
const saved=loadedDraft.form
const form=reactive<Record<string,unknown>&{committeeName:string;caseNumber:string;copyCount:string|number;submitterName:string;submitDate:string}>({committeeName:saved.committeeName||'',caseNumber:saved.caseNumber||'',copyCount:saved.copyCount||2,submitterName:saved.submitterName||'',submitDate:saved.submitDate||''})
type EvidenceItem=ReturnType<typeof makeItem>&Record<string,unknown>
const evidenceList=ref<EvidenceItem[]>(Array.isArray(saved.evidenceList)&&saved.evidenceList.length?saved.evidenceList.map(makeItem):[makeItem()])
const templateOnly=ref(false)
const isSubmitting=ref(false),showConfirm=ref(false),missingFields=ref<string[]>([]),usingExample=ref(!hasSavedDraft),status=reactive({type:loadedDraft.notice?'error':'',message:loadedDraft.notice})
const presets=[
  {name:'劳动合同',help:'说明劳动关系和双方约定',icon:'fa-regular fa-file-lines',source:'本人保存',purpose:'说明我与公司存在劳动关系以及双方约定的工作内容、工资等事项。'},
  {name:'工资流水',help:'说明工资金额和发放情况',icon:'fa-solid fa-money-check-dollar',source:'银行下载',purpose:'说明公司向我支付工资的金额、时间和拖欠情况。'},
  {name:'考勤记录',help:'说明出勤时间和工作情况',icon:'fa-regular fa-calendar-check',source:'本人保存',purpose:'说明我的出勤时间和实际工作情况。'},
  {name:'聊天记录',help:'说明工作安排或争议经过',icon:'fa-regular fa-comments',source:'本人手机',purpose:'说明公司对我的工作安排以及双方沟通过程。'},
  {name:'社保记录',help:'帮助说明劳动关系',icon:'fa-solid fa-shield-heart',source:'政务平台下载',purpose:'说明公司为我缴纳社会保险以及劳动关系存续时间。'},
]
let timer:ReturnType<typeof setTimeout>|undefined
const saveDraft=()=>{if(draftBlocked.value)return;const notice=saveProvincialDraft(DRAFT_KEY,{...loadedDraft.form,...form,evidenceList:evidenceList.value});if(notice){status.type='error';status.message=notice}}
window.addEventListener('pagehide',saveDraft)
watch([form,evidenceList],()=>{clearTimeout(timer);timer=setTimeout(saveDraft,350)},{deep:true})
onBeforeUnmount(()=>{clearTimeout(timer);saveDraft();window.removeEventListener('pagehide',saveDraft)})
const addItem=()=>{if(evidenceList.value.length<30){evidenceList.value.push(makeItem());usingExample.value=false}}
const removeItem=(index:number)=>{evidenceList.value.splice(index,1);usingExample.value=false}
const addPreset=(preset:typeof presets[number])=>{const existing=evidenceList.value.find(item=>!item.name&&!item.source&&!item.purpose);const target=existing||makeItem();Object.assign(target,{name:preset.name,source:preset.source,purpose:preset.purpose});if(!existing)evidenceList.value.push(target);usingExample.value=false}
const clearDraft=()=>{localStorage.removeItem(DRAFT_KEY);draftBlocked.value=false;Object.assign(form,{committeeName:defaults.committeeName,caseNumber:defaults.caseNumber,copyCount:defaults.copyCount,submitterName:defaults.submitterName,submitDate:defaults.submitDate});evidenceList.value=defaults.evidenceList.map(makeItem);usingExample.value=true;status.type='success';status.message='已清除保存内容，并恢复虚构示例。'}
const collectMissingFields=()=>{const list:string[]=[];if(hasField('committeeName')&&!form.committeeName)list.push('仲裁委员会');evidenceList.value.forEach((item,index)=>{if(!item.name&&!item.source&&!item.purpose&&!item.pageCount)list.push(index===0?'至少一项证据':`第 ${index+1} 项证据`);else{if(!item.name)list.push(`第 ${index+1} 项材料名称`);if(hasField('source')&&!item.source)list.push(`第 ${index+1} 项材料来源`);if(!item.purpose)list.push(`第 ${index+1} 项材料说明`)}});return list}
const parseError=(error:unknown)=>provincialError(error,false)
const requestGeneration=(blank:unknown=false)=>{templateOnly.value=blank===true;if(draftBlocked.value&&!templateOnly.value){status.type='error';status.message=loadedDraft.notice;return}status.message='';missingFields.value=templateOnly.value?[]:collectMissingFields();showConfirm.value=true}
const confirmGeneration=()=>{showConfirm.value=false;submitForm()}
const submitForm=async()=>{status.message='';isSubmitting.value=true;try{const payload=templateOnly.value?{}:{...form,evidenceList:evidenceList.value.map(({id,...item})=>item)};const blob=await postProvincialDocument(config.value.apiPath,payload);await downloadDocument(blob,config.value.downloadName);status.type='success';status.message='证据清单已生成。请核对顺序、页数和说明后再打印。'}catch(error){status.type='error';status.message=await parseError(error)}finally{isSubmitting.value=false}}
</script>
