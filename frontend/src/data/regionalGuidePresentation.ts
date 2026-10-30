/** Read only this guide's facts. JSON boundaries reject malformed data. */
import {isPlainRecord} from '../../../packages/regional-contracts/src/index.ts'
import type {RegionalGuide,RegionalTemplate,Region,DocumentKind} from '../../../packages/regional-contracts/src/index.ts'
const aliases:Record<string,string[]>={'必须到现场原因':['必须到现场原因','必需现场办理原因','必须到现场办理说明'],'咨询方式':['咨询方式','咨询服务','咨询电话'],'到办事现场次数':['到办事现场次数','到现场次数']}
export const publicError=(value:unknown,fallback='资料暂时无法读取，请稍后重试。'):string=>value instanceof Error?value.message:fallback
const invalid=():never=>{throw new Error('返回的公开资料格式不正确，请稍后重新核对。')}
export const record=(value:unknown):Record<string,unknown>=>isPlainRecord(value)?value:invalid()
export const text=(value:unknown,fallback=''):string=>value===undefined||value===null?fallback:typeof value==='string'?value:invalid()
const strings=(value:unknown):string[]=>value===undefined?[]:Array.isArray(value)&&value.every(v=>typeof v==='string')?value:invalid()
const rows=(value:unknown):Record<string,unknown>[]=>Array.isArray(value)?value.map(record):invalid()
const count=(value:unknown):number=>typeof value==='number'&&Number.isSafeInteger(value)&&value>=0?value:invalid()
const boolean=(value:unknown):boolean=>typeof value==='boolean'?value:invalid()
export function guideField(guide:unknown,name:string):string {
 const fields=isPlainRecord(guide)&&isPlainRecord(guide.fields)?guide.fields:undefined
 for(const key of aliases[name]??[name]){const entry=fields?.[key],value=isPlainRecord(entry)?entry.raw_value:undefined;if(value!==undefined&&value!==null&&String(value).trim())return String(value)}
 return '待核实'
}
export function visitCountLabel(guide:unknown):string {const value=guideField(guide,'到办事现场次数');return value==='待核实'||value.includes('次')?value:value+' 次'}
export function originalCopyLabel(material:unknown):string {const m=isPlainRecord(material)?material:{};return typeof m.original_copy==='string'&&m.original_copy?m.original_copy:/原件|复印件/.test(typeof m.material_type==='string'?m.material_type:'')?String(m.material_type):'原件/复印件待核实'}
export function materialDetails(material:unknown):Record<string,unknown> {
 const m=isPlainRecord(material)?material:{},result={...(isPlainRecord(m.details)?m.details:{})}
 for(const [key,label] of [['instructions','填写与份数说明'],['submission_method','提交方式'],['source_channel','材料从哪里取得'],['acceptance_standard','官网受理说明']] as const)if(m[key]!==undefined&&m[key]!==null&&m[key]!==''&&result[label]===undefined)result[label]=m[key]
 return result
}
export function hasGenerationKind(guide:unknown,kind:DocumentKind):boolean {return isPlainRecord(guide)&&Array.isArray(guide.templates)&&guide.templates.some(t=>isPlainRecord(t)&&t.can_generate===true&&Array.isArray(t.document_types)&&t.document_types.includes(kind))}
export interface TemplateDisplay extends RegionalTemplate {source_url:string;region_code:string;download_status:string;original_name:string;official_kind:string}
export interface MaterialDisplay extends Record<string,unknown> {id:string;name:string;official_badges:string[];required:string;format:string;copies:string|number;purpose:string}
export interface GuideDisplay extends RegionalGuide {templates:TemplateDisplay[];materials:MaterialDisplay[];warnings:string[];verified_at:string;official_version:string;channel:{online_status:string;entry_url:string;raw_value:string;entry_check:{status:string}}}
export function readGuideDisplay(value:RegionalGuide|null):GuideDisplay|null {
 if(value===null)return null
 const channel=record(value.channel)
 const templates=value.templates.map(t=>({...t,source_url:text(t.source_url),region_code:text(t.region_code),download_status:text(t.download_status),original_name:text(t.original_name),official_kind:text(t.official_kind)}))
 const materials=value.materials.map(m=>{const copies=m.copies===undefined||m.copies===null?'':typeof m.copies==='number'&&Number.isFinite(m.copies)?m.copies:text(m.copies);return{...m,id:text(m.id),name:text(m.name),official_badges:strings(m.official_badges),required:text(m.required),format:text(m.format),copies,purpose:text(m.purpose)}})
 return{...value,templates,materials,warnings:strings(value.warnings),verified_at:text(value.verified_at),official_version:text(value.official_version),channel:{...channel,online_status:text(channel.online_status),entry_url:text(channel.entry_url),raw_value:text(channel.raw_value),entry_check:{status:text(channel.entry_check===undefined?undefined:record(channel.entry_check).status)}}}
}
export interface DirectoryArea extends Region {region_code:string;source_id:string|null;can_generate:boolean}
export function readAreaRows(value:unknown,province:string,city=''):DirectoryArea[] {return rows(value).map(row=>{const rowProvince=text(row.province,province),rowCity=text(row.city,city);if(rowProvince!==province||(city&&rowCity!==city))return invalid();return{...row,province:rowProvince,city:rowCity,district:text(row.district),region_code:text(row.region_code),source_id:row.source_id===null||row.source_id===undefined?null:text(row.source_id),can_generate:row.can_generate===undefined?false:boolean(row.can_generate)}})}
export function readInventory(value:unknown):{items:DirectoryArea[];coverage:DirectoryArea[]} {const data=record(value),convert=(v:unknown)=>rows(v).map(row=>readAreaRows([row],text(row.province),text(row.city))[0]??invalid());return{items:convert(data.items),coverage:data.coverage===undefined?[]:convert(data.coverage)}}
export interface RolloutProvince {slug:string;name:string;targets_total:number;published_guides:number;generatable_localities:number;candidates:number;uncollected:number}
export interface RolloutStatus {directory_is_not_guide_coverage:true;published_guides:number;generatable_localities:number;unpublished_candidates:number;targets_total:number;provinces:RolloutProvince[]}
export function readRollout(value:unknown):RolloutStatus {const r=record(value);if(r.directory_is_not_guide_coverage!==true)return invalid();return{directory_is_not_guide_coverage:true,published_guides:count(r.published_guides),generatable_localities:count(r.generatable_localities),unpublished_candidates:count(r.unpublished_candidates),targets_total:count(r.targets_total),provinces:rows(r.provinces).map(p=>({slug:text(p.slug),name:text(p.name),targets_total:count(p.targets_total),published_guides:count(p.published_guides),generatable_localities:count(p.generatable_localities),candidates:count(p.candidates),uncollected:count(p.uncollected)}))}}
export interface ProvinceExperience {slug:string;service_kind:string;scope:string;state:string;captured_at:string;capital_confirmed:boolean;preferred_city:string;source_url:string;portal_url:string;steps:{title:string;text:string}[];materials:string[];notes:string[];templates:{material_name:string;text:string;kind:string;url:string}[]}
export function readExperience(value:unknown,slug:string):ProvinceExperience {const r=record(value);if(r.slug!==slug)return invalid();return{slug,service_kind:text(r.service_kind),scope:text(r.scope),state:text(r.state),captured_at:text(r.captured_at),capital_confirmed:r.capital_confirmed===undefined?false:boolean(r.capital_confirmed),preferred_city:text(r.preferred_city),source_url:text(r.source_url),portal_url:text(r.portal_url),steps:rows(r.steps).map(s=>({title:text(s.title),text:text(s.text)})),materials:strings(r.materials),notes:strings(r.notes),templates:r.templates===undefined?[]:rows(r.templates).map(t=>({material_name:text(t.material_name),text:text(t.text),kind:text(t.kind),url:text(t.url)}))}}
export interface VersionDisplay {content_hash:string;verified_at:string}
export const readVersions=(value:unknown):VersionDisplay[]=>rows(record(value).items).map(r=>({content_hash:text(r.content_hash),verified_at:text(r.verified_at)}))
export interface PublicEvent {id:string;province:string;district:string;type:string;reason:string;remediation:string;attempts:number;final_status:string;delivery_status:string;occurred_at:string;url:string;screenshot:string}
export interface CollectionRegion extends Region {region_id:string;province_name:string;authority:string;service_name:string;source_id:string;verified_at:string;source_url:string;templates:Record<string,unknown>[];channel:{raw_value:string;online_status:string}}
export interface CollectionReport {openclaw:{status:string;pending_count:number;attempted_at:string;total_count:number;acknowledged_count:number;exported_count:number;ai_reviewed_count:number};regions:CollectionRegion[];categories:Record<string,PublicEvent[]>;cross_province_checks:{source_id:string;limitation:string;raw_fields:Record<string,string>;material_requirement:string;verified_at:string;source_url:string}[]}
export function readCollectionReport(value:unknown):CollectionReport {
 const r=record(value),o=record(r.openclaw),categories=record(r.categories)
 const events=(v:unknown)=>rows(v).map(e=>({id:text(e.id),province:text(e.province),district:text(e.district),type:text(e.type),reason:text(e.reason),remediation:text(e.remediation),attempts:count(e.attempts),final_status:text(e.final_status),delivery_status:text(e.delivery_status),occurred_at:text(e.occurred_at),url:text(e.url),screenshot:text(e.screenshot)}))
 return{openclaw:{status:text(o.status),pending_count:count(o.pending_count),attempted_at:text(o.attempted_at),total_count:count(o.total_count),acknowledged_count:count(o.acknowledged_count),exported_count:count(o.exported_count),ai_reviewed_count:count(o.ai_reviewed_count)},categories:Object.fromEntries(Object.entries(categories).map(([key,value])=>[key,events(value)])),regions:rows(r.regions).map(g=>{const c=record(g.channel);return{province:text(g.province),city:text(g.city),district:text(g.district),region_id:text(g.region_id),province_name:text(g.province_name),authority:text(g.authority),service_name:text(g.service_name),source_id:text(g.source_id),verified_at:text(g.verified_at),source_url:text(g.source_url),templates:rows(g.templates),channel:{raw_value:text(c.raw_value),online_status:text(c.online_status)}}}),cross_province_checks:r.cross_province_checks===undefined?[]:rows(r.cross_province_checks).map(s=>({source_id:text(s.source_id),limitation:text(s.limitation),raw_fields:Object.fromEntries(Object.entries(record(s.raw_fields)).map(([k,v])=>[k,text(v)])),material_requirement:text(s.material_requirement),verified_at:text(s.verified_at),source_url:text(s.source_url)}))}
}
