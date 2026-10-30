import {apiURL as buildURL} from '../../../packages/client-contracts/src/index.ts'
import {parseApiError} from '../../../packages/regional-contracts/src/index.ts'
import {authSession} from './authSession.ts'
import {savedConnection} from './connection.ts'
export const API_BASE=(savedConnection()?.api||import.meta.env?.VITE_API_BASE_URL||'http://127.0.0.1:8000').replace(/\/$/,'')
export const apiURL=(path:string):string=>buildURL(API_BASE || globalThis.location?.origin || 'http://127.0.0.1:8000',path)
export const authorizationHeaders=():Record<string,string>=>{const token=authSession.get()?.access_token;return token?{Authorization:'Bearer '+token}:{}}
export class APIError extends Error {status:number;constructor(status:number,message:string){super(message);this.status=status}}
export async function readJSON(path:string,options:RequestInit={}):Promise<unknown>{
  const session=authSession.get(),headers=new Headers(options.headers)
  if(session)headers.set('Authorization','Bearer '+session.access_token)
  const response=await fetch(apiURL(path),{...options,headers,cache:'no-store'})
  if(response.status===401&&session&&authSession.get()?.access_token===session.access_token)authSession.clear()
  if(response.status===204)return null
  let raw:unknown
  try{raw=await response.json()}catch{throw new Error('服务返回的资料格式不正确，请重试。')}
  if(!response.ok)throw new APIError(response.status,parseApiError(raw))
  return raw
}
