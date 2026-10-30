/** Public tools remain anonymous-capable; account drafts never adopt device data. */
import {computed,shallowRef,watch} from 'vue'
import {currentUser} from './auth'
import {API_BASE} from './http'

const server=API_BASE||globalThis.location?.origin||'http://127.0.0.1:8000'
export const publicDraftOwner=computed(()=>JSON.stringify([server,currentUser.value?.id??null]))
let revision=0
export const publicEditorIdentity=shallowRef(JSON.stringify([publicDraftOwner.value,revision]))
watch(publicDraftOwner,value=>{publicEditorIdentity.value=JSON.stringify([value,++revision])},{flush:'sync'})

export function provincialDraftKey(api:string,userId:string|null,province:string,kind:'application'|'evidence'):string {
  return 'labourlawyer.provincial-draft.v7:'+encodeURIComponent(JSON.stringify([api.replace(/\/$/,''),userId,province,kind]))
}
export function provincialDraftLocation(province:string,kind:'application'|'evidence'):{key:string;notice:string;legacyKey?:string} {
  const userId=currentUser.value?.id??null
  const base={key:provincialDraftKey(server,userId,province,kind),
    notice:userId===null?'未登录设备草稿：仅保存在这台设备，登录账号不会自动读取。':'当前账号的本机草稿，仅在这台设备恢复。'}
  return userId===null?{...base,legacyKey:`labourlawyer-${province}-${kind}-draft-v6`}:base
}
