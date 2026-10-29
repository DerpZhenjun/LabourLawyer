<template>
  <div class="zhejiang-own-fields">
    <p class="zhejiang-notice">默认内容全部为虚构示例，请逐项替换为自己的情况；也可以清空后填写。未填写的位置留空。</p>
    <p class="region-small">{{ kind === 'application' ? '本表用于劳动者申请，申请人签名留空，供本人核对后手写。' : '本表单独生成证据清单，提交人和接收人签字位置留空。' }}日期和份数不会自动填写。</p>
    <div class="region-actions zhejiang-actions">
      <button type="button" class="ll-button secondary" @click="replaceAll(createZhejiangOwnExample(kind))">载入虚构示例</button>
      <button type="button" class="ll-button secondary" @click="replaceAll(createEmptyZhejiangOwn(kind))">清空填写内容</button>
    </div>

    <fieldset v-for="group in groups" :key="group.label" class="zhejiang-group">
      <legend>{{ group.label }}</legend>
      <div class="region-form-fields zhejiang-grid">
        <div v-for="field in group.fields" :key="field.key" class="zhejiang-field">
          <label :for="idFor(field.key)" class="regional-form-label">{{ field.label }}</label>
          <select v-if="field.key === 'householdType'" :id="idFor(field.key)" :value="value?.[field.key] ?? ''"
            :disabled="!formShapeValid" :aria-invalid="fieldError(field.key) ? 'true' : undefined" :aria-describedby="description(field.key)"
            @change="updateField(field.key, eventValue($event))">
            <option value="">留空，打印后本人核对</option>
            <option v-for="choice in ZHEJIANG_HOUSEHOLD_CHOICES" :key="choice" :value="choice">{{ choice }}</option>
            <option v-if="value?.householdType && !householdChoice(value.householdType)" :value="value.householdType">{{ value.householdType }}（请核对）</option>
          </select>
          <input v-else :id="idFor(field.key)" :value="value?.[field.key] ?? ''" type="text" autocomplete="off"
            :disabled="!formShapeValid" :inputmode="field.inputmode || 'text'"
            :aria-invalid="fieldError(field.key) ? 'true' : undefined" :aria-describedby="description(field.key)"
            @input="updateField(field.key, eventValue($event))">
          <p :id="idFor(`${field.key}-hint`)" class="region-small zhejiang-capacity">
            {{ field.hint || '' }}
            <template v-if="field.key !== 'copyCount'"> {{ count(value?.[field.key]) }} / {{ ZHEJIANG_OWN_LIMITS.ordinary }} 字符（含空格）</template>
            <template v-if="field.key === 'householdType'">原件“外省非农业户口”出现两次，不能确定时请留空，打印后在纸面确认，不会替你勾选。</template>
          </p>
          <p v-if="fieldError(field.key)" :id="idFor(`${field.key}-error`)" class="zhejiang-error">{{ fieldError(field.key) }}</p>
        </div>
      </div>
    </fieldset>

    <template v-if="kind === 'application'">
      <fieldset class="zhejiang-group" :aria-describedby="description('requests')">
        <legend>请求事项</legend>
        <p :id="idFor('requests-hint')" class="region-small">逐项写清具体要求和金额，最多4项，每项最多1200字符。已有文字不会自动裁剪。</p>
        <div v-for="(request, index) in requests" :key="index" class="zhejiang-list-item">
          <label :for="idFor(`requests.${index}`)" class="regional-form-label">第{{ index + 1 }}项请求</label>
          <textarea :id="idFor(`requests.${index}`)" :value="displayText(request)" rows="3" :disabled="!formShapeValid || !requestShapeValid"
            :aria-invalid="fieldError(`requests.${index}`) ? 'true' : undefined" :aria-describedby="itemDescription(`requests.${index}`, 'requests')"
            @input="updateRequest(index, eventValue($event))"></textarea>
          <p class="region-small zhejiang-capacity">{{ count(request) }} / {{ ZHEJIANG_OWN_LIMITS.request }} 字符</p>
          <p v-if="fieldError(`requests.${index}`)" :id="idFor(`requests.${index}-error`)" class="zhejiang-error">{{ fieldError(`requests.${index}`) }}</p>
          <button type="button" class="ll-button secondary" :aria-label="`删除第${index + 1}项请求`"
            :disabled="requests.length <= 1 || !requestShapeValid || !formShapeValid" @click="removeRequest(index)">删除此项请求</button>
        </div>
        <p v-if="fieldError('requests')" :id="idFor('requests-error')" class="zhejiang-error">{{ fieldError('requests') }}</p>
        <button type="button" class="ll-button secondary" :disabled="requests.length >= 4 || !requestShapeValid || !formShapeValid" @click="addRequest">添加请求事项</button>
        <p class="region-small">已填写 {{ requests.length }} / 4 项请求。</p>
      </fieldset>
      <div class="zhejiang-group">
        <label :for="idFor('factsReason')" class="regional-form-label">事实与理由</label>
        <textarea :id="idFor('factsReason')" :value="displayText(value?.factsReason)" rows="7" :disabled="!formShapeValid"
          :aria-invalid="fieldError('factsReason') ? 'true' : undefined" :aria-describedby="description('factsReason')"
          @input="updateField('factsReason', eventValue($event))"></textarea>
        <p :id="idFor('factsReason-hint')" class="region-small zhejiang-capacity">{{ count(value?.factsReason) }} / {{ ZHEJIANG_OWN_LIMITS.factsReason }} 字符（含空格和换行）；请写清事情经过及提出请求的理由。</p>
        <p v-if="fieldError('factsReason')" :id="idFor('factsReason-error')" class="zhejiang-error">{{ fieldError('factsReason') }}</p>
      </div>
    </template>

    <fieldset v-if="kind === 'evidence'" class="zhejiang-group" :aria-describedby="description('evidenceList')">
      <legend>证据内容</legend>
      <p :id="idFor('evidenceList-hint')" class="region-small">逐项填写证据名称、页数、来源和证明内容，最多40项。未确定的栏目可以留空。</p>
      <fieldset v-for="(item, index) in evidence" :key="index" class="zhejiang-evidence-item" :aria-describedby="evidenceDescription(index)">
        <legend>第{{ index + 1 }}项证据</legend>
        <div class="zhejiang-grid">
          <div v-for="field in ZHEJIANG_OWN_EVIDENCE_FIELDS" :key="field.key" class="zhejiang-field">
            <label :for="idFor(`evidenceList.${index}.${field.key}`)" class="regional-form-label">{{ field.label }}</label>
            <textarea :id="idFor(`evidenceList.${index}.${field.key}`)" :value="displayText(itemValue(item,field.key))" rows="2"
              :disabled="!formShapeValid || !evidenceShapeValid || !isObject(item)"
              :aria-invalid="fieldError(`evidenceList.${index}.${field.key}`) ? 'true' : undefined"
              :aria-describedby="itemDescription(`evidenceList.${index}.${field.key}`, 'evidenceList')"
              @input="updateEvidence(index, field.key, eventValue($event))"></textarea>
            <p class="region-small zhejiang-capacity">{{ count(itemValue(item,field.key)) }} / {{ field.limit }} 字符（含空格和换行）</p>
            <p v-if="fieldError(`evidenceList.${index}.${field.key}`)" :id="idFor(`evidenceList.${index}.${field.key}-error`)" class="zhejiang-error">{{ fieldError(`evidenceList.${index}.${field.key}`) }}</p>
          </div>
        </div>
        <p v-if="fieldError(`evidenceList.${index}`)" :id="idFor(`evidenceList.${index}-error`)" class="zhejiang-error">{{ fieldError(`evidenceList.${index}`) }}</p>
        <p v-if="fieldError(`evidenceList.${index}.form`)" :id="idFor(`evidenceList.${index}.form-error`)" class="zhejiang-error">{{ fieldError(`evidenceList.${index}.form`) }}</p>
        <button type="button" class="ll-button secondary" :aria-label="`删除第${index + 1}项证据`"
          :disabled="evidence.length <= 1 || !evidenceShapeValid || !formShapeValid" @click="removeEvidence(index)">删除此项证据</button>
      </fieldset>
      <p v-if="fieldError('evidenceList')" :id="idFor('evidenceList-error')" class="zhejiang-error">{{ fieldError('evidenceList') }}</p>
      <button type="button" class="ll-button secondary" :disabled="evidence.length >= 40 || !evidenceShapeValid || !formShapeValid" @click="addEvidence">添加证据</button>
      <p class="region-small">已填写 {{ evidence.length }} / 40 项证据。</p>
    </fieldset>
    <p v-if="fieldError('form')" :id="idFor('form-error')" class="zhejiang-error">{{ fieldError('form') }}</p>
    <p v-if="!validation.valid" class="zhejiang-error" role="status" aria-live="polite">还有{{ validation.errors.length }}处内容需要调整，调整后才能生成。已填写内容全部保留。</p>
  </div>
</template>

<script setup lang="ts">
import {computed, onMounted, useId, watch} from 'vue'
import {ZHEJIANG_OWN_LIMITS, ZHEJIANG_OWN_FIELD_GROUPS, ZHEJIANG_OWN_EVIDENCE_FIELDS, ZHEJIANG_HOUSEHOLD_CHOICES,
  createEmptyZhejiangOwn, createZhejiangOwnExample, validateZhejiangOwn, zhejiangOwnPayload, zhejiangOwnCharacterCount,
  zhejiangOwnDraftIsObject, zhejiangOwnCopyObject, zhejiangOwnCopyList} from '@/data/zhejiangOwnFields'
import type {ZhejiangOwnValidation,ZhejiangOwnEditableKey,ZhejiangOwnEvidenceItem} from '@/data/zhejiangOwnFields'

const props=withDefaults(defineProps<{modelValue?: unknown; kind?: 'application' | 'evidence'}>(),{kind:'application'})
const emit=defineEmits<{'update:modelValue': [value: unknown]; validation: [result: ZhejiangOwnValidation]}>()
const count=zhejiangOwnCharacterCount,isObject=zhejiangOwnDraftIsObject
const initial=computed(()=>createZhejiangOwnExample(props.kind==='evidence'?'evidence':'application'))
const rawValue=computed<unknown>(()=>props.modelValue===undefined?initial.value:props.modelValue)
// Rendering gets a guarded view. Validation and emitted updates retain raw data.
const value=computed(()=>isObject(rawValue.value)?rawValue.value:undefined)
const groups=computed(()=>ZHEJIANG_OWN_FIELD_GROUPS[props.kind]||[])
const prefix=`zhejiang-own-${useId()}`,idFor=(key: string)=>`${prefix}-${key}`
const formShapeValid=computed(()=>isObject(rawValue.value))
const validation=computed(()=>validateZhejiangOwn(rawValue.value,props.kind))
const fieldError=(key: string)=>validation.value.errors.find(error=>error.field===key)?.message||''
const description=(key: string)=>`${idFor(`${key}-hint`)}${fieldError(key)?` ${idFor(`${key}-error`)}`:''}`
const itemDescription=(key: string,group: string)=>`${idFor(`${group}-hint`)}${fieldError(key)?` ${idFor(`${key}-error`)}`:''}`
const evidenceDescription=(i: number)=>`${idFor('evidenceList-hint')}${fieldError(`evidenceList.${i}`)?` ${idFor(`evidenceList.${i}-error`)}`:''}${fieldError(`evidenceList.${i}.form`)?` ${idFor(`evidenceList.${i}.form-error`)}`:''}`
const requestShapeValid=computed(()=>value.value?.requests===undefined||Array.isArray(value.value.requests))
const evidenceShapeValid=computed(()=>value.value?.evidenceList===undefined||Array.isArray(value.value.evidenceList))
function atLeastOne(list: unknown,empty: unknown): unknown[]{
  if(Array.isArray(list)){if(list.length)return list;const next=zhejiangOwnCopyList(list);next.push(empty);return next}
  return[empty]
}
const requests=computed(()=>atLeastOne(value.value?.requests,typeof value.value?.requests==='string'?value.value.requests:''))
const evidence=computed(()=>atLeastOne(value.value?.evidenceList,{name:'',pageCount:'',source:'',purpose:''}))
function itemValue(item: unknown,key: keyof ZhejiangOwnEvidenceItem): unknown{return isObject(item)?item[key]:undefined}
// Presentation only; the original unknown draft remains the validation input.
function displayText(value: unknown): string{return typeof value==='string'?value:String(value??'')}
function householdChoice(value: unknown): boolean{return typeof value==='string'&&ZHEJIANG_HOUSEHOLD_CHOICES.includes(value)}
function eventValue(event: {target: unknown}): string{
  const target=event.target
  return target!==null&&typeof target==='object'&&'value' in target&&typeof target.value==='string'?target.value:''
}
function updateField(key: ZhejiangOwnEditableKey,next: unknown){
  const current=rawValue.value
  if(isObject(current))emit('update:modelValue',{...zhejiangOwnCopyObject(current),[key]:next})
}
const replaceAll=(next: unknown)=>emit('update:modelValue',next)
function updateRequest(i: number,text: string){if(!requestShapeValid.value)return;const next=zhejiangOwnCopyList(requests.value);next[i]=text;updateField('requests',next)}
function addRequest(){if(requestShapeValid.value&&requests.value.length<4){const next=zhejiangOwnCopyList(requests.value);next.push('');updateField('requests',next)}}
function removeRequest(i: number){if(requestShapeValid.value&&requests.value.length>1){const next=zhejiangOwnCopyList(requests.value);next.splice(i,1);updateField('requests',next)}}
function updateEvidence(i: number,key: keyof ZhejiangOwnEvidenceItem,text: string){
  const item=evidence.value[i]
  if(!evidenceShapeValid.value||!isObject(item))return
  const next=zhejiangOwnCopyList(evidence.value);next[i]={...zhejiangOwnCopyObject(item),[key]:text};updateField('evidenceList',next)
}
function addEvidence(){if(evidenceShapeValid.value&&evidence.value.length<40){const next=zhejiangOwnCopyList(evidence.value);next.push({name:'',pageCount:'',source:'',purpose:''});updateField('evidenceList',next)}}
function removeEvidence(i: number){if(evidenceShapeValid.value&&evidence.value.length>1){const next=zhejiangOwnCopyList(evidence.value);next.splice(i,1);updateField('evidenceList',next)}}
watch(validation,result=>emit('validation',result),{immediate:true,deep:true})
onMounted(()=>{if(props.modelValue===undefined)emit('update:modelValue',createZhejiangOwnExample(props.kind))})
defineExpose({validate:()=>validateZhejiangOwn(rawValue.value,props.kind),getPayload:()=>zhejiangOwnPayload(rawValue.value,props.kind)})
</script>

<style scoped>
.zhejiang-own-fields{min-width:0;max-width:100%}
.zhejiang-notice{margin:0 0 12px;color:var(--ll-secondary);line-height:1.8}
.zhejiang-actions{display:flex;flex-wrap:wrap;gap:12px;margin:16px 0 24px}
.zhejiang-own-fields button{min-height:44px;white-space:normal}
.zhejiang-group{min-width:0;margin:0 0 24px;padding:0 0 24px;border:0;border-bottom:1px solid var(--ll-border)}
.zhejiang-group>legend,.zhejiang-evidence-item>legend{float:none;width:auto;padding:0;font-size:18px;font-weight:650;line-height:1.6}
.zhejiang-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px;margin-top:16px}
.zhejiang-field{min-width:0}
.regional-form-label{display:block;margin:0 0 8px;font-weight:600;line-height:1.6}
.zhejiang-own-fields :is(input,textarea,select){box-sizing:border-box;width:100%;min-width:0;max-width:100%;min-height:44px;padding:10px 12px;border:1px solid var(--ll-border-strong);border-radius:8px;background:var(--ll-surface,#fff);color:var(--ll-text);font:inherit;font-size:16px;line-height:1.7}
.zhejiang-own-fields textarea{min-height:96px;resize:vertical;overflow-wrap:anywhere}
.zhejiang-own-fields :is(input,textarea,select,button):focus-visible{outline:3px solid var(--ll-primary);outline-offset:2px}
.zhejiang-own-fields [aria-invalid=true]{border-color:var(--ll-danger,#a82622)}
.zhejiang-list-item,.zhejiang-evidence-item{min-width:0;margin:16px 0;padding:0 0 16px;border:0;border-bottom:1px solid var(--ll-border)}
.zhejiang-list-item button,.zhejiang-evidence-item button{margin-top:12px}
.zhejiang-capacity{margin:8px 0 0;font-size:14px;line-height:1.7;overflow-wrap:anywhere}
.zhejiang-error{margin:8px 0 0;color:var(--ll-danger,#a82622);font-size:14px;line-height:1.7;overflow-wrap:anywhere}
@media(max-width:600px){.zhejiang-grid{grid-template-columns:minmax(0,1fr);gap:16px}.zhejiang-actions button{flex:1 1 160px;min-width:0}.zhejiang-list-item button,.zhejiang-evidence-item button{max-width:100%}}
</style>
