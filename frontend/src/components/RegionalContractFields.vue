<template>
  <div class="contract-fields">
    <p class="region-small">栏目和填写容量来自当前地区表单。未确定的内容可以留空；文字不会自动裁剪。字数和项数为辅助填写容量，不作为官方受理条件。</p>
    <div class="region-actions">
      <button type="button" class="ll-button secondary" @click="replaceExample">载入虚构示例</button>
      <button type="button" class="ll-button secondary" @click="replaceEmpty">清空填写内容</button>
    </div>
    <section v-for="field in contract.fields" :key="field.key" class="region-panel contract-group">
      <template v-if="field.type === 'text' || field.type === 'copies'">
        <label :for="idFor(field.key)" class="regional-form-label">{{ field.label }}</label>
        <select v-if="field.choices" :id="idFor(field.key)" :value="display(value?.[field.key])" :disabled="!shapeValid"
          :aria-invalid="invalid(field.key)" :aria-describedby="description(field.key,field.key)" @change="updateField(field.key,eventValue($event))">
          <option value="">留空，稍后核对</option>
          <option v-for="choice in field.choices" :key="choice" :value="choice">{{ choice }}</option>
          <option v-if="display(value?.[field.key]) && !field.choices.includes(display(value?.[field.key]))" :value="display(value?.[field.key])">{{ display(value?.[field.key]) }}（请核对）</option>
        </select>
        <textarea v-else-if="(field.maxLength ?? 0) > 300" :id="idFor(field.key)" :value="display(value?.[field.key])" rows="5" :disabled="!shapeValid"
          :aria-invalid="invalid(field.key)" :aria-describedby="description(field.key,field.key)" @input="updateField(field.key,eventValue($event))"></textarea>
        <input v-else :id="idFor(field.key)" :value="display(value?.[field.key])" type="text" autocomplete="off"
          :inputmode="field.type==='copies' && field.integer ? 'numeric':'text'" :disabled="!shapeValid"
          :aria-invalid="invalid(field.key)" :aria-describedby="description(field.key,field.key)" @input="updateField(field.key,eventValue($event))">
        <p :id="idFor(`${field.key}-hint`)" class="region-small">{{ hint(field,value?.[field.key]) }}</p>
      </template>
      <fieldset v-else :aria-describedby="description(field.key,field.key)">
        <legend>{{ field.label }}</legend>
        <p :id="idFor(`${field.key}-hint`)" class="region-small">逐项填写；{{ listFor(field).length }} / {{ field.maxItems }} 项。已有内容会完整保留。</p>
        <fieldset v-for="(item,index) in listFor(field)" :key="index" class="contract-item" :aria-describedby="rowDescription(field.key,index)">
          <legend>第{{ index + 1 }}项{{ field.label }}</legend>
          <template v-if="field.type==='text_list'">
            <label :for="idFor(`${field.key}.${index}`)" class="regional-form-label">第{{ index + 1 }}项{{ field.label }}</label>
            <textarea :id="idFor(`${field.key}.${index}`)" :value="display(item)" rows="3" :disabled="!shapeValid || !listValid(field)"
              :aria-invalid="invalid(`${field.key}.${index}`)" :aria-describedby="description(`${field.key}.${index}`,field.key)"
              @input="updateListText(field,index,eventValue($event))"></textarea>
            <p class="region-small">{{ hint(field,item) }}</p>
          </template>
          <div v-else class="region-form-fields">
            <div v-for="column in field.fields" :key="column.key">
              <label :for="idFor(`${field.key}.${index}.${column.key}`)" class="regional-form-label">{{ column.label }}</label>
              <select v-if="column.choices" :id="idFor(`${field.key}.${index}.${column.key}`)" :value="display(itemValue(item,column.key))"
                :disabled="!shapeValid || !listValid(field) || !isPlainRecord(item)" :aria-invalid="invalid(`${field.key}.${index}.${column.key}`)"
                :aria-describedby="description(`${field.key}.${index}.${column.key}`,field.key)" @change="updateListObject(field,index,column.key,eventValue($event))">
                <option value="">留空，稍后核对</option>
                <option v-for="choice in column.choices" :key="choice" :value="choice">{{ choice }}</option>
                <option v-if="display(itemValue(item,column.key)) && !column.choices.includes(display(itemValue(item,column.key)))" :value="display(itemValue(item,column.key))">{{ display(itemValue(item,column.key)) }}（请核对）</option>
              </select>
              <textarea v-else :id="idFor(`${field.key}.${index}.${column.key}`)" :value="display(itemValue(item,column.key))" rows="2"
                :disabled="!shapeValid || !listValid(field) || !isPlainRecord(item)" :aria-invalid="invalid(`${field.key}.${index}.${column.key}`)"
                :aria-describedby="description(`${field.key}.${index}.${column.key}`,field.key)" @input="updateListObject(field,index,column.key,eventValue($event))"></textarea>
              <p class="region-small">{{ hint(column,itemValue(item,column.key)) }}</p>
              <p v-if="fieldError(`${field.key}.${index}.${column.key}`)" :id="idFor(`${field.key}.${index}.${column.key}-error`)" class="contract-error">{{ fieldError(`${field.key}.${index}.${column.key}`) }}</p>
            </div>
          </div>
          <p v-if="fieldError(`${field.key}.${index}`)" :id="idFor(`${field.key}.${index}-error`)" class="contract-error">{{ fieldError(`${field.key}.${index}`) }}</p>
          <p v-if="fieldError(`${field.key}.${index}.form`)" :id="idFor(`${field.key}.${index}.form-error`)" class="contract-error">{{ fieldError(`${field.key}.${index}.form`) }}</p>
          <button type="button" class="ll-button secondary" :aria-label="`删除第${index+1}项${field.label}`" :disabled="!shapeValid || !listValid(field) || listFor(field).length<=1" @click="removeItem(field,index)">删除此项</button>
        </fieldset>
        <button type="button" class="ll-button secondary" :disabled="!shapeValid || !listValid(field) || listFor(field).length >= (field.maxItems ?? 0)" @click="addItem(field)">添加{{ field.label }}</button>
      </fieldset>
      <p v-if="fieldError(field.key)" :id="idFor(`${field.key}-error`)" class="contract-error">{{ fieldError(field.key) }}</p>
    </section>
    <p v-if="fieldError('form')" :id="idFor('form-error')" class="contract-error">{{ fieldError('form') }}</p>
    <p v-if="!validation.valid" class="contract-error" role="status" aria-live="polite">还有{{ validation.errors.length }}处内容需要调整；原草稿全部保留，调整后才能生成。</p>
  </div>
</template>
<script setup lang="ts">
import {computed,useId} from 'vue'
import {createEmptyForm,createExampleForm,isPlainRecord,validateForm} from '../../../packages/regional-contracts/src/index.ts'
import type {FieldSpec,FormContract} from '../../../packages/regional-contracts/src/index.ts'

const props=defineProps<{contract: FormContract; modelValue: unknown}>()
const emit=defineEmits<{'update:modelValue':[value:unknown]}>()
const value=computed(()=>isPlainRecord(props.modelValue)?props.modelValue:undefined)
const shapeValid=computed(()=>isPlainRecord(props.modelValue))
const validation=computed(()=>validateForm(props.contract,props.modelValue))
const prefix=`regional-contract-${useId()}`,idFor=(key:string)=>`${prefix}-${key}`
const display=(raw:unknown):string=>typeof raw==='string'?raw:String(raw??'')
const itemValue=(item:unknown,key:string):unknown=>isPlainRecord(item)?item[key]:undefined
const fieldError=(key:string)=>validation.value.errors.find(error=>error.field===key)?.message??''
const invalid=(key:string)=>fieldError(key)?'true':undefined
const description=(key:string,group:string)=>`${idFor(`${group}-hint`)}${fieldError(key)?` ${idFor(`${key}-error`)}`:''}`
const rowDescription=(key:string,index:number)=>`${idFor(`${key}-hint`)}${fieldError(`${key}.${index}`)?` ${idFor(`${key}.${index}-error`)}`:''}${fieldError(`${key}.${index}.form`)?` ${idFor(`${key}.${index}.form-error`)}`:''}`
function hint(field:FieldSpec,current:unknown):string {
  const parts=['可以留空。']
  if(field.maxLength!==undefined)parts.push(`${Array.from(display(current)).length} / ${field.maxLength} 字符（含空格和换行）。`)
  if(field.type==='copies'&&field.integer)parts.push(`填写整数${field.min!==undefined?`，最少${field.min}`:''}${field.max!==undefined?`，最多${field.max}`:''}。`)
  if(field.format==='iso-date')parts.push('填写时使用有效的YYYY-MM-DD日期。')
  return parts.join('')
}
function eventValue(event:{target:unknown}):string {
  const target=event.target
  return target!==null&&typeof target==='object'&&'value' in target&&typeof target.value==='string'?target.value:''
}
function copyObject(raw:Record<string,unknown>):Record<PropertyKey,unknown> {return Object.fromEntries(Reflect.ownKeys(raw).map(key=>[key,Reflect.get(raw,key)]))}
function copyList(raw:readonly unknown[]):unknown[] {
  const next:unknown[]=new Array(raw.length)
  for(const key of Reflect.ownKeys(raw))if(key!=='length')Object.defineProperty(next,key,{value:Reflect.get(raw,key),enumerable:true,writable:true,configurable:true})
  return next
}
function emptyItem(field:FieldSpec):unknown {return field.type==='text_list'?'':Object.fromEntries((field.fields??[]).map(column=>[column.key,'']))}
function listFor(field:FieldSpec):unknown[] {
  const raw=value.value?.[field.key]
  if(Array.isArray(raw)){if(raw.length)return raw;const next=copyList(raw);next.push(emptyItem(field));return next}
  return[field.type==='text_list'&&typeof raw==='string'?raw:emptyItem(field)]
}
const listValid=(field:FieldSpec)=>value.value?.[field.key]===undefined||Array.isArray(value.value[field.key])
function updateField(key:string,next:unknown) {if(isPlainRecord(props.modelValue))emit('update:modelValue',{...copyObject(props.modelValue),[key]:next})}
function updateListText(field:FieldSpec,index:number,text:string) {if(!listValid(field))return;const next=copyList(listFor(field));next[index]=text;updateField(field.key,next)}
function updateListObject(field:FieldSpec,index:number,key:string,text:string) {
  if(!listValid(field))return
  const list=listFor(field),item=list[index]
  if(!isPlainRecord(item))return
  const next=copyList(list);next[index]={...copyObject(item),[key]:text};updateField(field.key,next)
}
function addItem(field:FieldSpec) {const list=listFor(field);if(listValid(field)&&list.length<(field.maxItems??0)){const next=copyList(list);next.push(emptyItem(field));updateField(field.key,next)}}
function removeItem(field:FieldSpec,index:number) {const list=listFor(field);if(listValid(field)&&list.length>1){const next=copyList(list);next.splice(index,1);updateField(field.key,next)}}
const replaceEmpty=()=>emit('update:modelValue',createEmptyForm(props.contract))
const replaceExample=()=>emit('update:modelValue',createExampleForm(props.contract))
defineExpose({validate:()=>validation.value})
</script>
<style scoped>
.contract-fields{min-width:0;max-width:100%}.contract-fields .region-actions{margin:16px 0 24px}
.contract-fields fieldset{min-width:0;margin:0;padding:0;border:0}.contract-fields legend{float:none;width:auto;font-size:18px;font-weight:650}
.contract-fields .contract-item{margin:20px 0;padding:16px 0;border-top:1px solid var(--ll-border)}
.regional-form-label{display:block;margin:0 0 8px;font-weight:600}.contract-fields :is(input,textarea,select){box-sizing:border-box;width:100%;min-width:0;min-height:44px;padding:10px 12px;font:inherit;font-size:16px;line-height:1.7;border:1px solid var(--ll-border-strong);border-radius:8px;color:var(--ll-text);background:var(--ll-surface,#fff)}
.contract-fields textarea{resize:vertical;overflow-wrap:anywhere}.contract-fields button{min-height:44px;white-space:normal}.contract-fields :focus-visible{outline:3px solid var(--ll-primary);outline-offset:3px}
.contract-error{color:var(--ll-danger,#9f2635);overflow-wrap:anywhere}.contract-fields [aria-invalid=true]{border-color:var(--ll-danger,#9f2635)}
@media(max-width:640px){.contract-fields .region-actions{display:grid;gap:12px}.contract-fields .region-actions button{width:100%}}
</style>
