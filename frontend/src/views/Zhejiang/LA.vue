<template>
  <component :is="embedded ? 'section' : 'main'" class="document-page" :class="{'embedded-document':embedded}" :id="embedded ? undefined : 'main-content'" :tabindex="embedded ? undefined : -1">
    <header v-if="!embedded" class="page-hero">
      <div class="hero-inner">
        <RouterLink :to="config.backRoute" class="back-link"><i aria-hidden="true" class="fa-solid fa-arrow-left"></i> 返回{{ config.shortName }}办理页</RouterLink>
        <div class="hero-copy">
          <span class="document-icon"><i aria-hidden="true" class="fa-regular fa-file-lines"></i></span>
          <div><p class="eyebrow">{{ config.name }}官方格式</p><h1>劳动人事争议仲裁申请书</h1><p>按提示填写，我们会把内容放进{{ config.name }}官方申请书模板，并下载为 Word 文档。</p></div>
        </div>
        <button type="button" class="blank-template-action" :disabled="isSubmitting" @click="requestGeneration(true)"><i aria-hidden="true" class="fa-solid fa-download"></i> 只需要表格？下载空白模板</button>
        <div class="progress-strip" aria-label="填写步骤">
          <button v-for="(label, index) in steps" :key="label" type="button" :aria-current="index === focusedStep ? 'step' : undefined" :class="{ active: index === focusedStep, done: index < activeStep && !usingExample }" @click="jumpToStep(index)"><b>{{ index + 1 }}</b>{{ label }}</button>
        </div>
      </div>
    </header>

    <div class="page-grid">
      <form class="form-column" :class="{'sample-values':usingExample}" novalidate @input="usingExample=false" @change="usingExample=false" @submit.prevent="requestGeneration">
        <div class="sample-note"><i aria-hidden="true" class="fa-solid fa-wand-magic-sparkles"></i><span><strong>已填入虚构示例，请按实际情况修改</strong>可以直接生成案例文书，也可以按你的实际情况逐项修改。</span></div>
        <section class="form-section" id="applicant-section">
          <div class="section-heading"><span><i aria-hidden="true" class="fa-regular fa-user"></i></span><div><small>第 1 步</small><h2>填写你的信息</h2><p>请按身份证上的内容填写。</p></div></div>
          <div class="fields two-columns">
            <label v-if="hasField('committeeName')" class="field full"><span>提交给哪个仲裁委员会 <em>必填</em></span><input v-model.trim="form.committeeName" type="text" placeholder="例如：杭州市劳动人事争议仲裁委员会" autocomplete="organization"><small>一般选择工作地或公司所在地的劳动人事争议仲裁委员会。</small></label>
            <label v-if="hasField('applicantName')" class="field"><span>姓名 <em>必填</em></span><input v-model.trim="form.applicantName" type="text" placeholder="身份证上的姓名" autocomplete="name"></label>
            <label v-if="hasField('age')" class="field"><span>年龄</span><input v-model="form.age" type="number" min="0" max="150" placeholder="未填时按出生日期和申请日期计算"></label>
            <label v-if="hasField('birthDate')" class="field"><span>出生日期</span><input v-model="form.birthDate" type="date"></label>
            <fieldset v-if="hasField('gender')" class="field"><legend>性别</legend><div class="choice-row"><label v-for="item in ['男','女','其他']" :key="item"><input v-model="form.gender" type="radio" :value="item"><span>{{ item }}</span></label></div></fieldset>
            <label v-if="hasField('nationality')" class="field"><span>民族</span><input v-model.trim="form.nationality" type="text" placeholder="例如：汉族"></label>
            <label v-if="hasField('idNumber')" class="field"><span>身份证号码 <em>必填</em></span><input v-model.trim="form.idNumber" type="text" maxlength="30" placeholder="请核对后再填写" autocomplete="off"></label>
            <label v-if="hasField('phone')" class="field"><span>联系电话 <em>必填</em></span><input v-model.trim="form.phone" type="tel" placeholder="能接到通知的手机号" autocomplete="tel"></label>
            <label v-if="hasField('householdType')" class="field"><span>户口类型</span><select v-model="form.householdType"><option value="">请选择</option><option v-for="item in householdOptions" :key="item">{{ item }}</option></select></label>
            <label v-if="hasField('idAddress')" class="field full"><span>身份证住址 <em>必填</em></span><input v-model.trim="form.idAddress" type="text" placeholder="身份证上写的住址" autocomplete="street-address"></label>
            <label v-if="hasField('applicantMailingAddress')" class="field full"><span>你的收件地址</span><div class="field-action"><input v-model.trim="form.applicantMailingAddress" type="text" placeholder="用于接收仲裁材料，不填则使用身份证住址"><button type="button" @click="form.applicantMailingAddress=form.idAddress">同身份证住址</button></div></label>
          </div>
        </section>

        <section class="form-section" id="company-section">
          <div class="section-heading"><span><i aria-hidden="true" class="fa-regular fa-building"></i></span><div><small>第 2 步</small><h2>填写公司信息</h2><p>不确定时，可查看劳动合同或公司的营业执照信息。</p></div></div>
          <div class="fields two-columns">
            <label v-if="hasField('respondentName')" class="field full"><span>公司全称 <em>必填</em></span><input v-model.trim="form.respondentName" type="text" placeholder="请填写营业执照上的完整名称" autocomplete="organization"></label>
            <label v-if="hasField('socialCreditCode')" class="field"><span>统一社会信用代码</span><input v-model.trim="form.socialCreditCode" type="text" maxlength="30" placeholder="营业执照上的 18 位代码"></label>
            <label v-if="hasField('legalRepName')" class="field"><span>法定代表人姓名</span><input v-model.trim="form.legalRepName" type="text" placeholder="不知道可以暂时留空"></label>
            <label v-if="hasField('registeredAddress')" class="field full"><span>公司注册地址 <em>必填</em></span><input v-model.trim="form.registeredAddress" type="text" placeholder="营业执照上的住所"></label>
            <label v-if="hasField('workAddress')" class="field full"><span>实际工作地址 <em>必填</em></span><input v-model.trim="form.workAddress" type="text" placeholder="你平时上班的具体地址"></label>
            <label v-if="hasField('mailingAddress')" class="field full"><span>公司收件地址</span><div class="field-action"><input v-model.trim="form.mailingAddress" type="text" placeholder="用于接收仲裁材料，不清楚可与注册地址相同"><button type="button" @click="form.mailingAddress=form.registeredAddress">同注册地址</button></div></label>
            <label v-if="hasField('legalRepPosition')" class="field"><span>法定代表人职务</span><input v-model.trim="form.legalRepPosition" type="text" placeholder="例如：执行董事"></label>
            <label v-if="hasField('legalRepPhone')" class="field"><span>法定代表人电话</span><input v-model.trim="form.legalRepPhone" type="tel" placeholder="不知道可以留空"></label>
            <label v-if="hasField('companyContact')" class="field"><span>公司联系人</span><input v-model.trim="form.companyContact" type="text" placeholder="例如：人事负责人"></label>
            <label v-if="hasField('companyContactPhone')" class="field"><span>联系人电话</span><input v-model.trim="form.companyContactPhone" type="tel" placeholder="不知道可以留空"></label>
          </div>
        </section>

        <section v-if="extraFields.length" class="form-section"><h2>当地模板补充信息</h2><div class="fields two-columns"><label v-for="[key,label] in extraFields" :key="key" class="field"><span>{{ label }}</span><input v-model.trim="form[key]" :type="documentFieldDefinitions[key]?.type === 'date' ? 'date' : 'text'"></label></div></section>
        <section class="form-section" id="requests-section">
          <div class="section-heading"><span><i aria-hidden="true" class="fa-solid fa-list-check"></i></span><div><small>第 3 步</small><h2>你希望公司怎么处理</h2><p>一条写一件事，并写清时间和金额。最多填写 {{ maxRequests }} 条。</p></div></div>
          <div class="example-box"><i aria-hidden="true" class="fa-regular fa-lightbulb"></i><p><strong>参考写法：</strong>请求公司支付 2026 年 1 月至 3 月拖欠的工资共计 15,000 元。</p></div>
          <div class="request-list">
            <div v-for="(item,index) in form.requests" :key="index" class="request-item"><b>{{ index + 1 }}</b><textarea v-model.trim="form.requests[index]" :aria-label="`第 ${index + 1} 项要求`" rows="3" maxlength="300" :placeholder="index === 0 ? '请写明你的第一项要求' : '继续填写另一项要求'"></textarea><button v-if="form.requests.length > 1" type="button" aria-label="删除这一项" @click="removeRequest(index)"><i aria-hidden="true" class="fa-regular fa-trash-can"></i></button></div>
          </div>
          <button v-if="form.requests.length < maxRequests" type="button" class="add-button" @click="form.requests.push('')"><i aria-hidden="true" class="fa-solid fa-plus"></i> 再加一项要求</button>
          <label v-if="hasField('claimCalculation')" class="field calculation-field"><span>金额是怎么算的</span><textarea v-model.trim="form.claimCalculation" rows="5" maxlength="240" placeholder="例如：拖欠工资＝5000元/月 × 3个月＝15000元；经济补偿＝5000元/月 × 2个月＝10000元。没有金额的请求可以留空。"></textarea><small>用于模板中单独列出的计算方式或事实说明。</small></label>

          <div v-if="showEmploymentDetails" class="guangdong-details">
            <div class="subsection-title"><span><i aria-hidden="true" class="fa-solid fa-briefcase"></i></span><div><h3>补充工作基本情况</h3><p>请按当前地区模板中的基本事实填写。知道多少填多少，不确定的可以先留空。</p></div></div>
            <div class="fields two-columns">
              <label v-if="hasField('employmentDate')" class="field"><span>入职日期</span><input v-model="form.employmentDate" type="date"></label>
              <label v-if="hasField('jobTitle')" class="field"><span>岗位或职务</span><input v-model.trim="form.jobTitle" type="text" placeholder="例如：运营专员"></label>
              <label v-if="hasField('signedContract')" class="field"><span>有没有签劳动合同</span><select v-model="form.signedContract"><option value="">请选择</option><option>有</option><option>无</option></select></label>
              <label v-if="hasField('contractStartDate')" class="field"><span>最后一份劳动合同期限</span><div class="date-range"><input aria-label="劳动合同开始日期" v-model="form.contractStartDate" type="date"><b>至</b><input aria-label="劳动合同结束日期" v-model="form.contractEndDate" type="date"></div></label>
              <label v-if="hasField('workSchedule')" class="field full"><span>平时怎么上班</span><input v-model.trim="form.workSchedule" type="text" placeholder="例如：每周工作5天，每天8小时；或写明排班情况"></label>
              <label v-if="hasField('attendanceRequired')" class="field"><span>是否需要考勤</span><select v-model="form.attendanceRequired"><option value="">请选择</option><option>是</option><option>否</option></select></label>
              <label v-if="hasField('attendanceMethod')" class="field"><span>考勤方式</span><input v-model.trim="form.attendanceMethod" type="text" placeholder="例如：钉钉打卡、指纹"></label>
              <label v-if="hasField('salaryPaymentMethod')" class="field"><span>工资怎么发</span><select v-model="form.salaryPaymentMethod"><option value="">请选择</option><option>现金</option><option>转账</option></select></label>
              <label v-if="hasField('salaryReceiptRequired')" class="field"><span>领工资是否签收</span><select v-model="form.salaryReceiptRequired"><option value="">请选择</option><option>需要签收</option><option>不需要签收</option></select></label>
              <label v-if="hasField('startingSalary')" class="field"><span>入职时工资标准</span><input v-model.trim="form.startingSalary" type="text" placeholder="例如：5000元/月"></label>
              <label v-if="hasField('salaryAdjustments')" class="field"><span>后来工资有没有调整</span><input v-model.trim="form.salaryAdjustments" type="text" placeholder="没有可写“无”"></label>
              <label v-if="hasField('currentlyEmployed')" class="field"><span>现在是否还在职</span><select v-model="form.currentlyEmployed"><option value="">请选择</option><option>是</option><option>否</option></select></label>
              <label v-if="hasField('departureDate')" class="field"><span>离职日期</span><input v-model="form.departureDate" type="date" :disabled="form.currentlyEmployed==='是'"></label>
              <label v-if="hasField('departureReason')" class="field full"><span>离职原因</span><input v-model.trim="form.departureReason" type="text" :disabled="form.currentlyEmployed==='是'" placeholder="仍在职不用填写；已离职请简单说明"></label>
              <label v-if="hasField('averageMonthlySalary')" class="field"><span>离职前12个月平均工资</span><input v-model.trim="form.averageMonthlySalary" type="text" :disabled="form.currentlyEmployed==='是'" placeholder="例如：5200元/月"></label>
            </div>
          </div>
        </section>

        <section class="form-section" id="facts-section">
          <div class="section-heading"><span><i aria-hidden="true" class="fa-regular fa-pen-to-square"></i></span><div><small>第 4 步</small><h2>说明事情经过</h2><p>按时间顺序写清楚，不用写复杂的法律用语。</p></div></div>
          <div class="writing-tips"><span>建议写清</span><ul><li>什么时候入职、做什么工作</li><li>工资约定和实际发放情况</li><li>争议是怎样发生的</li><li>与上面各项要求有关的事实</li></ul></div>
          <label v-if="hasField('factsReason')" class="field"><span>事情经过和理由 <em>必填</em></span><textarea v-model.trim="form.factsReason" class="facts-area" rows="10" :maxlength="factsLimit" placeholder="例如：我于2024年3月1日入职该公司，担任……双方约定每月工资……从……开始，公司……"></textarea><small class="count">{{ form.factsReason.length }} / {{ factsLimit }}</small></label>
          <div class="fields two-columns compact-fields">
            <label v-if="hasField('applicationDate')" class="field"><span>申请日期</span><input v-model="form.applicationDate" type="date"></label>
            <label v-if="hasField('copyCount')" class="field"><span>申请书副本份数</span><input v-model.number="form.copyCount" type="number" min="1" max="20"><small>{{ config.copyHint }}</small></label>
          </div>
        </section>

        <div v-if="status.message" class="status-message" :class="status.type" role="status"><i aria-hidden="true" :class="status.type==='success'?'fa-solid fa-circle-check':'fa-solid fa-circle-exclamation'"></i>{{ status.message }}</div>
        <div class="submit-area"><div><strong>生成{{ config.name }}官方格式 Word 文档</strong><small><i aria-hidden="true" class="fa-solid fa-circle-info"></i> 签名栏保留空白，打印核对后本人手写签名。</small></div><button type="submit" :disabled="isSubmitting"><i aria-hidden="true" :class="isSubmitting?'fa-solid fa-spinner fa-spin':'fa-regular fa-file-word'"></i>{{ isSubmitting ? '正在生成…' : '生成并下载申请书' }}</button></div>
      </form>

      <aside v-if="!embedded" class="side-column">
        <div class="side-card official-info"><span class="side-label"><i aria-hidden="true" class="fa-solid fa-building-columns"></i> {{ config.shortName }}官方办事信息</span><h2>提交前先准备这些</h2><ul><li><i aria-hidden="true" class="fa-regular fa-id-card"></i><span><strong>身份证明</strong>身份证等有效证件</span></li><li><i aria-hidden="true" class="fa-regular fa-building"></i><span><strong>公司登记信息</strong>公司全称、代码和地址</span></li><li><i aria-hidden="true" class="fa-solid fa-link"></i><span><strong>劳动关系材料</strong>合同、工资流水、社保记录等</span></li><li><i aria-hidden="true" class="fa-regular fa-folder-open"></i><span><strong>支持你要求的证据</strong>{{ config.materialNote }}</span></li></ul><RouterLink v-if="config.evidenceRoute" :to="config.evidenceRoute"><i aria-hidden="true" class="fa-solid fa-list-check"></i> 接着制作证据清单</RouterLink></div>
        <div class="side-card online-card"><div><span>官方信息</span><strong>{{ config.promise }}</strong><small>来源适用范围：{{ config.scope }}</small></div><a :href="config.officialUrl" target="_blank" rel="noopener noreferrer">查看{{ config.shortName }}官方来源页 <i aria-hidden="true" class="fa-solid fa-arrow-up-right-from-square"></i></a></div>
        <div class="draft-note"><i aria-hidden="true" class="fa-regular fa-floppy-disk"></i><div><strong>内容已自动保存在这台设备</strong><p>刷新页面后仍可继续填写。下载完成后可用下方按钮清除。</p><button type="button" @click="clearDraft">清除已保存内容</button></div></div>
      </aside>
    </div>
  </component>

  <GenerateConfirmation :open="showConfirm" :template-only="templateOnly" :missing-fields="missingFields" :province-name="config.name" document-name="申请书" @cancel="showConfirm=false" @confirm="confirmGeneration" />
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
import {postProvincialDocument,provincialError,readProvincialDraft,saveProvincialDraft} from '@/api/provincial'
import { RouterLink } from 'vue-router'
import GenerateConfirmation from '@/components/GenerateConfirmation.vue'
import { downloadDocument } from '@/composables/downloadDocument'
import { findProvince, makeApplicationExample, applicationExtraFields, applicationSupportedFields, documentFormLimits, documentFieldDefinitions } from '@/data/provinces'

const props=withDefaults(defineProps<{province?:string;embedded?:boolean}>(),{province:'zhejiang',embedded:false})
const foundProvince=findProvince(props.province)
if(!foundProvince)throw new Error('未找到该省份的办事资料，请返回省份选择页。')
const province=foundProvince
const hasField=(key:string)=>(applicationSupportedFields[props.province]||[]).includes(key)
const config = computed(() => ({...province,backRoute:`/province/${province.slug}`,apiPath:`/api/province-documents/${province.slug}/application/generate`}))
const factsLimit = computed(() => documentFormLimits(props.province).factsLength)
const maxRequests = computed(() => documentFormLimits(props.province).maxRequests)
const showEmploymentDetails = computed(() => ['guangdong','hainan','xinjiang'].includes(props.province))
const DRAFT_KEY = `labourlawyer-${props.province}-application-draft-v6`
const steps = ['你的信息', '公司信息', '你的要求', '事情经过']
const focusedStep=ref(0)
const householdOptions = ['本省非农业户口','本省农业户口','外省非农业户口','外省农业户口','港澳台人员','外籍人员']
const blankDefaults = { committeeName:'',applicantName:'',birthDate:'',gender:'',nationality:'',idNumber:'',phone:'',householdType:'',idAddress:'',applicantMailingAddress:'',respondentName:'',socialCreditCode:'',registeredAddress:'',mailingAddress:'',workAddress:'',legalRepName:'',legalRepPhone:'',legalRepPosition:'',companyContact:'',companyContactPhone:'',requests:[''],claimCalculation:'',employmentDate:'',jobTitle:'',signedContract:'',contractStartDate:'',contractEndDate:'',workSchedule:'',attendanceRequired:'',attendanceMethod:'',salaryPaymentMethod:'',salaryReceiptRequired:'',startingSalary:'',salaryAdjustments:'',currentlyEmployed:'',departureDate:'',departureReason:'',averageMonthlySalary:'',factsReason:'',copyCount:1 as string|number,applicationDate:'' }
const defaults = { ...blankDefaults, ...makeApplicationExample(province) }
const loadedDraft=readProvincialDraft(DRAFT_KEY,defaults)
const hasSavedDraft=loadedDraft.saved
const draftBlocked=ref(loadedDraft.blocked)
const extraFields=applicationExtraFields[props.province]||[]
const form = reactive<typeof defaults & Record<string,unknown>>(loadedDraft.form)
if (!Array.isArray(form.requests) || !form.requests.length) form.requests = ['']
const isSubmitting = ref(false)
const showConfirm = ref(false)
const templateOnly = ref(false)
const usingExample = ref(!hasSavedDraft)
const missingFields = ref<string[]>([])
const status = reactive({ type:loadedDraft.notice?'error':'', message:loadedDraft.notice })
let saveTimer:ReturnType<typeof setTimeout>|undefined
const saveDraft=()=>{if(draftBlocked.value)return;const notice=saveProvincialDraft(DRAFT_KEY,form);if(notice){status.type='error';status.message=notice}}
window.addEventListener('pagehide',saveDraft)
watch(form, () => { clearTimeout(saveTimer); saveTimer = setTimeout(saveDraft, 350) }, { deep:true })
onBeforeUnmount(() => { clearTimeout(saveTimer);saveDraft();window.removeEventListener('pagehide',saveDraft) })
const activeStep = computed(() => !form.applicantName || !form.idNumber || !form.phone || !form.idAddress ? 0 : !form.respondentName || (hasField('registeredAddress')&&!form.registeredAddress) || (hasField('workAddress')&&!form.workAddress) ? 1 : !form.requests.some(item => item.trim()) ? 2 : 3)
const jumpToStep = (index:number) => {
  focusedStep.value=index
  const section=['applicant-section','company-section','requests-section','facts-section'][index]
  const target=section?document.getElementById(section):null
  target?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' })
  target?.querySelector<HTMLElement>('input, textarea, select')?.focus({ preventScroll:true })
}
const removeRequest = (index:number) => form.requests.splice(index, 1)
const clearDraft = () => { localStorage.removeItem(DRAFT_KEY);draftBlocked.value=false; Object.assign(form, { ...defaults, requests:[...defaults.requests] }); usingExample.value=true; status.type='success'; status.message='已清除保存内容，并恢复虚构示例。'; window.scrollTo({ top:0, behavior:'smooth' }) }
const collectMissingFields = () => {
  const missing:string[]=[]
  if(!form.committeeName) missing.push('仲裁委员会'); if(!form.applicantName) missing.push('姓名'); if(hasField('idNumber')&&!form.idNumber) missing.push('身份证号码'); if(!form.phone) missing.push('联系电话'); if(hasField('idAddress')&&!form.idAddress) missing.push('身份证住址'); if(!form.respondentName) missing.push('公司全称'); if(hasField('registeredAddress')&&!form.registeredAddress) missing.push('公司注册地址'); if(hasField('workAddress')&&!form.workAddress) missing.push('实际工作地址'); if(!form.requests.some(item=>item.trim())) missing.push('至少一项要求'); if(form.factsReason.length<10) missing.push('事情经过（至少填写 10 个字）')
  return missing
}
const parseError=(error:unknown)=>provincialError(error)
const requestGeneration = (blank:unknown=false) => { templateOnly.value=blank===true;if(draftBlocked.value&&!templateOnly.value){status.type='error';status.message=loadedDraft.notice;return}status.message=''; missingFields.value=templateOnly.value?[]:collectMissingFields(); showConfirm.value=true }
const confirmGeneration = () => { showConfirm.value=false; submitForm() }
const submitForm = async () => {
  status.message=''; isSubmitting.value=true
  try { const payload=templateOnly.value?{}:{...form,requests:form.requests.map(item=>item.trim()).filter(Boolean)}; const blob=await postProvincialDocument(config.value.apiPath,payload); const filename=!templateOnly.value&&form.applicantName?`${form.applicantName}的劳动人事争议仲裁申请书.docx`:`${config.value.name}劳动人事争议仲裁申请书.docx`;await downloadDocument(blob,filename);status.type='success';status.message='申请书已生成。请打开 Word 仔细核对后再签字提交。' } catch(error){status.type='error';status.message=await parseError(error)} finally{isSubmitting.value=false}
}
</script>
