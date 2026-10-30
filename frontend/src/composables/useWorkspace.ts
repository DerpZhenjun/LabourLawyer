import {computed,reactive,ref} from 'vue'
import {parseWorkspaceSnapshot} from '../../../packages/regional-contracts/src/workspace.ts'
import type {NewCaseInput,WorkspaceCase,WorkspaceMutationResult,WorkspaceSnapshot,WorkspaceStorage} from '../../../packages/regional-contracts/src/workspace.ts'
export type {NewCaseInput,WorkspaceCase,WorkspaceSnapshot,WorkspaceStorage} from '../../../packages/regional-contracts/src/workspace.ts'

const STORAGE_KEY='labourlawyer.workspace.v1'
const initialCases:WorkspaceCase[]=[
  {id:'PL-2026-018',title:'工资及加班费争议',client:'陈*',employer:'杭州某科技有限公司',region:'浙江·杭州',amount:42860,stage:'材料准备',risk:'warning',deadline:'2026-09-22',evidence:12,evidenceReady:75,updatedAt:'今天 09:42'},
  {id:'PL-2026-017',title:'违法解除劳动合同',client:'林*',employer:'深圳某贸易有限公司',region:'广东·深圳',amount:68200,stage:'待提交',risk:'danger',deadline:'2026-09-19',evidence:8,evidenceReady:88,updatedAt:'昨天 18:30'},
  {id:'PL-2026-015',title:'工伤待遇争议',client:'周*',employer:'宁波某制造有限公司',region:'浙江·宁波',amount:126500,stage:'审理中',risk:'progress',deadline:'2026-10-08',evidence:17,evidenceReady:94,updatedAt:'09-14 14:12'},
  {id:'PL-2026-011',title:'未签劳动合同双倍工资',client:'王*',employer:'广州某设计工作室',region:'广东·广州',amount:36500,stage:'已结案',risk:'done',deadline:'2026-08-28',evidence:10,evidenceReady:100,updatedAt:'09-02 11:08'},
]
export function createWorkspace(storage?:WorkspaceStorage){
  const storageIssue=ref('')
  let saved:WorkspaceSnapshot|null=null,protectedStorage=false
  try{
    const raw=storage?.getItem(STORAGE_KEY)
    if(raw!==null && raw!==undefined){const parsed:unknown=JSON.parse(raw);saved=parseWorkspaceSnapshot(parsed);if(!saved){protectedStorage=true;storageIssue.value='已保存的案件资料格式暂不支持，原资料已保留；当前显示示例，本页更改不会覆盖原资料。'}}
  }catch{protectedStorage=true;storageIssue.value='暂时无法读取已保存的案件资料，原资料未改动；当前显示示例，本页更改只保留在当前页面。'}
  const state=reactive<WorkspaceSnapshot>({...saved,cases:saved?.cases.length?saved.cases:initialCases.map(item=>({...item})),recentDocuments:saved?.recentDocuments??[]})
  const persist=():boolean=>{
    if(protectedStorage)return false
    try{if(!storage)throw new Error('Storage unavailable');storage.setItem(STORAGE_KEY,JSON.stringify(state));storageIssue.value='';return true}
    catch{storageIssue.value='本次更改仅保留在当前页面，暂未写入浏览器存储；原有存储未清除。';return false}
  }
  const addCase=(input:NewCaseInput):WorkspaceMutationResult=>{
    if(!input || typeof input!=='object' || ['title','client','employer','region','deadline'].some(key=>{
      const value=Reflect.get(input,key);return value!==undefined && typeof value!=='string'
    }))return{ok:false,error:'请核对案件填写内容。'}
    if(input.amount!==undefined && typeof input.amount!=='string' && typeof input.amount!=='number')return{ok:false,error:'争议金额须为有效的非负数字。'}
    const amount=Number(input.amount||0)
    if(!Number.isFinite(amount) || amount<0)return{ok:false,error:'争议金额须为有效的非负数字。'}
    const next=String(state.cases.length+19).padStart(3,'0')
    state.cases.unshift({id:`PL-2026-${next}`,title:input.title||'劳动争议案件',client:input.client||'待补充',employer:input.employer||'待补充用人单位',
      region:input.region||'待选择地区',amount,stage:'案情梳理',risk:'progress',deadline:input.deadline||'待计算',evidence:0,evidenceReady:0,updatedAt:'刚刚'})
    return{ok:true,persisted:persist()}
  }
  return{state,storageIssue,activeCases:computed(()=>state.cases.filter(item=>item.stage!=='已结案')),
    totalAmount:computed(()=>state.cases.filter(item=>item.stage!=='已结案').reduce((sum,item)=>sum+item.amount,0)),addCase}
}
let browserStorage:WorkspaceStorage|undefined
try{if(typeof localStorage!=='undefined')browserStorage=localStorage}
catch{browserStorage={getItem(){throw new Error('Storage unavailable')},setItem(){throw new Error('Storage unavailable')}}}
const workspace=createWorkspace(browserStorage)
export function useWorkspace(){return workspace}
