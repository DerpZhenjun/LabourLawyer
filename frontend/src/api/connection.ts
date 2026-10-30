import {normalizeServiceAddress} from '../../../packages/client-contracts/src/index.ts'
export interface Connection {api:string;digital:string}
const KEY='labourlawyer.connection.v1'
declare global {interface Window {labourLawyerDesktop?:{connection?:{read:()=>unknown;write:(value:Connection|null)=>void}}}}
const desktopConnection=()=>typeof window==='undefined'?undefined:window.labourLawyerDesktop?.connection
export function savedConnection():Connection|null {
 try{
  const bridge=desktopConnection()
  const raw:unknown=bridge?bridge.read():JSON.parse(localStorage.getItem(KEY)||'null')
  if(!raw||typeof raw!=='object'||!('api' in raw)||typeof raw.api!=='string')return null
  const digital='digital' in raw&&typeof raw.digital==='string'&&raw.digital?normalizeServiceAddress(raw.digital):''
  return{api:normalizeServiceAddress(raw.api),digital}
 }catch{return null}
}
export function saveConnection(value:Connection){
 const next={api:normalizeServiceAddress(value.api),digital:value.digital?normalizeServiceAddress(value.digital):''}
 const bridge=desktopConnection();bridge?.write(next)
 try{localStorage.setItem(KEY,JSON.stringify(next))}catch(e){if(!bridge)throw e}
}
export const clearConnection=()=>{const bridge=desktopConnection();bridge?.write(null);try{localStorage.removeItem(KEY)}catch(e){if(!bridge)throw e}}
