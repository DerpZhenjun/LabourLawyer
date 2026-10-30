import {savedConnection} from './connection.ts'
import {APIError,apiURL,readJSON} from './http.ts'
import {normalizeServiceAddress} from '../../../packages/client-contracts/src/index.ts'
import {configuredDigitalOrigin} from '../../../packages/client-contracts/src/services.ts'
const local=(url:string)=>['localhost','127.0.0.1','[::1]','::1'].includes(new URL(url).hostname)
export async function resolveDigitalService(signal:AbortSignal):Promise<string>{
 const selected=savedConnection()?.digital
 if(selected)return normalizeServiceAddress(selected)
 try{
  const configured=configuredDigitalOrigin(await readJSON('/api/services',{signal}))
  if(configured)return configured
 }catch(error){if(!(error instanceof APIError&&error.status===404))throw error}
 const legacy=normalizeServiceAddress(import.meta.env.VITE_DIGITAL_LAWYER_URL||'http://127.0.0.1:3000')
 if(local(apiURL('/health'))||!local(legacy))return legacy
 throw Error('这个服务尚未配置数字人地址，请在连接设置中填写，或联系服务维护人员。')
}
