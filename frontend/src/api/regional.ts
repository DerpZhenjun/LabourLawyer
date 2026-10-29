import {
  assertFormContract, assertRegionalGuide, buildGenerateRequest, isPlainRecord, parseApiError, regionQuery,
} from '../../../packages/regional-contracts/src/index.ts'
import type {FormContract,FormContext,Region,RegionalGuide} from '../../../packages/regional-contracts/src/index.ts'

export type FormContractQuery = Region & Pick<FormContext,'source_id'|'version'|'template_id'|'kind'> & Partial<Pick<FormContext,'adapter'|'region_code'>>
export interface AreaOption { city?:string; district?:string; [key:string]:unknown }
export function createRegionalClient(baseURL:string,fetcher:typeof fetch=fetch) {
  const base=baseURL.replace(/\/$/,'')+'/api/regional-guides'
  const request=(url:string,signal?:AbortSignal,init:RequestInit={})=>fetcher(url,{...init,...(signal?{signal}:{})})
  async function read(response:Response):Promise<unknown> {
    let result:unknown
    try{result=await response.json()}catch{throw new Error('服务返回的资料格式不正确，请稍后重新核对。')}
    if(!response.ok)throw new Error(parseApiError(result))
    return result
  }
  return {
    base,
    async lookup(region:Region,signal?:AbortSignal):Promise<RegionalGuide> {
      return assertRegionalGuide(await read(await request(`${base}/lookup?${regionQuery(region)}`,signal)),region)
    },
    async areas(province:string,city='',signal?:AbortSignal):Promise<AreaOption[]> {
      const raw=await read(await request(`${base}/areas?province=${encodeURIComponent(province)}&city=${encodeURIComponent(city)}`,signal))
      if(!isPlainRecord(raw)||!Array.isArray(raw.items)||!raw.items.every(item=>isPlainRecord(item)&&typeof item[city?'district':'city']==='string'))throw new Error('地区目录格式不正确，请重新选择。')
      return raw.items as AreaOption[]
    },
    async contract(context:FormContractQuery,signal?:AbortSignal):Promise<FormContract> {
      const query=regionQuery(context)+`&source_id=${encodeURIComponent(context.source_id)}&version=${context.version}&template_id=${encodeURIComponent(context.template_id)}&kind=${context.kind}`
      return assertFormContract(await read(await request(`${base}/form-contract?${query}`,signal)),context)
    },
    async generate(contract:FormContract,form:unknown,signal?:AbortSignal):Promise<Blob> {
      const payload=buildGenerateRequest(contract,form)
      const response=await request(`${base}/generate`,signal,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})
      if(!response.ok){await read(response);throw new Error('无法生成，请核对内容。')}
      const context=contract.context,origin=response.headers.get('X-Document-Origin')
      if(response.headers.get('X-Form-Contract-ID')!==contract.contract_id || response.headers.get('X-Guide-Source-ID')!==context.source_id || response.headers.get('X-Guide-Version')!==String(context.version) ||
          !(context.mode==='reference_adaptation'?origin==='official-sample-adaptation-not-blank':['official-blank-filled','official-blank-converted-filled'].includes(origin ?? '')))
        throw new Error('下载文件的地区或来源版本不匹配，请重新选择地区核对。')
      const blob=await response.blob(),head=new Uint8Array(await blob.slice(0,4).arrayBuffer())
      if(head.length!==4||head[0]!==0x50||head[1]!==0x4b||head[2]!==3||head[3]!==4)throw new Error('没有收到有效的Word文件，请重试。')
      return blob
    },
  }
}
