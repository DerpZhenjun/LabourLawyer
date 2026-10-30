import {shallowRef} from 'vue'
import {APIError,readJSON} from './http'
import {authSession} from './authSession'
import type {AuthUser} from './authSession'
export const currentUser=shallowRef<AuthUser|null>(authSession.get()?.user??null)
let loginRevision=0
export function cancelPendingLogin(){loginRevision++}
authSession.subscribe(()=>{loginRevision++;currentUser.value=authSession.get()?.user??null})
export async function login(username:string,password:string){
  const revision=++loginRevision
  const data=await readJSON('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username,password})})
  if(revision!==loginRevision)return false
  authSession.set(data)
  return true
}
export async function verifySession():Promise<AuthUser|null>{
  const session=authSession.get();if(!session)return null
  const token=session.access_token
  try{
    const user=await readJSON('/api/auth/me')
    if(authSession.get()?.access_token!==token)return null
    authSession.set({...session,user});return authSession.get()?.user??null
  }catch(error){if(error instanceof APIError&&error.status===401&&authSession.get()?.access_token===token)authSession.clear();throw error}
}
export async function logout(){
  cancelPendingLogin()
  const token=authSession.get()?.access_token
  if(!token)return
  // Always clear this device, including during network failure; report unconfirmed server revocation.
  try{await readJSON('/api/auth/logout',{method:'POST'})}
  catch(error){if(!(error instanceof APIError&&error.status===401))throw error}
  finally{if(authSession.get()?.access_token===token)authSession.clear()}
}
export const safeAdminPath=(value:unknown)=>typeof value==='string'&&/^\/admin(?:\/|\?|$)/.test(value)&&!value.includes('\\')?value:'/admin'
