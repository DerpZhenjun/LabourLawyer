<template>
  <div class="hunan-application-fields">
    <p class="hunan-notice">默认内容全部为虚构示例，请逐项替换为自己的情况；也可以清空后填写。未填写的位置留空。</p>
    <p class="region-small">本表用于劳动者申请。附随证据说明是申请书的一部分，随申请书一并填写。</p>
    <div class="region-actions hunan-actions">
      <button type="button" class="ll-button secondary" @click="replaceAll(createHunanApplicationExample())">载入虚构示例</button>
      <button type="button" class="ll-button secondary" @click="replaceAll(createEmptyHunanApplication())">清空填写内容</button>
    </div>

    <fieldset v-for="group in HUNAN_FIELD_GROUPS" :key="group.label" class="hunan-group">
      <legend>{{ group.label }}</legend>
      <div class="region-form-fields hunan-grid">
        <div v-for="field in group.fields" :key="field.key" class="hunan-field">
          <label :for="idFor(field.key)" class="regional-form-label">{{ field.label }}</label>
          <input
            :id="idFor(field.key)" :value="value?.[field.key] ?? ''" type="text"
            :inputmode="field.inputmode || 'text'" autocomplete="off"
            :aria-invalid="fieldError(field.key) ? 'true' : undefined" :aria-describedby="describedBy(field.key)"
            @input="updateField(field.key, $event.target.value)"
          >
          <p :id="idFor(`${field.key}-hint`)" class="region-small hunan-capacity">{{ field.hint ? `${field.hint} ` : '' }}{{ count(value?.[field.key]) }} / {{ HUNAN_LIMITS.ordinary }} 字符（含空格）</p>
          <p v-if="fieldError(field.key)" :id="idFor(`${field.key}-error`)" class="hunan-error">{{ fieldError(field.key) }}</p>
        </div>
      </div>
    </fieldset>

    <fieldset class="hunan-group" :aria-describedby="describedBy('requests')">
      <legend>请求事项</legend>
      <p :id="idFor('requests-hint')" class="region-small">逐项写清具体要求和金额，最多{{ HUNAN_LIMITS.requests }}项。已有文字不会自动裁剪。</p>
      <div v-for="(request, index) in requests" :key="index" class="hunan-list-item">
        <label :for="idFor(`requests.${index}`)" class="regional-form-label">第{{ index + 1 }}项请求</label>
        <textarea :id="idFor(`requests.${index}`)" :value="request" rows="3"
          :aria-invalid="fieldError(`requests.${index}`) ? 'true' : undefined" :aria-describedby="itemDescription(`requests.${index}`, 'requests')"
          @input="updateRequest(index, $event.target.value)"></textarea>
        <p v-if="fieldError(`requests.${index}`)" :id="idFor(`requests.${index}-error`)" class="hunan-error">{{ fieldError(`requests.${index}`) }}</p>
        <button type="button" class="ll-button secondary" :aria-label="`删除第${index + 1}项请求`" :disabled="requests.length <= 1" @click="removeRequest(index)">删除此项请求</button>
      </div>
      <p v-if="fieldError('requests')" :id="idFor('requests-error')" class="hunan-error">{{ fieldError('requests') }}</p>
      <button type="button" class="ll-button secondary" :disabled="requests.length >= HUNAN_LIMITS.requests || !requestShapeValid" @click="addRequest">添加请求事项</button>
      <p class="region-small">已填写 {{ requests.length }} / {{ HUNAN_LIMITS.requests }} 项请求。</p>
    </fieldset>

    <div class="hunan-group">
      <label :for="idFor('factsReason')" class="regional-form-label">事实与理由</label>
      <textarea :id="idFor('factsReason')" :value="value?.factsReason ?? ''" rows="7"
        :aria-invalid="fieldError('factsReason') ? 'true' : undefined" :aria-describedby="describedBy('factsReason')"
        @input="updateField('factsReason', $event.target.value)"></textarea>
      <p :id="idFor('factsReason-hint')" class="region-small hunan-capacity">{{ count(value?.factsReason) }} / {{ HUNAN_LIMITS.facts }} 字符（含空格和换行）；请写清事情经过及提出请求的理由。</p>
      <p v-if="fieldError('factsReason')" :id="idFor('factsReason-error')" class="hunan-error">{{ fieldError('factsReason') }}</p>
    </div>

    <fieldset class="hunan-group" :aria-describedby="describedBy('evidenceList')">
      <legend>申请书附随证据说明</legend>
      <p :id="idFor('evidenceList-hint')" class="region-small">此处随申请书生成，最多{{ HUNAN_LIMITS.evidence }}项；不是单独的证据清单文书。每一栏最多{{ HUNAN_LIMITS.evidenceField }}字符。</p>
      <fieldset v-for="(item, index) in evidence" :key="index" class="hunan-evidence-item" :aria-describedby="evidenceDescription(index)">
        <legend>第{{ index + 1 }}项附随证据</legend>
        <div v-for="field in HUNAN_EVIDENCE_FIELDS" :key="field.key" class="hunan-field">
          <label :for="idFor(`evidenceList.${index}.${field.key}`)" class="regional-form-label">{{ field.label }}</label>
          <textarea :id="idFor(`evidenceList.${index}.${field.key}`)" :value="item?.[field.key] ?? ''" rows="2"
            :aria-invalid="fieldError(`evidenceList.${index}.${field.key}`) ? 'true' : undefined"
            :aria-describedby="itemDescription(`evidenceList.${index}.${field.key}`, 'evidenceList')"
            @input="updateEvidence(index, field.key, $event.target.value)"></textarea>
          <p class="region-small hunan-capacity">{{ count(item?.[field.key]) }} / {{ HUNAN_LIMITS.evidenceField }} 字符（含空格）</p>
          <p v-if="fieldError(`evidenceList.${index}.${field.key}`)" :id="idFor(`evidenceList.${index}.${field.key}-error`)" class="hunan-error">{{ fieldError(`evidenceList.${index}.${field.key}`) }}</p>
        </div>
        <p v-if="fieldError(`evidenceList.${index}`)" :id="idFor(`evidenceList.${index}-error`)" class="hunan-error">{{ fieldError(`evidenceList.${index}`) }}</p>
        <p v-if="fieldError(`evidenceList.${index}.form`)" :id="idFor(`evidenceList.${index}.form-error`)" class="hunan-error">{{ fieldError(`evidenceList.${index}.form`) }}</p>
        <button type="button" class="ll-button secondary" :aria-label="`删除第${index + 1}项附随证据`" :disabled="evidence.length <= 1" @click="removeEvidence(index)">删除此项附随证据</button>
      </fieldset>
      <p v-if="fieldError('evidenceList')" :id="idFor('evidenceList-error')" class="hunan-error">{{ fieldError('evidenceList') }}</p>
      <button type="button" class="ll-button secondary" :disabled="evidence.length >= HUNAN_LIMITS.evidence || !evidenceShapeValid" @click="addEvidence">添加附随证据</button>
      <p class="region-small">已填写 {{ evidence.length }} / {{ HUNAN_LIMITS.evidence }} 项附随证据。</p>
    </fieldset>

    <p class="region-small">申请人签名始终留空，供本人核对后手写。申请日期和副本份数可留空。</p>
    <p v-if="fieldError('form')" :id="idFor('form-error')" class="hunan-error">{{ fieldError('form') }}</p>
    <p v-if="!validation.valid" class="hunan-error" role="status" aria-live="polite">还有{{ validation.errors.length }}处内容需要调整，调整后才能生成。已填写内容全部保留。</p>
  </div>
</template>

<script setup>
import {computed, onMounted, useId, watch} from 'vue'
import {
  HUNAN_LIMITS, HUNAN_FIELD_GROUPS, HUNAN_EVIDENCE_FIELDS, createHunanApplicationExample,
  createEmptyHunanApplication, hunanCharacterCount, validateHunanApplication, hunanApplicationPayload,
} from '@/data/hunanApplicationFields'

const props=defineProps({modelValue:{type:Object,default:undefined}})
const emit=defineEmits(['update:modelValue','validation'])
const initialExample=createHunanApplicationExample()
const value=computed(()=>props.modelValue===undefined?initialExample:props.modelValue)
const prefix=`hunan-${useId()}`
const idFor=key=>`${prefix}-${key}`
const count=hunanCharacterCount
const validation=computed(()=>validateHunanApplication(value.value))
const fieldError=key=>validation.value.errors.find(error=>error.field===key)?.message||''
const describedBy=key=>`${idFor(`${key}-hint`)}${fieldError(key)?` ${idFor(`${key}-error`)}`:''}`
const itemDescription=(key,group)=>`${idFor(`${group}-hint`)}${fieldError(key)?` ${idFor(`${key}-error`)}`:''}`
const evidenceDescription=index=>`${idFor('evidenceList-hint')}${fieldError(`evidenceList.${index}`)?` ${idFor(`evidenceList.${index}-error`)}`:''}${fieldError(`evidenceList.${index}.form`)?` ${idFor(`evidenceList.${index}.form-error`)}`:''}`
const requestShapeValid=computed(()=>value.value?.requests===undefined||Array.isArray(value.value.requests))
const evidenceShapeValid=computed(()=>value.value?.evidenceList===undefined||Array.isArray(value.value.evidenceList))
const requests=computed(()=>Array.isArray(value.value?.requests)&&value.value.requests.length?value.value.requests:[typeof value.value?.requests==='string'?value.value.requests:''])
const evidence=computed(()=>Array.isArray(value.value?.evidenceList)&&value.value.evidenceList.length?value.value.evidenceList:[{name:'',source:'',purpose:''}])
const updateField=(key,next)=>emit('update:modelValue',{...value.value,[key]:next})
const replaceAll=next=>emit('update:modelValue',next)
function updateRequest(index,text){const next=[...requests.value];next[index]=text;updateField('requests',next)}
function addRequest(){if(requestShapeValid.value&&requests.value.length<HUNAN_LIMITS.requests)updateField('requests',[...requests.value,''])}
function removeRequest(index){if(requests.value.length>1){const next=[...requests.value];next.splice(index,1);updateField('requests',next)}}
function updateEvidence(index,key,text){const next=[...evidence.value];next[index]={...next[index],[key]:text};updateField('evidenceList',next)}
function addEvidence(){if(evidenceShapeValid.value&&evidence.value.length<HUNAN_LIMITS.evidence)updateField('evidenceList',[...evidence.value,{name:'',source:'',purpose:''}])}
function removeEvidence(index){if(evidence.value.length>1){const next=[...evidence.value];next.splice(index,1);updateField('evidenceList',next)}}
watch(validation,result=>emit('validation',result),{immediate:true,deep:true})
onMounted(()=>{if(props.modelValue===undefined)emit('update:modelValue',createHunanApplicationExample())})
defineExpose({validate:()=>validateHunanApplication(value.value),getPayload:()=>hunanApplicationPayload(value.value)})
</script>

<style scoped>
.hunan-application-fields{min-width:0;max-width:100%}
.hunan-notice{margin:0 0 12px;color:var(--ll-secondary);line-height:1.8}
.hunan-actions{display:flex;flex-wrap:wrap;gap:12px;margin:16px 0 24px}
.hunan-application-fields button{min-height:44px;white-space:normal}
.hunan-group{min-width:0;margin:0 0 24px;padding:0 0 24px;border:0;border-bottom:1px solid var(--ll-border)}
.hunan-group>legend,.hunan-evidence-item>legend{float:none;width:auto;padding:0;font-size:18px;font-weight:650;line-height:1.6}
.hunan-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px;margin-top:16px}
.hunan-field{min-width:0}
.regional-form-label{display:block;margin:0 0 8px;font-weight:600;line-height:1.6}
.hunan-application-fields :is(input,textarea){box-sizing:border-box;width:100%;min-width:0;max-width:100%;min-height:44px;padding:10px 12px;border:1px solid var(--ll-border-strong);border-radius:8px;background:var(--ll-surface,#fff);color:var(--ll-text);font:inherit;font-size:16px;line-height:1.7}
.hunan-application-fields textarea{min-height:96px;resize:vertical;overflow-wrap:anywhere}
.hunan-application-fields :is(input,textarea,button):focus-visible{outline:3px solid var(--ll-primary);outline-offset:2px}
.hunan-application-fields [aria-invalid=true]{border-color:var(--ll-danger,#a82622)}
.hunan-list-item,.hunan-evidence-item{min-width:0;margin:16px 0;padding:0 0 16px;border:0;border-bottom:1px solid var(--ll-border)}
.hunan-list-item button,.hunan-evidence-item button{margin-top:12px}
.hunan-evidence-item .hunan-field{margin-top:16px}
.hunan-capacity{margin:8px 0 0;font-size:14px;line-height:1.7;overflow-wrap:anywhere}
.hunan-error{margin:8px 0 0;color:var(--ll-danger,#a82622);font-size:14px;line-height:1.7;overflow-wrap:anywhere}
@media(max-width:600px){.hunan-grid{grid-template-columns:minmax(0,1fr);gap:16px}.hunan-actions button{flex:1 1 160px;min-width:0}.hunan-list-item button,.hunan-evidence-item button{max-width:100%}}
</style>
