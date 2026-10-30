import {apiURL as buildURL} from '../../../packages/client-contracts/src/index.ts'
import {parseApiError} from '../../../packages/regional-contracts/src/index.ts'
export const API_BASE=(import.meta.env?.VITE_API_BASE_URL||'http://127.0.0.1:8000').replace(/\/$/,'')
export const apiURL=(path:string):string=>buildURL(API_BASE || globalThis.location?.origin || 'http://127.0.0.1:8000',path)
export class APIError extends Error {status:number;constructor(status:number,message:string){super(message);this.status=status}}
export async function readJSON(path:string,options:RequestInit={}):Promise<unknown>{
  const response=await fetch(apiURL(path),options)
  let raw:unknown
  try{raw=await response.json()}catch{throw new Error('服务返回的资料格式不正确，请重试。')}
  if(!response.ok)throw new APIError(response.status,parseApiError(raw))
  return raw
}
