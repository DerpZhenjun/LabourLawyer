/** Display synonymous official headings from this guide only; never infer rules. */
const aliases={'必须到现场原因':['必须到现场原因','必需现场办理原因','必须到现场办理说明'],'咨询方式':['咨询方式','咨询服务','咨询电话'],'到办事现场次数':['到办事现场次数','到现场次数']}
export function guideField(guide,name){
  for(const key of aliases[name]||[name]){
    const value=guide?.fields?.[key]?.raw_value
    if(value!==undefined&&value!==null&&String(value).trim())return String(value)
  }
  return '待核实'
}
export function visitCountLabel(guide){
  const value=guideField(guide,'到办事现场次数')
  return value==='待核实'||value.includes('次')?value:value+' 次'
}
export function originalCopyLabel(material){
  return material.original_copy||(/原件|复印件/.test(material.material_type||'')?material.material_type:'原件/复印件待核实')
}
export function materialDetails(material){
  const result={...material.details}
  for(const [key,label] of [['instructions','填写与份数说明'],['submission_method','提交方式'],['source_channel','材料从哪里取得'],['acceptance_standard','官网受理说明']]){
    if(material[key]!==undefined&&material[key]!==null&&material[key]!==''&&result[label]===undefined)result[label]=material[key]
  }
  return result
}

export function hasGenerationKind(guide,kind){
  return !!guide?.templates?.some(t=>t.can_generate===true&&Array.isArray(t.document_types)&&t.document_types.includes(kind))
}
