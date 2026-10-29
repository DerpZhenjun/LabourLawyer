/** Exact EJS own application / independent evidence schema. No source examples used. */
export const JIANGSU_OWN_ADAPTER='jiangsu_own_blank_oct29e_v1'
export const JIANGSU_OWN_LIMITS=Object.freeze({ordinary:300,factsReason:12000,requests:4,request:1200,
  evidenceList:40,evidence_name:300,evidence_source:300,evidence_originalType:300,evidence_pageCount:300,evidence_purpose:1200,copyCount_min:1,copyCount_max:30})
export const JIANGSU_OWN_FIELD_GROUPS={
  application:[
    {label:'申请人信息',fields:[
      {key:'applicantName',label:'申请人姓名'},{key:'birthDate',label:'出生日期',hint:'可留空；填写时使用有效的YYYY-MM-DD日期。'},
      {key:'gender',label:'性别'},{key:'idNumber',label:'公民身份号码'},
      {key:'idAddress',label:'申请人居住地址'},{key:'otherDocumentType',label:'其他证件类型'},
      {key:'otherDocumentNumber',label:'其他证件号码'},{key:'applicantMailingAddress',label:'申请人通讯地址'},
      {key:'phone',label:'申请人移动电话',inputmode:'tel'},
      {key:'acceptMediation',label:'是否接受调解',hint:'请按本人意愿填写；未确定时留空，不会默认选择。'},
      {key:'legalAid',label:'是否法律援助',hint:'请核对本人情况后填写；未确定时留空。'},
    ]},
    {label:'被申请人信息',fields:[
      {key:'respondentName',label:'被申请人名称'},{key:'respondentType',label:'被申请人性质'},
      {key:'registeredAddress',label:'被申请人注册地址（住所）'},{key:'socialCreditCode',label:'统一社会信用代码'},
      {key:'legalRepName',label:'法定代表人或主要负责人'},{key:'legalRepPosition',label:'法定代表人或主要负责人职务'},
      {key:'departmentHead',label:'劳动者所在部门负责人'},{key:'departmentHeadPosition',label:'劳动者所在部门负责人职务'},
      {key:'mailingAddress',label:'被申请人通讯地址'},{key:'companyContact',label:'单位联系人'},
      {key:'companyContactPhone',label:'单位联系人电话',inputmode:'tel'},
    ]},
    {label:'提交信息',fields:[
      {key:'committeeName',label:'提交的仲裁委员会',hint:'请核对受理机关，未确定时可以留空。'},
      {key:'applicationDate',label:'申请日期',hint:'可留空；填写时使用有效的YYYY-MM-DD日期。'},
      {key:'copyCount',label:'申请书副本份数',inputmode:'numeric',hint:'可留空；填写1至30的整数，不在数字前加0，请按受理机关要求核对。'},
      {key:'evidenceCopyCount',label:'申请书所附证据副本份数',inputmode:'numeric',hint:'可留空；填写1至30的整数，不在数字前加0。此栏目属于申请书。'},
    ]},
  ],
  evidence:[{label:'证据清单提交信息',fields:[
    {key:'committeeName',label:'提交的仲裁委员会',hint:'请核对受理机关，未确定时可以留空。'},
    {key:'caseNumber',label:'案号',hint:'尚未取得案号时可以留空。'},
    {key:'submitDate',label:'提交日期',hint:'可留空；填写时使用有效的YYYY-MM-DD日期。'},
  ]}],
}
export const JIANGSU_OWN_EVIDENCE_FIELDS=[
  {key:'name',label:'证据名称',limit:300},{key:'source',label:'证据来源',limit:300},
  {key:'purpose',label:'证明内容',limit:1200},{key:'originalType',label:'原件或复印件',limit:300},
  {key:'pageCount',label:'页数',limit:300},
]
export const JIANGSU_OWN_DATA_FIELDS=Object.freeze({
  application:Object.freeze([...JIANGSU_OWN_FIELD_GROUPS.application.flatMap(g=>g.fields.map(f=>f.key)),'factsReason','requests']),
  evidence:Object.freeze(['committeeName','caseNumber','submitDate','evidenceList']),
  evidence_item:Object.freeze(JIANGSU_OWN_EVIDENCE_FIELDS.map(f=>f.key)),
})
const validDate=value=>{
  if(!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(value))return false
  const [year,month,day]=value.split('-').map(Number)
  if(year<1||year>9999||month<1||month>12)return false
  const leap=year%4===0&&(year%100!==0||year%400===0)
  return day>=1&&day<=[31,leap?29:28,31,30,31,30,31,31,30,31,30,31][month-1]
}
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v)&&[Object.prototype,null].includes(Object.getPrototypeOf(v))
const knownKind=kind=>['application','evidence'].includes(kind)
const listKeysValid=v=>Reflect.ownKeys(v).every(k=>k==='length'||(typeof k==='string'&&/^(0|[1-9]\d*)$/.test(k)&&Number.isSafeInteger(Number(k))&&Number(k)<v.length))
const xmlInvalid=/[\u0000-\u0008\u000b\u000c\u000e-\u001f\ufffe\uffff]/u
const usableText=v=>typeof v==='string'&&!xmlInvalid.test(v)&&!Array.from(v).some(c=>{const point=c.codePointAt(0);return point>=0xd800&&point<=0xdfff})
export const jiangsuOwnCharacterCount=v=>Array.from(typeof v==='string'?v:String(v??'')).length
export const jiangsuOwnDraftIsObject=object
export function jiangsuOwnCopyObject(value){return Object.fromEntries(Reflect.ownKeys(value).map(key=>[key,value[key]]))}
export function jiangsuOwnCopyList(value){
  const next=new Array(value.length)
  for(const key of Reflect.ownKeys(value))if(key!=='length')Object.defineProperty(next,key,{value:value[key],writable:true,enumerable:true,configurable:true})
  return next
}
export function createEmptyJiangsuOwn(kind='application'){
  if(!knownKind(kind))throw new Error('请选择申请书或证据清单。')
  const ordinary=Object.fromEntries(JIANGSU_OWN_FIELD_GROUPS[kind].flatMap(g=>g.fields.map(f=>[f.key,''])))
  return kind==='application'?{...ordinary,factsReason:'',requests:['']}:{...ordinary,evidenceList:[{name:'',source:'',purpose:'',originalType:'',pageCount:''}]}
}
export function createJiangsuOwnExample(kind='application'){
  const empty=createEmptyJiangsuOwn(kind)
  if(kind==='evidence')return{...empty,evidenceList:[{name:'虚构劳动合同',source:'虚构示例，由申请人保存',purpose:'虚构示例：证明双方劳动关系及约定工资。',originalType:'虚构示例：复印件',pageCount:'3'}]}
  return{...empty,applicantName:'陈虚构',respondentName:'虚构青禾有限公司',gender:'女',
    idAddress:'虚构示例路一号',registeredAddress:'虚构示例路二号',
    requests:['请求支付虚构拖欠工资3000元。'],
    factsReason:'以下全部为软件演示的虚构情况。陈虚构在虚构青禾有限公司从事示例工作，双方约定月工资3000元。虚构单位尚未支付一个月工资，双方协商未果，故提出上述请求。'}
}
export function validateJiangsuOwn(value,kind='application'){
  const errors=[],add=(field,label,message)=>errors.push({field,label,message})
  if(!knownKind(kind)){add('form','文书类型','请选择申请书或证据清单。');return{valid:false,errors}}
  if(!object(value)){add('form','填写内容','填写内容格式不正确，请清空本表后重新填写。');return{valid:false,errors}}
  const allowed=new Set(JIANGSU_OWN_DATA_FIELDS[kind])
  if(Reflect.ownKeys(value).some(k=>typeof k!=='string'||!allowed.has(k)))add('form','填写内容','含有本表不支持的内容，可能来自旧草稿。请清空后重新填写；不会自动丢弃或发送这些内容。')
  const check=(v,key,label,limit)=>{
    if(!usableText(v)){add(key,label,`${label}请填写普通文字，不得含有无法保存的字符。`);return}
    if(jiangsuOwnCharacterCount(v)>limit)add(key,label,`${label}最多${limit}个字符（含空格和换行），请调整后再生成；文字会完整保留。`)
  }
  for(const f of JIANGSU_OWN_FIELD_GROUPS[kind].flatMap(g=>g.fields)){
    if(!Object.hasOwn(value,f.key))continue
    const v=value[f.key]
    if(['copyCount','evidenceCopyCount'].includes(f.key)){
      const valid=v===''||v===null||(typeof v==='number'&&Number.isInteger(v)&&v>=1&&v<=30)||(typeof v==='string'&&/^[1-9]\d*$/.test(v)&&Number(v)>=1&&Number(v)<=30)
      if(!valid)add(f.key,f.label,`${f.label}请留空，或填写1至30的整数。`)
    }else{
      check(v,f.key,f.label,JIANGSU_OWN_LIMITS.ordinary)
      if(['birthDate','applicationDate','submitDate'].includes(f.key)&&typeof v==='string'&&v!==''&&!validDate(v))add(f.key,f.label,`${f.label}请留空，或填写有效的YYYY-MM-DD日期（年份0001至9999）。`)
    }
  }
  if(kind==='application'){
    if(Object.hasOwn(value,'factsReason'))check(value.factsReason,'factsReason','事实与理由',JIANGSU_OWN_LIMITS.factsReason)
    if(Object.hasOwn(value,'requests')){
      if(!Array.isArray(value.requests))add('requests','请求事项','请求事项须逐项填写文字。')
      else{
        if(!listKeysValid(value.requests))add('requests','请求事项','请求列表含有本表不支持的内容，请清空后重新填写。')
        if(value.requests.length>4)add('requests','请求事项','最多填写4项请求，请调整后再生成；已有文字会完整保留。')
        for(let i=0;i<value.requests.length;i++)check(value.requests[i],`requests.${i}`,`第${i+1}项请求`,1200)
      }
    }
  }else if(Object.hasOwn(value,'evidenceList')){
    if(!Array.isArray(value.evidenceList))add('evidenceList','证据','证据须逐项填写。')
    else{
      if(!listKeysValid(value.evidenceList))add('evidenceList','证据','证据列表含有本表不支持的内容，请清空后重新填写。')
      if(value.evidenceList.length>40)add('evidenceList','证据','最多填写40项证据，请调整后再生成；已有文字会完整保留。')
      for(let i=0;i<value.evidenceList.length;i++){
        const item=value.evidenceList[i]
        const prefix=`evidenceList.${i}`,label=`第${i+1}项证据`
        if(!object(item)){add(prefix,label,`${label}须分别填写名称、来源、证明内容、原件或复印件和页数。`);continue}
        if(Reflect.ownKeys(item).some(k=>typeof k!=='string'||!JIANGSU_OWN_DATA_FIELDS.evidence_item.includes(k)))add(`${prefix}.form`,label,`${label}含有本表不支持的栏目，请清空后重新填写。`)
        for(const f of JIANGSU_OWN_EVIDENCE_FIELDS)if(Object.hasOwn(item,f.key))check(item[f.key],`${prefix}.${f.key}`,`${label}的${f.label}`,f.limit)
      }
    }
  }
  return{valid:errors.length===0,errors}
}
export function jiangsuOwnPayload(value,kind='application'){
  const result=validateJiangsuOwn(value,kind)
  if(!result.valid){const error=new Error(result.errors[0].message);error.fieldErrors=result.errors;throw error}
  return Object.fromEntries(Reflect.ownKeys(value).map(key=>[key,key==='requests'?[...value[key]]:key==='evidenceList'?value[key].map(jiangsuOwnCopyObject):value[key]]))
}
