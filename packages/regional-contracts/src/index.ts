/** Portable wire types and lossless validation. No framework, network or model dependencies. */
export type DocumentKind = 'application' | 'evidence'
export type GenerationMode = 'blank' | 'reference_adaptation'
export interface Region { province: string; city: string; district: string }
export interface FormContext extends Region {
  region_code: string; source_id: string; version: number; template_id: string
  kind: DocumentKind; mode: GenerationMode; adapter: string
}
export interface RegionalTemplate {
  id: string; can_generate?: boolean; document_types: DocumentKind[]
  adapter?: string; official_kind?: string; original_name?: string; sha256?: string
  [key: string]: unknown
}
export interface RegionalGuide extends Region {
  source_id: string | null; version?: number; region_code?: string; source_url?: string
  verification_status?: string; service_name?: string; authority?: string; message?: string
  templates: RegionalTemplate[]; materials: Record<string, unknown>[]
  fields: Record<string, unknown>; sections: Record<string, unknown>; channel: Record<string, unknown>
  [key: string]: unknown
}
export interface FieldSpec {
  key: string; label: string; type: 'text' | 'copies' | 'text_list' | 'object_list'
  maxLength?: number; maxItems?: number; min?: number; max?: number; nullable?: boolean
  integer?: boolean; allow_leading_zero?: boolean; format?: 'iso-date'; choices?: string[]
  fields?: FieldSpec[]
}
export interface LayoutRule {
  max_lines: number; line_widths?: number[]; no_newlines?: boolean
  first_width?: number; later_width?: number; join?: '\n'; trim?: boolean
}
export interface LayoutLimits {
  unicode_version: string; wide_ranges: [number, number][]; fields: Record<string, LayoutRule>
}
export interface FormPolicy {
  unknown_fields: 'reject'; invalid_xml: 'reject'; capacity_is_official_requirement: false
  trim_text?: boolean; text_controls?: 'xml' | 'newline_only'
  text_list_total_max_length?: Record<string, number>; layout_limits?: LayoutLimits
}
export type FormScalar = string | number | null
export type FormValue = FormScalar | string[] | Record<string, FormScalar>[]
export type FormData = Record<string, FormValue>
export interface FormContract {
  schema_version: 1; contract_id: string; context: FormContext
  fields: FieldSpec[]; defaults: FormData; policy: FormPolicy
}
export interface FieldError { field: string; label: string; message: string }
export interface Validation { valid: boolean; errors: FieldError[] }
export interface RegionalGenerateRequest extends Region {
  source_id: string; version: number; template_id: string; kind: DocumentKind
  mode: GenerationMode; contract_id: string; data: FormData
}
export const isPlainRecord = (value: unknown): value is Record<string, unknown> =>
  value !== null && typeof value === 'object' && !Array.isArray(value) &&
  [Object.prototype, null].includes(Object.getPrototypeOf(value))
const own = (o: object, key: PropertyKey) => Object.prototype.hasOwnProperty.call(o, key)
const nonempty = (v: unknown): v is string => typeof v === 'string' && v.length > 0
const positive = (v: unknown): v is number => typeof v === 'number' && Number.isSafeInteger(v) && v > 0
// Python str.strip semantics used by the fixed-line filler; FEFF is content.
const pythonStrip = (v: string) => v.replace(/^[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+|[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+$/gu, '')
const textLength = (v: string) => Array.from(v).length
const plainText = (v: unknown): v is string => typeof v === 'string' && !Array.from(v).some(c => {
  const n=c.codePointAt(0) ?? 0
  return !(n===9 || n===10 || n===13 || (n>=0x20 && n<=0xd7ff) || (n>=0xe000 && n<=0xfffd) || (n>=0x10000 && n<=0x10ffff))
})
const listShape = (v: unknown[]): boolean => Reflect.ownKeys(v).every(k =>
  k==='length' || (typeof k==='string' && /^(0|[1-9]\d*)$/.test(k) && Number(k)<v.length)) &&
  Array.from({length:v.length},(_,i)=>own(v,i)).every(Boolean)
const kind = (v: unknown): v is DocumentKind => v==='application' || v==='evidence'
const problem = (): never => { throw new Error('地区或表单资料格式不正确，请重新选择地区核对来源。') }
const clone = (v: unknown): unknown => Array.isArray(v) ? v.map(clone) : isPlainRecord(v) ?
  Object.fromEntries(Reflect.ownKeys(v).map(k=>[k,clone(Reflect.get(v,k))])) : v

export function regionQuery(region: Region): string {
  return (['province','city','district'] as const).map(k=>`${k}=${encodeURIComponent(region[k] || '')}`).join('&')
}
export function parseApiError(value: unknown, fallback='无法完成操作，请重新核对内容和服务连接。'): string {
  return isPlainRecord(value) && typeof value.detail==='string' ? value.detail : fallback
}
export const fieldErrors = parseApiError

/** Network JSON is untrusted; never assert a previous district into the new result. */
export function assertRegionalGuide(value: unknown, expected: Region): RegionalGuide {
  if (!isPlainRecord(value)) return problem()
  for (const k of ['province','city','district'] as const) if (value[k]!==expected[k]) return problem()
  if (!(value.source_id===null || nonempty(value.source_id)) || !Array.isArray(value.templates) ||
      !Array.isArray(value.materials) || !value.materials.every(isPlainRecord) ||
      !isPlainRecord(value.fields) || !isPlainRecord(value.sections) || !isPlainRecord(value.channel)) return problem()
  if (value.source_id!==null && (!positive(value.version) || !nonempty(value.region_code))) return problem()
  for (const t of value.templates) {
    if (!isPlainRecord(t) || !nonempty(t.id) || (t.can_generate!==undefined && typeof t.can_generate!=='boolean') ||
        !Array.isArray(t.document_types) || !t.document_types.every(kind) ||
        (t.can_generate && (!value.source_id || !t.document_types.length))) return problem()
  }
  return value as unknown as RegionalGuide
}

function assertFields(value: unknown, nested=false): asserts value is FieldSpec[] {
  if (!Array.isArray(value) || value.length>120 || !listShape(value)) return problem()
  const keys=new Set<string>()
  for (const f of value) {
    if (!isPlainRecord(f) || !nonempty(f.key) || !/^[A-Za-z][A-Za-z0-9_]*$/.test(f.key) ||
        ['constructor','prototype','__proto__'].includes(f.key) || keys.has(f.key) ||
        !nonempty(f.label) || !['text','copies','text_list','object_list'].includes(String(f.type))) return problem()
    keys.add(f.key)
    if (nested && !['text','copies'].includes(String(f.type))) return problem()
    if (f.maxLength!==undefined && (!positive(f.maxLength) || f.maxLength>200000)) return problem()
    if (['text_list','object_list'].includes(String(f.type)) && (!positive(f.maxItems) || f.maxItems>1000)) return problem()
    if (f.type==='object_list') assertFields(f.fields,true)
    if (f.format!==undefined && f.format!=='iso-date') return problem()
    for(const name of ['min','max']) if(f[name]!==undefined && (typeof f[name]!=='number' || !Number.isFinite(f[name]))) return problem()
    for(const name of ['nullable','integer','allow_leading_zero']) if(f[name]!==undefined && typeof f[name]!=='boolean') return problem()
    if(f.choices!==undefined && (!Array.isArray(f.choices) || !f.choices.every(v=>typeof v==='string'))) return problem()
  }
}
function assertLayout(value: unknown): asserts value is LayoutLimits {
  if(!isPlainRecord(value) || !nonempty(value.unicode_version) || !Array.isArray(value.wide_ranges) || value.wide_ranges.length>4000 || !isPlainRecord(value.fields)) return problem()
  let end=-1
  for(const range of value.wide_ranges) {
    if(!Array.isArray(range) || range.length!==2 || !Number.isSafeInteger(range[0]) || !Number.isSafeInteger(range[1]) || range[0]<=end || range[1]<range[0] || range[1]>0x10ffff) return problem()
    end=range[1]
  }
  for(const r of Object.values(value.fields)) {
    if(!isPlainRecord(r) || !positive(r.max_lines) || r.max_lines>1000) return problem()
    if(r.line_widths!==undefined && (!Array.isArray(r.line_widths) || !r.line_widths.every(positive))) return problem()
    for(const n of ['first_width','later_width']) if(r[n]!==undefined && (!positive(r[n]) || r[n]>10000)) return problem()
    if(r.line_widths===undefined && (!positive(r.first_width) || !positive(r.later_width))) return problem()
  }
}
export function assertFormContract(value: unknown, expected: Partial<FormContext>): FormContract {
  if(!isPlainRecord(value) || value.schema_version!==1 || typeof value.contract_id!=='string' ||
      !/^[a-f0-9]{64}$/.test(value.contract_id) || !isPlainRecord(value.context) ||
      !isPlainRecord(value.defaults) || !isPlainRecord(value.policy)) return problem()
  const c=value.context,p=value.policy
  for(const key of ['province','city','district','region_code','source_id','template_id','adapter']) if(!nonempty(c[key])) return problem()
  if(!positive(c.version) || !kind(c.kind) || !['blank','reference_adaptation'].includes(String(c.mode))) return problem()
  for(const [key,v] of Object.entries(expected)) if(c[key]!==v) return problem()
  if(p.unknown_fields!=='reject' || p.invalid_xml!=='reject' || p.capacity_is_official_requirement!==false) return problem()
  if(p.text_controls!==undefined && !['xml','newline_only'].includes(String(p.text_controls))) return problem()
  if(p.layout_limits!==undefined) assertLayout(p.layout_limits)
  assertFields(value.fields)
  const contract=value as unknown as FormContract
  if(!validateForm(contract,value.defaults).valid) return problem()
  if(Object.keys(value.defaults).length!==contract.fields.length) return problem()
  return contract
}
const validDate = (v: string): boolean => {
  if(!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(v)) return false
  const [y=0,m=0,d=0]=v.split('-').map(Number),leap=y%4===0 && (y%100!==0 || y%400===0)
  return y>=1 && y<=9999 && m>=1 && m<=12 && d>=1 && d<=[31,leap?29:28,31,30,31,30,31,31,30,31,30,31][m-1]!
}
function displayWidth(text: string, ranges: [number,number][]): number {
  let width=0
  for(const c of text) {
    const point=c.codePointAt(0) ?? 0;let lo=0,hi=ranges.length-1,wide=false
    while(lo<=hi){const mid=(lo+hi)>>1;const r=ranges[mid]!;if(point<r[0])hi=mid-1;else if(point>r[1])lo=mid+1;else{wide=true;break}}
    width+=wide?2:1
  }
  return width
}
function layoutFits(raw: unknown, rule: LayoutRule, ranges: [number,number][]): boolean {
  if(rule.line_widths) {
    if(!Array.isArray(raw) || raw.length>rule.max_lines) return false
    return raw.every((v,i)=>typeof v==='string' && !(rule.no_newlines && v.includes('\n')) && displayWidth(rule.trim?pythonStrip(v):v,ranges)<=(rule.line_widths?.[i] ?? 0))
  }
  let text=Array.isArray(raw)?raw.join(rule.join ?? '\n'):typeof raw==='string'?raw:''
  if(rule.trim)text=pythonStrip(text)
  let lines=0,line='',capacity=rule.first_width ?? 56
  for(const c of text) {
    if(c==='\n'){lines++;line='';capacity=rule.later_width ?? 56}
    else if(displayWidth(line+c,ranges)>capacity){lines++;line=c;capacity=rule.later_width ?? 56}
    else line+=c
    if(lines>rule.max_lines)return false
  }
  return lines+(line?1:0)<=rule.max_lines
}
export function validateForm(contract: FormContract, value: unknown): Validation {
  const errors: FieldError[]=[],add=(field:string,label:string,message:string)=>errors.push({field,label,message})
  const checkText=(v:unknown,f:FieldSpec,path:string)=>{
    if(v===null && f.nullable)return
    if(!plainText(v) || (contract.policy.text_controls==='newline_only' && typeof v==='string' && /[\u0000-\u0009\u000b-\u001f]/.test(v))){add(path,f.label,'请填写普通文字，不能含有无法保存的字符。');return}
    if(f.maxLength!==undefined && textLength(v)>f.maxLength)add(path,f.label,`${f.label}最多${f.maxLength}字符；已有内容会保留，请调整后生成。`)
    if(f.format==='iso-date' && v!=='' && !validDate(v))add(path,f.label,'请留空，或填写有效的YYYY-MM-DD日期。')
    if(f.choices && v!=='' && !f.choices.includes(v))add(path,f.label,'请选择此表支持的选项，未确定时可以留空。')
  }
  const walk=(record:unknown,fields:FieldSpec[],prefix='')=>{
    if(!isPlainRecord(record)){add(prefix||'form','填写内容','填写内容格式不正确。');return}
    const allowed=new Set(fields.map(f=>f.key))
    if(Reflect.ownKeys(record).some(k=>typeof k!=='string' || !allowed.has(k)))add(prefix?`${prefix}.form`:'form','填写内容','含有本表不支持的内容；不会自动丢弃，请重新核对。')
    for(const f of fields) {
      if(!own(record,f.key))continue
      const v=record[f.key],path=prefix?`${prefix}.${f.key}`:f.key
      if(f.type==='text')checkText(v,f,path)
      else if(f.type==='copies') {
        if(v==='' || (v===null && f.nullable))continue
        if(f.integer) {
          const numeric=typeof v==='number'?v:typeof v==='string' && (f.allow_leading_zero?/^[0-9]+$/:/^[1-9][0-9]*$/).test(v)?Number(v):NaN
          if(!Number.isSafeInteger(numeric) || (f.min!==undefined && numeric<f.min) || (f.max!==undefined && numeric>f.max))add(path,f.label,'请留空或填写此表支持的整数份数。')
        } else if(typeof v==='number') {if(!Number.isFinite(v))add(path,f.label,'请填写有限数字或文字。')}
        else checkText(v,f,path)
      } else {
        if(!Array.isArray(v)){add(path,f.label,'请逐项填写列表。');continue}
        if(v.length>(f.maxItems ?? 40)){add(path,f.label,`${f.label}最多${f.maxItems ?? 40}项；已有内容会保留。`);continue}
        if(!listShape(v)){add(path,f.label,'列表包含空缺或额外内容，请重新核对。');continue}
        v.forEach((item,i)=>f.type==='text_list'?checkText(item,f,`${path}.${i}`):walk(item,f.fields ?? [],`${path}.${i}`))
      }
    }
  }
  walk(value,contract.fields)
  if(isPlainRecord(value)) {
    for(const [key,limit] of Object.entries(contract.policy.text_list_total_max_length ?? {})) {
      const list=value[key]
      if(Array.isArray(list) && list.every(v=>typeof v==='string') && textLength(list.join('\n'))>limit)add(key,key,`全部内容最多${limit}字符，请调整后生成。`)
    }
    const layout=contract.policy.layout_limits
    if(layout)for(const [key,rule] of Object.entries(layout.fields))if(own(value,key) && !layoutFits(value[key],rule,layout.wide_ranges))add(key,key,'超过此表固定版式容量，请缩短；内容不会自动裁剪。')
  }
  return {valid:errors.length===0,errors}
}
/** Known guide notices, display only; source and eligibility stay unchanged. */
export function plainGuideWarning(value: string): string {
  switch(value) {
    case "自身partial来源；官方版本未知；预约组织标签不是委员会自动填写授权。": return "已核对本地区公开办事资料；资料版本和仲裁委员会全称仍需向办理机构确认。"
    case "显示份数与按人数副本备注均保留，不自动推断法律提交份数。": return "材料份数和按人数准备副本的说明均按官网保留，请在提交前向办理机构确认所需份数。"
    case "非适配证据状态UNKNOWN，不声称官网不提供；示范或扫描说明不生成。": return "尚未完成填写核验的附件暂不用于生成，不代表官网没有提供相关表格。示例样表和材料说明仅供参考，不能当作空白表格填写。"
    default: return value
  }
}
export function createEmptyForm(contract: FormContract): FormData { return clone(contract.defaults) as FormData }
export function createExampleForm(contract: FormContract): FormData {
  const form=createEmptyForm(contract)
  const examples:Record<string,string>={applicantName:'陈虚构',respondentName:'虚构青禾有限公司',idAddress:'虚构示例路一号',registeredAddress:'虚构示例路二号',factsReason:'以下全部为软件演示的虚构情况。虚构单位拖欠示例工资3000元，双方协商未果，故提出上述请求。',facts:'虚构示例：虚构单位拖欠一个月工资3000元，双方协商未果。'}
  for(const f of contract.fields) {
    if(f.type==='text' && examples[f.key])form[f.key]=examples[f.key]!
    if(f.type==='text_list' && f.key==='requests')form[f.key]=['请求支付虚构拖欠工资3000元。']
    if(f.type==='text_list' && f.key==='applicant_lines')form[f.key]=['申请人：陈虚构（示例）']
    if(f.type==='text_list' && f.key==='respondent_lines')form[f.key]=['被申请人：虚构公司（示例）']
    if(f.type==='object_list') {
      const e:Record<string,FormScalar>={}
      const example:Record<string,string>={name:'虚构劳动合同',pageCount:'3',source:'虚构示例：本人保存',purpose:'虚构示例：说明双方劳动关系。',originalType:'复印件'}
      for(const field of f.fields ?? [])e[field.key]=example[field.key] ?? ''
      form[f.key]=[e]
    }
  }
  if(!validateForm(contract,form).valid) return createEmptyForm(contract)
  return form
}
export function buildGenerateRequest(contract: FormContract, form: unknown): RegionalGenerateRequest {
  const validation=validateForm(contract,form)
  if(!validation.valid)throw new Error(validation.errors[0]?.message ?? '请核对填写内容。')
  const c=contract.context
  return {province:c.province,city:c.city,district:c.district,source_id:c.source_id,version:c.version,template_id:c.template_id,kind:c.kind,mode:c.mode,contract_id:contract.contract_id,data:clone(form) as FormData}
}
