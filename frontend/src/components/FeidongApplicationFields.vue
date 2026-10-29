<template>
  <div class="feidong-application-fields">
    <p class="feidong-example-notice">默认内容全部是虚构示例，请逐项替换为自己的情况。也可以清空后填写；未填写的位置将留空。</p>
    <div class="region-actions feidong-example-actions">
      <button type="button" class="ll-button secondary" @click="replaceAll(createFeidongApplicationExample())">载入虚构示例</button>
      <button type="button" class="ll-button secondary" @click="replaceAll(createEmptyFeidongApplication())">清空填写内容</button>
    </div>

    <fieldset v-for="field in FEIDONG_PARTY_FIELDS" :key="field.key" class="feidong-party">
      <legend>{{ field.label }}</legend>
      <p :id="idFor(`${field.key}-hint`)" class="region-small">{{ field.hint }}</p>
      <div class="region-form-fields feidong-party-lines">
        <div v-for="index in [0, 1]" :key="index" class="feidong-line">
          <label :for="idFor(`${field.key}-${index}`)" class="regional-form-label">{{ field.label }}第{{ index + 1 }}行</label>
          <input
            :id="idFor(`${field.key}-${index}`)"
            :value="partyLine(field.key, index)"
            type="text"
            autocomplete="off"
            :aria-invalid="fieldError(`${field.key}.${index}`) ? 'true' : undefined"
            :aria-describedby="`${idFor(`${field.key}-hint`)} ${idFor(`${field.key}-${index}-capacity`)}${fieldError(`${field.key}.${index}`) ? ` ${idFor(`${field.key}-${index}-error`)}` : ''}`"
            @input="updateParty(field.key, index, $event.target.value)"
          >
          <p :id="idFor(`${field.key}-${index}-capacity`)" class="region-small feidong-capacity">{{ width(partyLine(field.key, index)) }} / {{ index === 0 ? 40 : 50 }} 显示单位；最多{{ index === 0 ? 20 : 25 }}个汉字。</p>
          <p v-if="fieldError(`${field.key}.${index}`)" :id="idFor(`${field.key}-${index}-error`)" class="feidong-error">{{ fieldError(`${field.key}.${index}`) }}</p>
        </div>
      </div>
      <p v-if="fieldError(field.key)" class="feidong-error">{{ fieldError(field.key) }}</p>
    </fieldset>

    <div class="feidong-body-field">
      <label :for="idFor('requests')" class="regional-form-label">请求事项</label>
      <p :id="idFor('requests-hint')" class="region-small">一项请求写一行，可写清具体要求和金额。折行后最多9行，首行最多22个汉字，之后每行最多28个汉字。</p>
      <textarea
        :id="idFor('requests')"
        :value="requestText"
        rows="5"
        :aria-invalid="fieldError('requests') ? 'true' : undefined"
        :aria-describedby="`${idFor('requests-hint')} ${idFor('requests-usage')}${fieldError('requests') ? ` ${idFor('requests-error')}` : ''}`"
        @input="updateField('requests', $event.target.value.split('\n'))"
      ></textarea>
      <p :id="idFor('requests-usage')" class="region-small feidong-capacity">折行后 {{ lineCount(requestText, 44) }} / 9 行。</p>
      <p v-if="fieldError('requests')" :id="idFor('requests-error')" class="feidong-error">{{ fieldError('requests') }}</p>
    </div>

    <div class="feidong-body-field">
      <label :for="idFor('facts')" class="regional-form-label">事实和理由</label>
      <p :id="idFor('facts-hint')" class="region-small">写清事情经过、证据和证据来源、证人姓名与住址等。每行最多28个汉字，折行后最多10行。</p>
      <textarea
        :id="idFor('facts')"
        :value="factsText"
        rows="6"
        :aria-invalid="fieldError('facts') ? 'true' : undefined"
        :aria-describedby="`${idFor('facts-hint')} ${idFor('facts-usage')}${fieldError('facts') ? ` ${idFor('facts-error')}` : ''}`"
        @input="updateField('facts', $event.target.value)"
      ></textarea>
      <p :id="idFor('facts-usage')" class="region-small feidong-capacity">折行后 {{ lineCount(factsText) }} / 10 行。</p>
      <p v-if="fieldError('facts')" :id="idFor('facts-error')" class="feidong-error">{{ fieldError('facts') }}</p>
    </div>

    <p class="region-small">汉字和全角字符计2个显示单位，英文字母、数字和普通空格计1个；首尾空白不计入容量。超出容量时请先调整内容，不会自动截断文字。</p>
    <p class="region-small">申请人签名、申请日期和附件份数留空，请打印后本人核对并手写。</p>
    <p v-if="fieldError('form')" class="feidong-error">{{ fieldError('form') }}</p>
    <p v-if="!validation.valid" class="feidong-error-summary" role="status" aria-live="polite">还有{{ validation.errors.length }}处内容需要调整，调整后才能生成。已填写的文字均保留。</p>
  </div>
</template>

<script setup>
import {computed, onMounted, useId, watch} from 'vue'
import {
  FEIDONG_PARTY_FIELDS, createFeidongApplicationExample, createEmptyFeidongApplication,
  feidongFieldWidth, wrapFeidongText, validateFeidongApplication, feidongApplicationPayload,
} from '@/data/feidongApplicationFields'

const props=defineProps({modelValue:{type:Object,default:undefined}})
const emit=defineEmits(['update:modelValue','validation'])
const initialExample=createFeidongApplicationExample()
const value=computed(()=>props.modelValue===undefined?initialExample:props.modelValue)
const prefix=`feidong-${useId()}`
const idFor=part=>`${prefix}-${part}`
const validation=computed(()=>validateFeidongApplication(value.value))
const fieldError=field=>validation.value.errors.find(error=>error.field===field)?.message||''
const partyLine=(key,index)=>typeof value.value?.[key]?.[index]==='string'?value.value[key][index]:''
const requestText=computed(()=>Array.isArray(value.value?.requests)?value.value.requests.filter(request=>typeof request==='string').join('\n'):'')
const factsText=computed(()=>typeof value.value?.facts==='string'?value.value.facts:'')
const width=text=>{try{return feidongFieldWidth(text)}catch{return '—'}}
const lineCount=(text,first=56)=>{try{return wrapFeidongText(text,first,56).length}catch{return '—'}}
const updateField=(key,next)=>emit('update:modelValue',{...value.value,[key]:next})
function updateParty(key,index,text){
  const current=Array.isArray(value.value?.[key])?[...value.value[key]]:['','']
  // Preserve unexpected extra rows for validation rather than quietly deleting them.
  while(current.length<=index)current.push('')
  current[index]=text
  updateField(key,current)
}
const replaceAll=next=>emit('update:modelValue',next)
watch(validation,result=>emit('validation',result),{immediate:true,deep:true})
onMounted(()=>{if(props.modelValue===undefined)emit('update:modelValue',createFeidongApplicationExample())})
defineExpose({validate:()=>validateFeidongApplication(value.value),getPayload:()=>feidongApplicationPayload(value.value)})
</script>

<style scoped>
.feidong-application-fields{min-width:0;max-width:100%}
.feidong-example-notice{margin:0 0 16px;line-height:1.8;color:var(--ll-secondary)}
.feidong-example-actions{margin-bottom:24px}
.feidong-example-actions button{min-height:44px;white-space:normal}
.feidong-party{min-width:0;margin:0 0 24px;padding:0 0 24px;border:0;border-bottom:1px solid var(--ll-border)}
.feidong-party legend{float:none;width:auto;padding:0;font-size:18px;font-weight:650;line-height:1.5}
.feidong-party-lines{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px;margin-top:16px}
.feidong-line{min-width:0}
.regional-form-label{display:block;margin-bottom:8px;font-weight:600;line-height:1.6}
.feidong-application-fields :is(input,textarea){box-sizing:border-box;width:100%;min-width:0;max-width:100%;min-height:44px;padding:10px 12px;border:1px solid var(--ll-border-strong);border-radius:8px;background:var(--ll-surface,#fff);color:var(--ll-text);font:inherit;font-size:16px;line-height:1.7}
.feidong-application-fields textarea{min-height:130px;resize:vertical;overflow-wrap:anywhere}
.feidong-application-fields :is(input,textarea):focus-visible{outline:3px solid var(--ll-primary);outline-offset:2px}
.feidong-application-fields [aria-invalid=true]{border-color:var(--ll-danger,#a82622)}
.feidong-body-field{margin-top:24px}
.feidong-body-field .region-small{margin:0 0 10px}
.feidong-capacity{margin:8px 0 0!important;font-size:14px;overflow-wrap:anywhere}
.feidong-error,.feidong-error-summary{margin:8px 0 0;color:var(--ll-danger,#a82622);font-size:14px;line-height:1.7;overflow-wrap:anywhere}
.feidong-error-summary{padding:12px;border-left:3px solid var(--ll-danger,#a82622)}
@media(max-width:600px){.feidong-party-lines{grid-template-columns:minmax(0,1fr);gap:16px}.feidong-example-actions button{flex:1 1 160px;min-width:0}}
</style>
