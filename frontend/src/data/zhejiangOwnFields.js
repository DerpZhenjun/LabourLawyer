/** Exact ZJD worker application / independent evidence contract. No source samples. */
export const ZHEJIANG_OWN_ADAPTER='zhejiang_own_worker_oct29d_v1'
export const ZHEJIANG_OWN_LIMITS=Object.freeze({ordinary:300,factsReason:12000,requests:4,request:1200,
  evidenceList:40,evidence_name:300,evidence_source:300,evidence_pageCount:300,evidence_purpose:1200,copyCount_min:1,copyCount_max:30})
export const ZHEJIANG_OWN_FIELD_GROUPS={
  application:[
    {label:'申请人信息',fields:[
      {key:'applicantName',label:'申请人姓名'},{key:'birthDate',label:'出生日期',hint:'可留空，例如1991-05-09。'},
      {key:'gender',label:'性别'},{key:'nationality',label:'民族'},
      {key:'idNumber',label:'身份证号码'},{key:'phone',label:'联系电话',inputmode:'tel'},
      {key:'householdType',label:'户口类型',hint:'不确定可以留空，打印后本人核对。'},
      {key:'idAddress',label:'申请人住所'},
    ]},
    {label:'被申请人信息',fields:[
      {key:'respondentName',label:'被申请人名称'},{key:'socialCreditCode',label:'统一社会信用代码'},
      {key:'registeredAddress',label:'被申请人住所'},{key:'mailingAddress',label:'被申请人通讯地址'},
      {key:'workAddress',label:'你的实际工作地址'},{key:'legalRepName',label:'法定代表人或主要负责人姓名'},
      {key:'legalRepPhone',label:'法定代表人或主要负责人电话',inputmode:'tel'},{key:'legalRepPosition',label:'法定代表人或主要负责人职务'},
      {key:'companyContact',label:'单位联系人姓名'},{key:'companyContactPhone',label:'单位联系人电话',inputmode:'tel'},
    ]},
    {label:'提交信息',fields:[
      {key:'committeeName',label:'提交的仲裁委员会',hint:'请核对受理机关，未确定时可以留空。'},
      {key:'applicationDate',label:'申请日期',hint:'可以留空，打印后填写。'},
      {key:'copyCount',label:'申请书副本份数',inputmode:'numeric',hint:'可以留空；填写时须为1至30的整数，请按受理机关要求核对。'},
    ]},
  ],
  evidence:[{label:'证据清单提交信息',fields:[
    {key:'committeeName',label:'提交的仲裁委员会',hint:'请核对受理机关，未确定时可以留空。'},
    {key:'caseNumber',label:'案号',hint:'尚未取得案号时可以留空。'},
    {key:'copyCount',label:'证据清单份数',inputmode:'numeric',hint:'可以留空；填写时须为1至30的整数，请按受理机关要求核对。'},
    {key:'submitDate',label:'提交日期',hint:'可以留空，打印后填写。'},
  ]}],
}
export const ZHEJIANG_OWN_EVIDENCE_FIELDS=[
  {key:'name',label:'证据名称',limit:300},{key:'pageCount',label:'页数',limit:300},
  {key:'source',label:'证据来源',limit:300},{key:'purpose',label:'证明内容',limit:1200},
]
// The source repeats 外省非农业户口. Neither duplicate can be safely auto-selected.
export const ZHEJIANG_HOUSEHOLD_CHOICES=Object.freeze(['本省非农业户口','本省农业户口','港澳台人员','外籍人员'])
export const ZHEJIANG_OWN_DATA_FIELDS=Object.freeze({
  application:Object.freeze([...ZHEJIANG_OWN_FIELD_GROUPS.application.flatMap(g=>g.fields.map(f=>f.key)),'factsReason','requests']),
  evidence:Object.freeze(['committeeName','caseNumber','copyCount','submitDate','evidenceList']),
  evidence_item:Object.freeze(ZHEJIANG_OWN_EVIDENCE_FIELDS.map(f=>f.key)),
})
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v)&&[Object.prototype,null].includes(Object.getPrototypeOf(v))
const knownKind=kind=>['application','evidence'].includes(kind)
const listKeysValid=v=>Reflect.ownKeys(v).every(k=>k==='length'||(typeof k==='string'&&/^(0|[1-9]\d*)$/.test(k)&&Number.isSafeInteger(Number(k))&&Number(k)<v.length))
const xmlInvalid=/[\u0000-\u0008\u000b\u000c\u000e-\u001f\ufffe\uffff]/u
const usableText=v=>typeof v==='string'&&!xmlInvalid.test(v)&&!Array.from(v).some(c=>{const point=c.codePointAt(0);return point>=0xd800&&point<=0xdfff})
export const zhejiangOwnCharacterCount=v=>Array.from(typeof v==='string'?v:String(v??'')).length
export const zhejiangOwnDraftIsObject=object
export function zhejiangOwnCopyObject(value){return Object.fromEntries(Reflect.ownKeys(value).map(key=>[key,value[key]]))}
export function zhejiangOwnCopyList(value){
  const next=new Array(value.length)
  for(const key of Reflect.ownKeys(value))if(key!=='length')Object.defineProperty(next,key,{value:value[key],writable:true,enumerable:true,configurable:true})
  return next
}
export function createEmptyZhejiangOwn(kind='application'){
  if(!knownKind(kind))throw new Error('请选择申请书或证据清单。')
  const ordinary=Object.fromEntries(ZHEJIANG_OWN_FIELD_GROUPS[kind].flatMap(g=>g.fields.map(f=>[f.key,''])))
  return kind==='application'?{...ordinary,factsReason:'',requests:['']}:{...ordinary,evidenceList:[{name:'',pageCount:'',source:'',purpose:''}]}
}
export function createZhejiangOwnExample(kind='application'){
  const empty=createEmptyZhejiangOwn(kind)
  if(kind==='evidence')return{...empty,evidenceList:[{name:'虚构劳动合同',pageCount:'3',source:'虚构示例，由申请人保存',purpose:'虚构示例：证明双方劳动关系及约定工资。'}]}
  return{...empty,applicantName:'陈虚构',respondentName:'虚构青禾有限公司',gender:'女',nationality:'汉族',
    idAddress:'虚构示例路一号',registeredAddress:'虚构示例路二号',workAddress:'虚构示例路二号',
    requests:['请求支付虚构拖欠工资3000元。'],
    factsReason:'以下全部为软件演示的虚构情况。陈虚构在虚构青禾有限公司从事示例工作，双方约定月工资3000元。虚构单位尚未支付一个月工资，双方协商未果，故提出上述请求。'}
}
export function validateZhejiangOwn(value,kind='application'){
  const errors=[],add=(field,label,message)=>errors.push({field,label,message})
  if(!knownKind(kind)){add('form','文书类型','请选择申请书或证据清单。');return{valid:false,errors}}
  if(!object(value)){add('form','填写内容','填写内容格式不正确，请清空本表后重新填写。');return{valid:false,errors}}
  const allowed=new Set(ZHEJIANG_OWN_DATA_FIELDS[kind])
  if(Reflect.ownKeys(value).some(k=>typeof k!=='string'||!allowed.has(k)))add('form','填写内容','含有本表不支持的内容，可能来自旧草稿。请清空后重新填写；不会自动丢弃或发送这些内容。')
  const check=(v,key,label,limit)=>{
    if(!usableText(v)){add(key,label,`${label}请填写普通文字，不得含有无法保存的字符。`);return}
    if(zhejiangOwnCharacterCount(v)>limit)add(key,label,`${label}最多${limit}个字符（含空格和换行），请调整后再生成；文字会完整保留。`)
  }
  for(const f of ZHEJIANG_OWN_FIELD_GROUPS[kind].flatMap(g=>g.fields)){
    if(!Object.hasOwn(value,f.key))continue
    const v=value[f.key]
    if(f.key==='copyCount'){
      const valid=v===''||v===null||(typeof v==='number'&&Number.isInteger(v)&&v>=1&&v<=30)||(typeof v==='string'&&/^[0-9]+$/.test(v)&&Number(v)>=1&&Number(v)<=30)
      if(!valid)add(f.key,f.label,`${f.label}请留空，或填写1至30的整数。`)
    }else check(v,f.key,f.label,ZHEJIANG_OWN_LIMITS.ordinary)
  }
  if(kind==='application'){
    if(Object.hasOwn(value,'factsReason'))check(value.factsReason,'factsReason','事实与理由',ZHEJIANG_OWN_LIMITS.factsReason)
    if(value.householdType&& !ZHEJIANG_HOUSEHOLD_CHOICES.includes(value.householdType))add('householdType','户口类型','原件“外省非农业户口”出现两次，不能自动判断应勾哪项。请留空后在纸面核对；其他内容请从本表选项中选择。')
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
        if(!object(item)){add(prefix,label,`${label}须分别填写名称、页数、来源和证明内容。`);continue}
        if(Reflect.ownKeys(item).some(k=>typeof k!=='string'||!ZHEJIANG_OWN_DATA_FIELDS.evidence_item.includes(k)))add(`${prefix}.form`,label,`${label}含有本表不支持的栏目，请清空后重新填写。`)
        for(const f of ZHEJIANG_OWN_EVIDENCE_FIELDS)if(Object.hasOwn(item,f.key))check(item[f.key],`${prefix}.${f.key}`,`${label}的${f.label}`,f.limit)
      }
    }
  }
  return{valid:errors.length===0,errors}
}
export function zhejiangOwnPayload(value,kind='application'){
  const result=validateZhejiangOwn(value,kind)
  if(!result.valid){const error=new Error(result.errors[0].message);error.fieldErrors=result.errors;throw error}
  return Object.fromEntries(Reflect.ownKeys(value).map(key=>[key,key==='requests'?[...value[key]]:key==='evidenceList'?value[key].map(zhejiangOwnCopyObject):value[key]]))
}
