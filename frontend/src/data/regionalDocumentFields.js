/** Editable fields must follow the selected form; hidden examples never submit. */
const ZHEJIANG='zhejiang_own_blank_v1'
export const isZhejiangBlankAdapter=adapter=>[ZHEJIANG,'zhejiang_shangcheng_own_blank_v1','zhejiang_ningbo_own_blank_oct29_v1'].includes(adapter)
export function regionalApplicationFields(base,isBlank,adapter){
  if(isZhejiangBlankAdapter(adapter))return base.filter(f=>!['currentAddress','applicantMailingAddress','applicantPostalCode'].includes(f.key))
  return isBlank?base.filter(f=>!['nationality','currentAddress','applicantPostalCode'].includes(f.key)).map(f=>f.key==='idAddress'?{...f,label:'居住地址'}:f):base
}
export function regionalExtraFields(jsFields,adapter){
  if(!isZhejiangBlankAdapter(adapter))return jsFields
  return [{key:'householdType',label:'户口类型（按原表填写）',max:50},
    {key:'socialCreditCode',label:'公司统一社会信用代码',max:50},
    {key:'mailingAddress',label:'公司的通讯地址'},
    {key:'workAddress',label:'你的实际工作地址'},
    {key:'legalRepPhone',label:'公司法定代表人联系电话',max:40},
    {key:'companyContact',label:'公司的联系人',max:80},
    {key:'copyCount',label:'申请书副本份数',type:'number',placeholder:'不确定可以留空'},
    {key:'applicationDate',label:'申请日期（也可以打印后填写）',type:'date'}]
}
export function applicationPayload(form,editableFields,requestText,additionalKeys=[]){
  const allowed=new Set([...editableFields.map(f=>f.key),'factsReason',...additionalKeys])
  return {...Object.fromEntries([...allowed].filter(k=>Object.hasOwn(form,k)).map(k=>[k,form[k]])),
    requests:requestText.split(/\r?\n/).map(s=>s.trim()).filter(Boolean)}
}
