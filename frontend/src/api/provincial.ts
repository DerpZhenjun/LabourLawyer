import axios from 'axios'
import {apiURL} from './http'

export {ProvincialValidationError} from '../../../packages/regional-contracts/src/provincial.ts'
export type {ProvincialValidation,ProvincialFieldError} from '../../../packages/regional-contracts/src/provincial.ts'
export const isProvincialRecord=(value:unknown):value is Record<string,unknown>=>
  value!==null&&typeof value==='object'&&!Array.isArray(value)&&[Object.prototype,null].includes(Object.getPrototypeOf(value))
export function provincialInputValue(value:unknown):string|number {
  return typeof value==='number'||typeof value==='string'?value:value==null?'':String(value)
}
export function provincialEventValue(event:Event):string {
  const target=event.target
  return target instanceof HTMLInputElement||target instanceof HTMLTextAreaElement||target instanceof HTMLSelectElement?target.value:''
}
export interface ProvincialDraft<T> {form:T;raw:unknown;blocked:boolean;saved:boolean;notice:string;saveBlocked?:boolean}
const clone=<T>(value:T):T=>structuredClone(value)
/** Retain unknown legacy keys. Malformed stored text remains untouched until explicit clear. */
const CLEARED='{"__labourlawyer_cleared_draft_v7":true}'
export function readProvincialDraft<T extends Record<string,unknown>>(key:string,defaults:T,legacyKey?:string):ProvincialDraft<T> {
  let raw:unknown=null
  let stored=false
  try {
    const primary=localStorage.getItem(key)
    const text=primary===null&&legacyKey?localStorage.getItem(legacyKey):primary
    if(text===CLEARED)return {form:clone(defaults),raw:null,blocked:false,saved:false,notice:''}
    if(text===null)return {form:clone(defaults),raw:null,blocked:false,saved:false,notice:''}
    stored=true
    raw=text
    const parsed:unknown=JSON.parse(text);raw=parsed
    if(!isProvincialRecord(parsed))throw new Error('shape')
    const form={...clone(defaults),...parsed}
    for(const [field,initial] of Object.entries(defaults)) {
      const value=form[field]
      if(Array.isArray(initial)) {
        if(!Array.isArray(value))throw new Error('list')
        if(field==='requests'&&!value.every(v=>typeof v==='string'))throw new Error('requests')
        if(field==='evidenceList'&&!value.every(isProvincialRecord))throw new Error('evidence')
      } else if(field==='copyCount') {
        if(typeof value!=='string'&&(typeof value!=='number'||!Number.isFinite(value)))throw new Error('copies')
      } else if(typeof initial==='string'&&typeof value!=='string')throw new Error('text')
    }
    return {form,raw,blocked:false,saved:true,notice:''}
  } catch {
    return {form:clone(defaults),raw,blocked:stored,saved:stored,saveBlocked:true,notice:stored?'保存的草稿格式无法读取，原始内容仍保留在本机。请重置本次填写后重试。':'草稿暂无法读取，仍可填写和生成；请自行保留重要内容。'}
  }
}
export function saveProvincialDraft(key:string,value:unknown):string {
  try {localStorage.setItem(key,JSON.stringify(value));return ''}catch{return '草稿暂未保存，请自行保留内容；仍可生成文书。'}
}
/** A scoped tombstone suppresses legacy fallback without deleting legacy bytes. */
export function clearProvincialDraft(key:string):string {
  try{localStorage.setItem(key,CLEARED);return ''}catch{return '重置状态暂未保存，旧本机内容仍保留；请自行保管重要内容。'}
}
export async function postProvincialDocument(path:string,payload:Readonly<Record<string,unknown>>,signal?:AbortSignal):Promise<Blob> {
  const response=await axios.post<unknown>(apiURL(path),payload,{responseType:'blob',timeout:30000,...(signal?{signal}:{})})
  if(!(response.data instanceof Blob))throw new TypeError('生成服务没有返回文书文件，请重试。')
  return response.data
}
export async function provincialError(error:unknown,showResponseDetail=true):Promise<string> {
  if(axios.isAxiosError<unknown>(error)) {
    const raw=error.response?.data
    if(raw instanceof Blob) {
      try {const value:unknown=JSON.parse(await raw.text());if(isProvincialRecord(value)&&typeof value.detail==='string')return value.detail}catch{/* retain safe fallback */}
    }
    if(showResponseDetail&&isProvincialRecord(raw)&&typeof raw.detail==='string')return raw.detail
    if(error.code==='ERR_NETWORK')return '无法连接文书生成服务，请确认后端已经启动。'
  }
  return '生成失败，请稍后再试。'
}
