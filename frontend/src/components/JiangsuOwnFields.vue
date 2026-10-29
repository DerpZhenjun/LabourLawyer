<template>
  <div class="jiangsu-own-fields">
    <p class="jiangsu-notice">默认内容全部为虚构示例，请逐项替换为自己的情况；也可以清空后填写。未填写的位置留空。</p>
    <p class="region-small">{{ kind === 'application' ? '本表用于劳动者申请，申请人签名留空，供本人核对后手写。' : '本表单独生成证据清单，提交人和接收人签字位置留空。' }}日期不会自动填写；申请书的两类副本份数不会预填，独立证据清单没有份数栏目。</p>
    <div class="region-actions jiangsu-actions">
      <button type="button" class="ll-button secondary" @click="replaceAll(createJiangsuOwnExample(kind))">载入虚构示例</button>
      <button type="button" class="ll-button secondary" @click="replaceAll(createEmptyJiangsuOwn(kind))">清空填写内容</button>
    </div>

    <fieldset v-for="group in groups" :key="group.label" class="jiangsu-group">
      <legend>{{ group.label }}</legend>
      <div class="region-form-fields jiangsu-grid">
        <div v-for="field in group.fields" :key="field.key" class="jiangsu-field">
          <label :for="idFor(field.key)" class="regional-form-label">{{ field.label }}</label>
          <input :id="idFor(field.key)" :value="value?.[field.key] ?? ''" type="text" autocomplete="off"
            :disabled="!formShapeValid" :inputmode="field.inputmode || 'text'"
            :aria-invalid="fieldError(field.key) ? 'true' : undefined" :aria-describedby="description(field.key)"
            @input="updateField(field.key, $event.target.value)">
          <p :id="idFor(`${field.key}-hint`)" class="region-small jiangsu-capacity">
            {{ field.hint || '' }}
            <template v-if="!['copyCount','evidenceCopyCount'].includes(field.key)"> {{ count(value?.[field.key]) }} / {{ JIANGSU_OWN_LIMITS.ordinary }} 字符（含空格）</template>
          </p>
          <p v-if="fieldError(field.key)" :id="idFor(`${field.key}-error`)" class="jiangsu-error">{{ fieldError(field.key) }}</p>
        </div>
      </div>
    </fieldset>

    <template v-if="kind === 'application'">
      <fieldset class="jiangsu-group" :aria-describedby="description('requests')">
        <legend>请求事项</legend>
        <p :id="idFor('requests-hint')" class="region-small">逐项写清具体要求和金额，最多4项，每项最多1200字符。已有文字不会自动裁剪。</p>
        <div v-for="(request, index) in requests" :key="index" class="jiangsu-list-item">
          <label :for="idFor(`requests.${index}`)" class="regional-form-label">第{{ index + 1 }}项请求</label>
          <textarea :id="idFor(`requests.${index}`)" :value="request" rows="3" :disabled="!formShapeValid || !requestShapeValid"
            :aria-invalid="fieldError(`requests.${index}`) ? 'true' : undefined" :aria-describedby="itemDescription(`requests.${index}`, 'requests')"
            @input="updateRequest(index, $event.target.value)"></textarea>
          <p class="region-small jiangsu-capacity">{{ count(request) }} / {{ JIANGSU_OWN_LIMITS.request }} 字符</p>
          <p v-if="fieldError(`requests.${index}`)" :id="idFor(`requests.${index}-error`)" class="jiangsu-error">{{ fieldError(`requests.${index}`) }}</p>
          <button type="button" class="ll-button secondary" :aria-label="`删除第${index + 1}项请求`"
            :disabled="requests.length <= 1 || !requestShapeValid || !formShapeValid" @click="removeRequest(index)">删除此项请求</button>
        </div>
        <p v-if="fieldError('requests')" :id="idFor('requests-error')" class="jiangsu-error">{{ fieldError('requests') }}</p>
        <button type="button" class="ll-button secondary" :disabled="requests.length >= 4 || !requestShapeValid || !formShapeValid" @click="addRequest">添加请求事项</button>
        <p class="region-small">已填写 {{ requests.length }} / 4 项请求。</p>
      </fieldset>
      <div class="jiangsu-group">
        <label :for="idFor('factsReason')" class="regional-form-label">事实与理由</label>
        <textarea :id="idFor('factsReason')" :value="value?.factsReason ?? ''" rows="7" :disabled="!formShapeValid"
          :aria-invalid="fieldError('factsReason') ? 'true' : undefined" :aria-describedby="description('factsReason')"
          @input="updateField('factsReason', $event.target.value)"></textarea>
        <p :id="idFor('factsReason-hint')" class="region-small jiangsu-capacity">{{ count(value?.factsReason) }} / {{ JIANGSU_OWN_LIMITS.factsReason }} 字符（含空格和换行）；请写清事情经过及提出请求的理由。</p>
        <p v-if="fieldError('factsReason')" :id="idFor('factsReason-error')" class="jiangsu-error">{{ fieldError('factsReason') }}</p>
      </div>
    </template>

    <fieldset v-if="kind === 'evidence'" class="jiangsu-group" :aria-describedby="description('evidenceList')">
      <legend>证据内容</legend>
      <p :id="idFor('evidenceList-hint')" class="region-small">逐项填写证据名称、来源、证明内容、原件或复印件和页数，最多40项。未确定的栏目可以留空。</p>
      <fieldset v-for="(item, index) in evidence" :key="index" class="jiangsu-evidence-item" :aria-describedby="evidenceDescription(index)">
        <legend>第{{ index + 1 }}项证据</legend>
        <div class="jiangsu-grid">
          <div v-for="field in JIANGSU_OWN_EVIDENCE_FIELDS" :key="field.key" class="jiangsu-field">
            <label :for="idFor(`evidenceList.${index}.${field.key}`)" class="regional-form-label">{{ field.label }}</label>
            <textarea :id="idFor(`evidenceList.${index}.${field.key}`)" :value="item?.[field.key] ?? ''" rows="2"
              :disabled="!formShapeValid || !evidenceShapeValid || !isObject(item)"
              :aria-invalid="fieldError(`evidenceList.${index}.${field.key}`) ? 'true' : undefined"
              :aria-describedby="itemDescription(`evidenceList.${index}.${field.key}`, 'evidenceList')"
              @input="updateEvidence(index, field.key, $event.target.value)"></textarea>
            <p class="region-small jiangsu-capacity">{{ count(item?.[field.key]) }} / {{ field.limit }} 字符（含空格和换行）</p>
            <p v-if="fieldError(`evidenceList.${index}.${field.key}`)" :id="idFor(`evidenceList.${index}.${field.key}-error`)" class="jiangsu-error">{{ fieldError(`evidenceList.${index}.${field.key}`) }}</p>
          </div>
        </div>
        <p v-if="fieldError(`evidenceList.${index}`)" :id="idFor(`evidenceList.${index}-error`)" class="jiangsu-error">{{ fieldError(`evidenceList.${index}`) }}</p>
        <p v-if="fieldError(`evidenceList.${index}.form`)" :id="idFor(`evidenceList.${index}.form-error`)" class="jiangsu-error">{{ fieldError(`evidenceList.${index}.form`) }}</p>
        <button type="button" class="ll-button secondary" :aria-label="`删除第${index + 1}项证据`"
          :disabled="evidence.length <= 1 || !evidenceShapeValid || !formShapeValid" @click="removeEvidence(index)">删除此项证据</button>
      </fieldset>
      <p v-if="fieldError('evidenceList')" :id="idFor('evidenceList-error')" class="jiangsu-error">{{ fieldError('evidenceList') }}</p>
      <button type="button" class="ll-button secondary" :disabled="evidence.length >= 40 || !evidenceShapeValid || !formShapeValid" @click="addEvidence">添加证据</button>
      <p class="region-small">已填写 {{ evidence.length }} / 40 项证据。</p>
    </fieldset>
    <p v-if="fieldError('form')" :id="idFor('form-error')" class="jiangsu-error">{{ fieldError('form') }}</p>
    <p v-if="!validation.valid" class="jiangsu-error" role="status" aria-live="polite">还有{{ validation.errors.length }}处内容需要调整，调整后才能生成。已填写内容全部保留。</p>
  </div>
</template>

<script setup>
import {computed, onMounted, useId, watch} from 'vue'
import {JIANGSU_OWN_LIMITS, JIANGSU_OWN_FIELD_GROUPS, JIANGSU_OWN_EVIDENCE_FIELDS,
  createEmptyJiangsuOwn, createJiangsuOwnExample, validateJiangsuOwn, jiangsuOwnPayload, jiangsuOwnCharacterCount,
  jiangsuOwnDraftIsObject, jiangsuOwnCopyObject, jiangsuOwnCopyList} from '@/data/jiangsuOwnFields'

const props=defineProps({modelValue:{type:Object,default:undefined},kind:{type:String,default:'application',validator:v=>['application','evidence'].includes(v)}})
const emit=defineEmits(['update:modelValue','validation'])
const initial=computed(()=>createJiangsuOwnExample(props.kind==='evidence'?'evidence':'application'))
const value=computed(()=>props.modelValue===undefined?initial.value:props.modelValue)
const groups=computed(()=>JIANGSU_OWN_FIELD_GROUPS[props.kind]||[])
const prefix=`jiangsu-own-${useId()}`,idFor=key=>`${prefix}-${key}`
const count=jiangsuOwnCharacterCount,isObject=jiangsuOwnDraftIsObject
const formShapeValid=computed(()=>isObject(value.value))
const validation=computed(()=>validateJiangsuOwn(value.value,props.kind))
const fieldError=key=>validation.value.errors.find(error=>error.field===key)?.message||''
const description=key=>`${idFor(`${key}-hint`)}${fieldError(key)?` ${idFor(`${key}-error`)}`:''}`
const itemDescription=(key,group)=>`${idFor(`${group}-hint`)}${fieldError(key)?` ${idFor(`${key}-error`)}`:''}`
const evidenceDescription=i=>`${idFor('evidenceList-hint')}${fieldError(`evidenceList.${i}`)?` ${idFor(`evidenceList.${i}-error`)}`:''}${fieldError(`evidenceList.${i}.form`)?` ${idFor(`evidenceList.${i}.form-error`)}`:''}`
const requestShapeValid=computed(()=>value.value?.requests===undefined||Array.isArray(value.value.requests))
const evidenceShapeValid=computed(()=>value.value?.evidenceList===undefined||Array.isArray(value.value.evidenceList))
function atLeastOne(list,empty){if(Array.isArray(list)){if(list.length)return list;const next=jiangsuOwnCopyList(list);next.push(empty);return next}return[empty]}
const requests=computed(()=>atLeastOne(value.value?.requests,typeof value.value?.requests==='string'?value.value.requests:''))
const evidence=computed(()=>atLeastOne(value.value?.evidenceList,{name:'',source:'',purpose:'',originalType:'',pageCount:''}))
function updateField(key,next){if(formShapeValid.value)emit('update:modelValue',{...jiangsuOwnCopyObject(value.value),[key]:next})}
const replaceAll=next=>emit('update:modelValue',next)
function updateRequest(i,text){if(!requestShapeValid.value)return;const next=jiangsuOwnCopyList(requests.value);next[i]=text;updateField('requests',next)}
function addRequest(){if(requestShapeValid.value&&requests.value.length<4){const next=jiangsuOwnCopyList(requests.value);next.push('');updateField('requests',next)}}
function removeRequest(i){if(requestShapeValid.value&&requests.value.length>1){const next=jiangsuOwnCopyList(requests.value);next.splice(i,1);updateField('requests',next)}}
function updateEvidence(i,key,text){if(!evidenceShapeValid.value||!isObject(evidence.value[i]))return;const next=jiangsuOwnCopyList(evidence.value);next[i]={...jiangsuOwnCopyObject(next[i]),[key]:text};updateField('evidenceList',next)}
function addEvidence(){if(evidenceShapeValid.value&&evidence.value.length<40){const next=jiangsuOwnCopyList(evidence.value);next.push({name:'',source:'',purpose:'',originalType:'',pageCount:''});updateField('evidenceList',next)}}
function removeEvidence(i){if(evidenceShapeValid.value&&evidence.value.length>1){const next=jiangsuOwnCopyList(evidence.value);next.splice(i,1);updateField('evidenceList',next)}}
watch(validation,result=>emit('validation',result),{immediate:true,deep:true})
onMounted(()=>{if(props.modelValue===undefined)emit('update:modelValue',createJiangsuOwnExample(props.kind))})
defineExpose({validate:()=>validateJiangsuOwn(value.value,props.kind),getPayload:()=>jiangsuOwnPayload(value.value,props.kind)})
</script>

<style scoped>
.jiangsu-own-fields{min-width:0;max-width:100%}
.jiangsu-notice{margin:0 0 12px;color:var(--ll-secondary);line-height:1.8}
.jiangsu-actions{display:flex;flex-wrap:wrap;gap:12px;margin:16px 0 24px}
.jiangsu-own-fields button{min-height:44px;white-space:normal}
.jiangsu-group{min-width:0;margin:0 0 24px;padding:0 0 24px;border:0;border-bottom:1px solid var(--ll-border)}
.jiangsu-group>legend,.jiangsu-evidence-item>legend{float:none;width:auto;padding:0;font-size:18px;font-weight:650;line-height:1.6}
.jiangsu-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px;margin-top:16px}
.jiangsu-field{min-width:0}
.regional-form-label{display:block;margin:0 0 8px;font-weight:600;line-height:1.6}
.jiangsu-own-fields :is(input,textarea,select){box-sizing:border-box;width:100%;min-width:0;max-width:100%;min-height:44px;padding:10px 12px;border:1px solid var(--ll-border-strong);border-radius:8px;background:var(--ll-surface,#fff);color:var(--ll-text);font:inherit;font-size:16px;line-height:1.7}
.jiangsu-own-fields textarea{min-height:96px;resize:vertical;overflow-wrap:anywhere}
.jiangsu-own-fields :is(input,textarea,select,button):focus-visible{outline:3px solid var(--ll-primary);outline-offset:2px}
.jiangsu-own-fields [aria-invalid=true]{border-color:var(--ll-danger,#a82622)}
.jiangsu-list-item,.jiangsu-evidence-item{min-width:0;margin:16px 0;padding:0 0 16px;border:0;border-bottom:1px solid var(--ll-border)}
.jiangsu-list-item button,.jiangsu-evidence-item button{margin-top:12px}
.jiangsu-capacity{margin:8px 0 0;font-size:14px;line-height:1.7;overflow-wrap:anywhere}
.jiangsu-error{margin:8px 0 0;color:var(--ll-danger,#a82622);font-size:14px;line-height:1.7;overflow-wrap:anywhere}
@media(max-width:600px){.jiangsu-grid{grid-template-columns:minmax(0,1fr);gap:16px}.jiangsu-actions button{flex:1 1 160px;min-width:0}.jiangsu-list-item button,.jiangsu-evidence-item button{max-width:100%}}
</style>
