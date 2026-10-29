<template>
  <component :is="embedded ? 'section' : 'main'" :id="embedded ? undefined : 'main-content'" :tabindex="embedded ? undefined : -1" :class="embedded ? 'regional-editor' : 'regional-page ll-container'">
    <nav v-if="!embedded" class="region-breadcrumb" aria-label="当前位置"><RouterLink :to="back">返回当地办事指南</RouterLink><span>/</span><span>{{ title }}</span></nav>
    <header v-if="!embedded" class="region-heading"><div><span class="ll-eyebrow">{{ region.city }} · {{ region.district }}</span><h1>{{ title }}</h1><p>一项一项填写，也可以生成后在 Word 中继续补充。</p></div></header>
    <p v-if="loading" role="status" class="region-panel">正在核对当地文书来源…</p>
    <div v-else-if="error" role="alert" class="region-notice danger">{{ error }}</div>
    <section v-else-if="!template" class="region-panel"><h2>当地文书尚未通过填写核验</h2><p>不会用其他地区的模板代替。</p><RouterLink :to="back" class="ll-button secondary">返回指南核对来源</RouterLink></section>
    <form v-else @submit.prevent="requestConfirmation">
      <div class="sample-note"><i class="fa-regular fa-lightbulb" aria-hidden="true"></i><span><strong>已填入虚构示例，请替换为你的真实信息</strong>姓名、地址、金额和证据仅用于演示。受理机构和邮政编码请自行确认；可以直接生成示例文书作参考。</span></div>
      <details class="reference-source-note"><summary>文书来源与使用说明：{{ isHunan?'依据当地官方DOC的平台转换副本':isBlank?'当地官方空白表格':'当地官方参考样表，非空白模板' }}</summary><p>{{ sourceDescription }}生成内容属于辅助填写，不保证受理。签名需本人手写，不会自动提交。填写信息不发送给 OpenClaw，也不会在服务端留存。</p></details>
      <FeidongApplicationFields v-if="isFeidong" v-model="feidongForm" />
      <HunanApplicationFields v-if="isHunan" v-model="hunanForm" />
      <ZhejiangOwnFields v-if="isZhejiangOwn" v-model="zhejiangOwnForm" :kind="kind" />
      <section v-if="kind==='application'&&!isFeidong&&!isHunan&&!isZhejiangOwn" class="region-panel">
        <h2>你的信息和公司的信息</h2>
        <div class="region-form-fields"><label v-for="f in applicationFields" :key="f.key">{{ f.label }}<input v-model="form[f.key]" :maxlength="f.max||300" :autocomplete="f.autocomplete||'off'" :placeholder="f.placeholder||'可以稍后补充'"></label></div>
        <details v-if="isBlank" class="blank-extra-fields">
          <summary>补充表格中的其他信息</summary>
          <p class="region-small">下面对应当地空白表格上的栏目。不清楚的可以留空，再向受理机构确认。<template v-if="!isZhejiangBlank">调解意愿和法律援助请由你本人选择。</template></p>
          <div class="region-form-fields">
            <label v-if="!isZhejiangBlank">是否接受调解<select v-model="form.acceptMediation"><option value="">请本人选择</option><option>是</option><option>否</option></select></label>
            <label v-if="!isZhejiangBlank">是否申请法律援助<select v-model="form.legalAid"><option value="">请本人确认</option><option>是</option><option>否</option></select></label>
            <label v-for="f in blankExtraFields" :key="f.key">{{ f.label }}<input v-model="form[f.key]" :type="f.type||'text'" :maxlength="f.max||300" autocomplete="off" :placeholder="f.placeholder||'可以稍后补充'"></label>
          </div>
        </details>
      </section>
      <section v-if="kind==='application'&&!isFeidong&&!isHunan&&!isZhejiangOwn" class="region-panel"><h2>希望解决什么问题？</h2><label class="regional-form-label">你的要求<textarea v-model="requestText" maxlength="1200" aria-describedby="regional-request-hint" placeholder="例如：请求支付拖欠的工资，并写清金额。"></textarea></label><p id="regional-request-hint" class="region-small">一项要求写一行，生成时会分别编号。</p><label class="regional-form-label">事情经过<textarea v-model="form.factsReason" maxlength="12000" placeholder="写清何时入职、工作和工资情况，以及发生了什么。"></textarea></label></section>
      <section v-else-if="kind==='evidence'&&!isZhejiangOwn" class="region-panel"><h2>添加你的证据</h2><p>一份材料填写一项。只列出你实际准备的材料。</p><div v-if="isBlank" class="region-form-fields"><label>受理的仲裁委员会名称<input v-model="evidenceHeader.committeeName" maxlength="120" placeholder="请先确认受理机构"></label><label>案号（已有时填写）<input v-model="evidenceHeader.caseNumber" maxlength="100" placeholder="没有案号可以留空"></label></div><div v-for="(item,index) in evidenceList" :key="item.key" class="regional-material"><div class="evidence-row-title"><h3>第 {{ index+1 }} 项证据</h3><button type="button" class="ll-button secondary" @click="removeEvidence(index)" :aria-label="`删除第${index+1}项证据`" :disabled="evidenceList.length===1"><i class="fa-regular fa-trash-can" aria-hidden="true"></i> 删除</button></div><div class="region-form-fields"><label class="full">材料名称<input v-model="item.name" maxlength="300" placeholder="例如：劳动合同"></label><label v-if="isBlank">材料从哪里取得<input v-model="item.source" maxlength="500" placeholder="例如：本人保存"></label><label v-else>材料件数<input v-model="item.itemCount" maxlength="30" placeholder="例如：1"></label><label>页数<input v-model="item.pageCount" maxlength="30" placeholder="例如：3"></label><label>原件还是复印件<select v-model="item.originalType"><option value="">待确认</option><option>原件</option><option>复印件</option></select></label><label v-if="!isBlank">备注<input v-model="item.notes" maxlength="500"></label><label class="full">这份材料能说明什么<textarea v-model="item.purpose" maxlength="1200" placeholder="例如：说明我与公司存在劳动关系。"></textarea></label></div></div><button type="button" class="ll-button secondary add-regional-evidence" @click="addEvidence" :disabled="evidenceList.length>=40"><i class="fa-solid fa-plus" aria-hidden="true"></i> 添加一项证据</button></section>
      <p v-if="generationError" class="region-notice danger" role="alert">{{ generationError }}</p>
      <p v-if="downloaded" class="region-notice" role="status">文书已生成并下载。请核对空白处、份数和当地要求，打印后本人签名。</p>
      <section class="region-panel region-generation"><div><h2>生成 Word 文档</h2><p>按当地{{ isHunan?'官方DOC的平台转换副本':isBlank?'官方空白表格':'参考样表' }}填写，未填写的位置留空。</p></div><button class="ll-button" :disabled="generating">{{ generating?'正在生成…':'生成并下载'+title }}</button></section>
    </form>
    <Teleport to="body"><div v-if="confirmOpen" class="reference-dialog" @click.self="confirmOpen=false"><section ref="dialog" role="dialog" aria-modal="true" aria-labelledby="reference-title" aria-describedby="reference-description" tabindex="-1"><h2 id="reference-title">确认生成{{ title }}？</h2><p id="reference-description">{{ sourceDescription }}默认内容是虚构示例，未替换时只能作参考，不能直接提交；未填写的位置留空。请核对内容、受理机构并本人签字，不会代你提交申请。</p><div class="region-actions"><button type="button" class="ll-button secondary" @click="confirmOpen=false">取消</button><button type="button" class="ll-button" @click="generate">确认生成</button></div></section></div></Teleport>
  </component>
</template>
<script setup>
import {computed,ref} from 'vue'
import FeidongApplicationFields from '@/components/FeidongApplicationFields.vue'
import HunanApplicationFields from '@/components/HunanApplicationFields.vue'
import ZhejiangOwnFields from '@/components/ZhejiangOwnFields.vue'
import {useZhejiangOwnDrafts} from '@/composables/useZhejiangOwnDrafts'
import {ZHEJIANG_OWN_ADAPTER,validateZhejiangOwn,zhejiangOwnPayload} from '@/data/zhejiangOwnFields'
import {createHunanApplicationExample,validateHunanApplication,hunanApplicationPayload} from '@/data/hunanApplicationFields'
import {FEIDONG_ADAPTER_KEY,createFeidongApplicationExample,validateFeidongApplication,feidongApplicationPayload} from '@/data/feidongApplicationFields'
import {regionalApplicationFields,regionalExtraFields,applicationPayload,isZhejiangBlankAdapter} from '@/data/regionalDocumentFields'
import {useRoute,RouterLink} from 'vue-router'
import {useRegionalGuide,regionalAPI} from '@/composables/useRegionalGuide'
import {useDialogFocus} from '@/composables/useDialogFocus'
import {downloadDocument} from '@/composables/downloadDocument'
import {findProvince,makeApplicationExample,makeEvidenceExample} from '@/data/provinces'
import '@/regional-guide.css'
import '@/document-forms.css'
const props=defineProps({embedded:Boolean,selectedRegion:Object,selectedGuide:Object,documentKind:String})
const route=useRoute(),region=computed(()=>props.selectedRegion||({province:String(route.params.slug),city:String(route.query.city||''),district:String(route.query.district||'')}))
const kind=computed(()=>props.documentKind||route.params.kind),title=computed(()=>kind.value==='evidence'?'证据清单':'仲裁申请书')
const back=computed(()=>({path:`/province/${region.value.province}`,query:{city:region.value.city,district:region.value.district}}))
const {guide,loading,error}=props.embedded?{guide:computed(()=>props.selectedGuide),loading:ref(false),error:ref('')}:useRegionalGuide(region)
const template=computed(()=>guide.value?.templates.find(t=>t.can_generate && t.document_types.includes(kind.value)))
const feidongForm=ref(createFeidongApplicationExample())
const hunanForm=ref(createHunanApplicationExample())
const isZhejiangOwn=computed(()=>template.value?.adapter===ZHEJIANG_OWN_ADAPTER)
const zhejiangOwnForm=useZhejiangOwnDrafts(kind)
const isHunan=computed(()=>kind.value==='application'&&['hunan_own_legacy_worker_oct29b_v1','hunan_own_legacy_worker_oct29c_v1'].includes(template.value?.adapter))
const isFeidong=computed(()=>kind.value==='application'&&template.value?.adapter===FEIDONG_ADAPTER_KEY)
const isBlank=computed(()=>template.value?.official_kind==='blank')
const isZhejiangBlank=computed(()=>isZhejiangBlankAdapter(template.value?.adapter))
const sourceDescription=computed(()=>isHunan.value?'将依据本区官方 DOC 空白表的平台转换副本填写。下载结果是平台生成的 DOCX，官方原件保留 DOC 格式。':isBlank.value?`将根据${region.value.district}官网提供的空白表格辅助填写。`:`将根据${region.value.district}官方参考样表辅助填写。它不是官方空白模板。`)
// Reuse the province example story, never its committee, identity prefix or addresses.
const exampleProvince={...findProvince(region.value.province),city:region.value.city,committee:'请填写实际受理的仲裁委员会',exampleCompany:`${region.value.city}示例科技有限公司`}
const example=makeApplicationExample(exampleProvince)
const address=`${region.value.city}示例路88号（示例）`
const confirmOpen=ref(false),dialog=ref(null),generating=ref(false),generationError=ref(''),downloaded=ref(false)
const form=ref({...example,applicantName:`${example.applicantName}（示例）`,idNumber:'身份证号码（示例，请替换）',idAddress:address,currentAddress:address,applicantMailingAddress:address,registeredAddress:`${region.value.city}示例路120号（示例）`,mailingAddress:`${region.value.city}示例路120号（示例）`,applicantPostalCode:'请填写邮政编码',acceptMediation:'',legalAid:'',applicationDate:'',evidenceCopyCount:2})
const requestText=ref(example.requests.join('\n'))
useDialogFocus(()=>confirmOpen.value,dialog,()=>{confirmOpen.value=false})
let count=0
const blankEvidence=()=>({key:++count,name:'',source:'',pageCount:'',itemCount:'',originalType:'',purpose:'',notes:''})
const evidenceHeader=ref({committeeName:exampleProvince.committee,caseNumber:''})
const evidenceList=ref([{...blankEvidence(),...makeEvidenceExample(exampleProvince).evidenceList[0]}])
const addEvidence=()=>{if(evidenceList.value.length<40)evidenceList.value.push(blankEvidence())}
const removeEvidence=index=>{if(evidenceList.value.length>1)evidenceList.value.splice(index,1)}
const sampleFields=[{key:'applicantName',label:'你的姓名',max:80,autocomplete:'name'},{key:'phone',label:'联系电话',max:40,autocomplete:'tel'},{key:'gender',label:'性别',max:20},{key:'nationality',label:'民族',max:30},{key:'birthDate',label:'出生日期',max:30},{key:'idNumber',label:'身份证号码',max:40},{key:'idAddress',label:'户籍地址'},{key:'currentAddress',label:'现在住址'},{key:'applicantMailingAddress',label:'能够收到文书的通讯地址'},{key:'applicantPostalCode',label:'邮政编码',max:20},{key:'respondentName',label:'公司名称',max:200,autocomplete:'organization'},{key:'registeredAddress',label:'公司住所'},{key:'legalRepName',label:'公司法定代表人姓名',max:80},{key:'legalRepPosition',label:'该负责人职务',max:80},{key:'companyContactPhone',label:'公司联系电话',max:40},{key:'committeeName',label:'受理的仲裁委员会名称',max:120,placeholder:'请先确认受理机构'}]
const applicationFields=computed(()=>regionalApplicationFields(sampleFields,isBlank.value,template.value?.adapter))
const jiangsuExtraFields=[{key:'otherDocumentType',label:'其他证件类型（使用其他证件时填写）'},{key:'otherDocumentNumber',label:'其他证件号码',max:80},{key:'respondentType',label:'公司性质'},{key:'socialCreditCode',label:'公司统一社会信用代码',max:50},{key:'departmentHead',label:'你所在部门的负责人',max:80},{key:'departmentHeadPosition',label:'部门负责人职务',max:80},{key:'mailingAddress',label:'公司的通讯地址'},{key:'companyContact',label:'公司的联系人',max:80},{key:'copyCount',label:'随申请书附上的副本份数',type:'number',placeholder:'请按实际准备的份数填写'},{key:'evidenceCopyCount',label:'随申请书附上的证据份数',type:'number',placeholder:'请按实际准备的份数填写'},{key:'applicationDate',label:'申请日期（也可以打印后填写）',type:'date'}]
const blankExtraFields=computed(()=>regionalExtraFields(jiangsuExtraFields,template.value?.adapter))
function requestConfirmation(){
  if(isZhejiangOwn.value){const result=validateZhejiangOwn(zhejiangOwnForm.value,kind.value);if(!result.valid){generationError.value=result.errors.map(e=>e.message).join('；');return}}
  if(isHunan.value){const result=validateHunanApplication(hunanForm.value);if(!result.valid){generationError.value=result.errors.map(e=>e.message).join('；');return}}
  if(isFeidong.value){const result=validateFeidongApplication(feidongForm.value);if(!result.valid){generationError.value=result.errors.map(e=>e.message).join('；');return}}
  generationError.value='';confirmOpen.value=true
}
async function generate(){
  if(generating.value)return
  confirmOpen.value=false;generationError.value='';downloaded.value=false;generating.value=true
  try{
    const fields=[...applicationFields.value,...(isBlank.value?blankExtraFields.value:[])]
    const data=isZhejiangOwn.value?zhejiangOwnPayload(zhejiangOwnForm.value,kind.value):isHunan.value?hunanApplicationPayload(hunanForm.value):isFeidong.value?feidongApplicationPayload(feidongForm.value):kind.value==='application'?applicationPayload(form.value,fields,requestText.value,isBlank.value&&!isZhejiangBlank.value?['acceptMediation','legalAid']:[]):{...(isBlank.value?evidenceHeader.value:{}),evidenceList:evidenceList.value}
    const response=await fetch(`${regionalAPI}/generate`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...region.value,source_id:guide.value.source_id,version:guide.value.version,template_id:template.value.id,kind:kind.value,mode:isBlank.value?'blank':'reference_adaptation',data})})
    if(!response.ok){const failure=await response.json();throw new Error(typeof failure.detail==='string'?failure.detail:'无法生成，请核对内容后重试。')}
    await downloadDocument(await response.blob(),`${region.value.district}-${title.value}-${isHunan.value?'官方DOC转换填写':isBlank.value?'空白表格填写':'参考填写'}.docx`);downloaded.value=true
  }catch(e){generationError.value=e.message||'无法连接文书服务，请确认后端已启动。'}finally{generating.value=false}
}
</script>
<style scoped>.regional-form-label{display:grid;gap:8px;margin-top:20px}.evidence-row-title{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:18px}.add-regional-evidence{margin-top:24px;width:100%}.reference-source-note{margin:0 0 20px;font-size:14px}.reference-source-note p{margin:0;padding:12px 16px;line-height:1.85;background:var(--ll-wash);color:var(--ll-secondary);border-radius:8px}.blank-extra-fields{margin-top:24px;border-top:1px solid var(--ll-border);padding-top:16px}</style>
