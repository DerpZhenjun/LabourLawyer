import {savedConnection} from './connection.ts'
import type {components} from '../../../packages/client-contracts/src/generated/stable-api'
export type AuthUser=components['schemas']['UserResponse']
export type LoginSession=components['schemas']['LoginResponse']
interface StorageLike {getItem(key:string):string|null;setItem(key:string,value:string):void;removeItem(key:string):void}
const KEY='labourlawyer.session.v1'
export function createAuthSession(storage?:StorageLike,namespace='default'){
  const key=KEY+':'+namespace
  let current:LoginSession|null=null
  const listeners=new Set<()=>void>()
  const valid=(v:unknown):v is LoginSession=>{
    if(!v||typeof v!=='object')return false
    const s=v as Partial<LoginSession>,u=s.user
    return typeof s.access_token==='string'&&/^[A-Za-z0-9_-]{43}$/.test(s.access_token)&&s.token_type==='bearer'&&typeof s.expires_at==='number'&&Number.isFinite(s.expires_at)&&!!u&&typeof u.id==='string'&&typeof u.username==='string'&&['user','admin'].includes(u.role)
  }
  try{const raw=storage?.getItem(key);if(raw){const parsed:unknown=JSON.parse(raw);if(valid(parsed))current=parsed}}catch{/* unavailable/corrupt storage is not overwritten */}
  let timer:ReturnType<typeof setTimeout>|undefined
  const notify=()=>listeners.forEach(fn=>fn())
  const clear=()=>{if(timer!==undefined)clearTimeout(timer);timer=undefined;current=null;try{storage?.removeItem(key)}catch{}notify()}
  const arm=()=>{
    if(timer!==undefined)clearTimeout(timer);timer=undefined
    if(!current)return
    timer=setTimeout(()=>{timer=undefined;if(current&&current.expires_at<=Date.now()/1000)clear();else arm()},Math.max(0,Math.min(2147483647,(current.expires_at-Date.now()/1000)*1000)))
    const handle:unknown=timer
    if(handle&&typeof handle==='object'){const unref:unknown=Reflect.get(handle,'unref');if(typeof unref==='function')unref.call(handle)}
  }
  const get=()=>{if(current&&current.expires_at<=Date.now()/1000)clear();return current}
  const set=(value:unknown)=>{if(!valid(value)||value.expires_at<=Date.now()/1000)throw Error('登录信息格式不正确');current=value;try{storage?.setItem(key,JSON.stringify(value))}catch{}arm();notify()}
  arm()
  return{get,set,clear,subscribe(fn:()=>void){listeners.add(fn);return()=>listeners.delete(fn)}}
}
let storage:StorageLike|undefined
try{storage=globalThis.sessionStorage}catch{}
export const authSession=createAuthSession(storage,savedConnection()?.api||'default')

if(typeof globalThis.addEventListener==='function'){globalThis.addEventListener('focus',()=>authSession.get());globalThis.addEventListener('visibilitychange',()=>authSession.get())}
