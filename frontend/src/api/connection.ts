import {normalizeServiceAddress} from '../../../packages/client-contracts/src/index.ts'
export interface Connection {api:string;digital:string}
const KEY='labourlawyer.connection.v1'
export function savedConnection():Connection|null {
 try{
  const raw:unknown=JSON.parse(localStorage.getItem(KEY)||'null')
  if(!raw||typeof raw!=='object'||!('api' in raw)||typeof raw.api!=='string')return null
  const digital='digital' in raw&&typeof raw.digital==='string'&&raw.digital?normalizeServiceAddress(raw.digital):''
  return{api:normalizeServiceAddress(raw.api),digital}
 }catch{return null}
}
export function saveConnection(value:Connection){
 const next={api:normalizeServiceAddress(value.api),digital:value.digital?normalizeServiceAddress(value.digital):''}
 localStorage.setItem(KEY,JSON.stringify(next))
}
export const clearConnection=()=>localStorage.removeItem(KEY)
