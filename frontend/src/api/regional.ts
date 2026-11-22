import {
  assertFormContract, assertRegionalGuide, buildGenerateRequest, isOfficeZip, isPlainRecord, parseApiError, regionQuery, XLSX_MIME,
} from '../../../packages/regional-contracts/src/index.ts'
import type {FormContract,FormContext,Region,RegionalGuide} from '../../../packages/regional-contracts/src/index.ts'

export type FormContractQuery = Region & Pick<FormContext,'source_id'|'version'|'template_id'|'kind'> & Partial<Pick<FormContext,'adapter'|'region_code'|'output_format'>>
export interface AreaOption { city?:string; district?:string; [key:string]:unknown }
export interface OfficialBlankLayout { layoutSha256:string; officialSha256:string }

const sha256Pattern=/^[a-f0-9]{64}$/

function matchesGenerationOrigin(context:FormContext,headers:Headers,layout?:OfficialBlankLayout):boolean {
  const origin=headers.get('X-Document-Origin')
  if(context.mode==='reference_adaptation')return origin==='official-sample-adaptation-not-blank'&&!layout
  if(!layout)return origin==='official-blank-filled'||origin==='official-blank-converted-filled'
  return origin==='official-blank-metadata-sanitized-filled'&&
    headers.get('X-Document-Layout-Origin')==='official-blank-metadata-sanitized-layout'&&
    sha256Pattern.test(layout.layoutSha256)&&sha256Pattern.test(layout.officialSha256)&&
    layout.layoutSha256!==layout.officialSha256&&headers.get('X-Template-SHA256')===layout.layoutSha256&&
    headers.get('X-Official-Original-SHA256')===layout.officialSha256
}

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
      return assertRegionalGuide(await read(await request(`${base}/lookup?${regionQuery(region)}&xlsx=true`,signal)),region)
    },
    async areas(province:string,city='',signal?:AbortSignal):Promise<AreaOption[]> {
      const raw=await read(await request(`${base}/areas?province=${encodeURIComponent(province)}&city=${encodeURIComponent(city)}&xlsx=true`,signal))
      if(!isPlainRecord(raw)||!Array.isArray(raw.items)||!raw.items.every(item=>isPlainRecord(item)&&typeof item[city?'district':'city']==='string'))throw new Error('地区目录格式不正确，请重新选择。')
      return raw.items as AreaOption[]
    },
    async contract(context:FormContractQuery,signal?:AbortSignal):Promise<FormContract> {
      const query=regionQuery(context)+`&source_id=${encodeURIComponent(context.source_id)}&version=${context.version}&template_id=${encodeURIComponent(context.template_id)}&kind=${context.kind}&xlsx=true`
      return assertFormContract(await read(await request(`${base}/form-contract?${query}`,signal)),context)
    },
    async generate(contract:FormContract,form:unknown,signal?:AbortSignal,layout?:OfficialBlankLayout):Promise<Blob> {
      const payload=buildGenerateRequest(contract,form)
      const response=await request(`${base}/generate${contract.context.output_format==='xlsx'?'?xlsx=true':''}`,signal,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})
      if(!response.ok){await read(response);throw new Error('无法生成，请核对内容。')}
      const context=contract.context
      if(response.headers.get('X-Form-Contract-ID')!==contract.contract_id || response.headers.get('X-Guide-Source-ID')!==context.source_id || response.headers.get('X-Guide-Version')!==String(context.version) ||
          !matchesGenerationOrigin(context,response.headers,layout))
        throw new Error('下载文件的地区或来源版本不匹配，请重新选择地区核对。')
      const blob=await response.blob()
      if(context.output_format==='xlsx'){
        if(blob.type!==XLSX_MIME || !isOfficeZip(await blob.arrayBuffer(),'xlsx'))throw new Error('没有收到有效的 Excel 工作簿，请重试。')
        return blob
      }
      const head=new Uint8Array(await blob.slice(0,4).arrayBuffer())
      if(head.length!==4||head[0]!==0x50||head[1]!==0x4b||head[2]!==3||head[3]!==4)throw new Error('没有收到有效的Word文件，请重试。')
      return blob
    },
  }
}
