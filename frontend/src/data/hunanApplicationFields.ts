import {ProvincialValidationError, type ProvincialValidation, type ProvincialFieldError} from '../../../packages/regional-contracts/src/provincial.ts'
export interface HunanField {key:string;label:string;hint?:string;inputmode?:'tel'|'numeric'|'text'}
export interface HunanEvidence {name:string;source:string;purpose:string}
export interface HunanApplicationForm extends Record<string,unknown> {requests:string[];factsReason:string;evidenceList:HunanEvidence[];copyCount?:string|number}
export interface HunanApplicationPayload extends Record<string,unknown> {requests?:string[];factsReason?:string;evidenceList?:Partial<HunanEvidence>[];copyCount?:string|number}
/** Exact input contract for the two bound Hunan worker application forms. */
export const HUNAN_LIMITS=Object.freeze({ordinary:160,requests:8,facts:1800,evidence:10,evidenceField:300})
export const HUNAN_FIELD_GROUPS:{label:string;fields:HunanField[]}[]=[
  {label:'申请人信息',fields:[
    {key:'applicantName',label:'申请人姓名'},{key:'gender',label:'性别'},
    {key:'birthDate',label:'出生日期',hint:'可留空；例如：1990-01-02'},
    {key:'occupation',label:'职业'},{key:'nationality',label:'民族'},
    {key:'idAddress',label:'住所'},{key:'postalCode',label:'住所邮编'},
    {key:'phone',label:'联系电话',inputmode:'tel'},{key:'workUnit',label:'工作单位'},
    {key:'workUnitPostalCode',label:'工作单位邮编'},{key:'workUnitPhone',label:'工作单位电话',inputmode:'tel'},
  ]},
  {label:'被申请人信息',fields:[
    {key:'respondentName',label:'被申请人名称'},{key:'registeredAddress',label:'被申请人住所'},
    {key:'respondentPostalCode',label:'被申请人邮编'},{key:'legalRepName',label:'法定代表人或主要负责人'},
    {key:'legalRepPosition',label:'法定代表人职务'},{key:'legalRepPhone',label:'法定代表人电话',inputmode:'tel'},
    {key:'hrContactName',label:'人力资源管理部门负责人'},{key:'hrContactPosition',label:'人力资源负责人职务'},
    {key:'hrContactPhone',label:'人力资源负责人电话',inputmode:'tel'},
  ]},
  {label:'第三人与提交信息',fields:[
    {key:'thirdParty',label:'第三人',hint:'没有第三人可留空。'},
    {key:'committeeName',label:'提交的仲裁委员会',hint:'请自行核对受理机关，未确定时可留空。'},
    {key:'applicationDate',label:'申请日期',hint:'可留空；例如：2026-10-29'},
    {key:'copyCount',label:'申请书副本份数',hint:'可留空，请按受理机关要求核对份数。',inputmode:'numeric'},
  ]},
]
export const HUNAN_EVIDENCE_FIELDS:HunanField[]=[{key:'name',label:'证据名称'},{key:'source',label:'证据来源'},{key:'purpose',label:'证明目的'}]
const ordinary=HUNAN_FIELD_GROUPS.flatMap(group=>group.fields)
const allowed=new Set([...ordinary.map(field=>field.key),'requests','factsReason','evidenceList'])
const evidenceKeys=new Set(HUNAN_EVIDENCE_FIELDS.map(field=>field.key))
const object=(value:unknown):value is Record<string,unknown>=>value!==null&&typeof value==='object'&&!Array.isArray(value)&&[Object.prototype,null].includes(Object.getPrototypeOf(value))
const listKeysValid=(value:unknown[])=>Reflect.ownKeys(value).every(key=>key==='length'||(
  typeof key==='string'&&/^(0|[1-9]\d*)$/.test(key)&&Number.isSafeInteger(Number(key))&&Number(key)<value.length
))
const invalidXml=/[\u0000-\u0008\u000b\u000c\u000e-\u001f\ufffe\uffff]/u
const usableText=(value:unknown):value is string=>typeof value==='string'&&!invalidXml.test(value)&&!Array.from(value).some(char=>{
  const point=char.codePointAt(0) ?? 0;return point>=0xd800&&point<=0xdfff
})
export const hunanCharacterCount=(value:unknown)=>Array.from(typeof value==='string'?value:String(value??'')).length
export function createEmptyHunanApplication():HunanApplicationForm{
  return {...Object.fromEntries(ordinary.map(field=>[field.key,''])),requests:[''],factsReason:'',evidenceList:[{name:'',source:'',purpose:''}]}
}
export function createHunanApplicationExample():HunanApplicationForm{
  return {...createEmptyHunanApplication(),applicantName:'林虚构',gender:'女',birthDate:'1990-01-02',occupation:'虚构示例文员',nationality:'汉族',
    idAddress:'虚构示例路1号',workUnit:'虚构星禾有限公司',respondentName:'虚构星禾有限公司',registeredAddress:'虚构示例路2号',
    legalRepName:'周虚构',legalRepPosition:'虚构示例经理',hrContactName:'李虚构',hrContactPosition:'虚构示例人事负责人',committeeName:'虚构示例仲裁委员会',
    requests:['请求支付虚构拖欠工资3000元。'],
    factsReason:'本申请全部为软件演示虚构内容。林虚构于2025年3月1日进入虚构星禾有限公司从事示例文员工作，约定月工资3000元。虚构单位尚未支付2025年4月的工资，双方协商未果。申请人依据虚构劳动合同及工资记录提出上述请求。',
    evidenceList:[{name:'虚构劳动合同复印件',source:'虚构示例，由申请人保存',purpose:'虚构示例：说明双方劳动关系及约定工资。'}],
  }
}
export function validateHunanApplication(value:unknown):ProvincialValidation{
  const errors:ProvincialFieldError[]=[],add=(field:string,label:string,message:string)=>errors.push({field,label,message})
  if(!object(value)){add('form','申请书内容','申请书内容必须是填写对象，请清空本表后重新填写。');return{valid:false,errors}}
  if(Reflect.ownKeys(value).some(key=>typeof key!=='string'||!allowed.has(key))){
    add('form','申请书内容','包含本表不支持的字段，可能来自旧草稿。请清空本表后重新填写，未支持的内容不会发送。')
  }
  const check=(text:unknown,field:string,label:string,limit?:number)=>{
    if(!usableText(text)){add(field,label,`${label}请填写普通文字，不得包含无法保存的控制字符。`);return}
    if(limit!==undefined&&hunanCharacterCount(text)>limit)add(field,label,`${label}最多${limit}个字符（含空格），请调整后再生成；文字不会自动截断。`)
  }
  for(const field of ordinary){
    if(!Object.hasOwn(value,field.key))continue
    const current=value[field.key]
    if(field.key==='copyCount'&&typeof current==='number'&&Number.isFinite(current))check(String(current),field.key,field.label,HUNAN_LIMITS.ordinary)
    else check(current,field.key,field.label,HUNAN_LIMITS.ordinary)
  }
  if(Object.hasOwn(value,'factsReason'))check(value.factsReason,'factsReason','事实与理由',HUNAN_LIMITS.facts)
  if(Object.hasOwn(value,'requests')){
    if(!Array.isArray(value.requests))add('requests','请求事项','请求事项必须按条填写文字。')
    else{
      if(!listKeysValid(value.requests))add('requests','请求事项','请求事项列表含有本表不支持的字段，请清空本表后重新填写。')
      if(value.requests.length>HUNAN_LIMITS.requests)add('requests','请求事项','请求事项最多8项，请调整后再生成；已有各项内容均保留。')
      for(let index=0;index<value.requests.length;index++)check(value.requests[index],`requests.${index}`,`第${index+1}项请求`)
    }
  }
  if(Object.hasOwn(value,'evidenceList')){
    if(!Array.isArray(value.evidenceList))add('evidenceList','附随证据','附随证据必须逐项填写。')
    else{
      if(!listKeysValid(value.evidenceList))add('evidenceList','附随证据','附随证据列表含有本表不支持的字段，请清空本表后重新填写。')
      if(value.evidenceList.length>HUNAN_LIMITS.evidence)add('evidenceList','附随证据','附随证据最多10项，请调整后再生成；已有各项内容均保留。')
      for(let index=0;index<value.evidenceList.length;index++){
        const item=value.evidenceList[index],prefix=`evidenceList.${index}`,label=`第${index+1}项附随证据`
        if(!object(item)){add(prefix,label,`${label}须分别填写名称、来源和证明目的。`);continue}
        if(Reflect.ownKeys(item).some(key=>typeof key!=='string'||!evidenceKeys.has(key)))add(`${prefix}.form`,label,`${label}包含本表不支持的字段，请清空本表后重新填写。`)
        for(const field of HUNAN_EVIDENCE_FIELDS)if(Object.hasOwn(item,field.key))check(item[field.key],`${prefix}.${field.key}`,`${label}的${field.label}`,HUNAN_LIMITS.evidenceField)
      }
    }
  }
  return{valid:errors.length===0,errors}
}
export function hunanApplicationPayload(value:unknown):HunanApplicationPayload{
  const result=validateHunanApplication(value)
  if(!result.valid||!object(value))throw new ProvincialValidationError(result.errors)
  // Validation rejects unknown keys first. Preserve all submitted characters,
  // whitespace, empty rows and numeric copy-count values without normalization.
  return Object.fromEntries(Reflect.ownKeys(value).map(key=>{
    if(typeof key!=='string')throw new ProvincialValidationError(result.errors)
    const current=value[key]
    return[key,key==='requests'?[...(current as string[])]:key==='evidenceList'?(current as Record<string,unknown>[]).map(item=>Object.fromEntries(Reflect.ownKeys(item).map(field=>{if(typeof field!=='string')throw new ProvincialValidationError(result.errors);return[field,item[field]]}))):current]
  }))
}
