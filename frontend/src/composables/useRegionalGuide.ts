import {ref,watch,onBeforeUnmount} from 'vue'
import type {Ref} from 'vue'
import type {Region,RegionalGuide} from '../../../packages/regional-contracts/src/index.ts'
import {regionQuery} from '../../../packages/regional-contracts/src/index.ts'
import {createRegionalClient} from '../api/regional.ts'
export {regionQuery}
export const regionalClient=createRegionalClient(import.meta.env.VITE_API_BASE_URL||'http://127.0.0.1:8000')
export const regionalAPI=regionalClient.base
export const templateURL=(region:Region,id:string,binding?:{source_id:string;version:number})=>
  `${regionalAPI}/templates/${encodeURIComponent(id)}?${regionQuery(region)}${binding?`&source_id=${encodeURIComponent(binding.source_id)}&version=${binding.version}`:''}`
export function useRegionalGuide(region:Readonly<Ref<Region>>) {
  const guide=ref<RegionalGuide|null>(null),loading=ref(false),error=ref('')
  let controller:AbortController|undefined,sequence=0
  async function load() {
    const ticket=++sequence;controller?.abort();controller=new AbortController()
    const selected={...region.value}
    guide.value=null;error.value='';loading.value=true
    try{const result=await regionalClient.lookup(selected,controller.signal);if(ticket===sequence)guide.value=result}
    catch(e:unknown){if(ticket===sequence && !(e instanceof Error&&e.name==='AbortError'))error.value=e instanceof TypeError?'无法连接指南服务，请确认后端已启动后重试。':e instanceof Error?e.message:'无法读取当地指南，请稍后重试。'}
    finally{if(ticket===sequence)loading.value=false}
  }
  watch([()=>region.value.province,()=>region.value.city,()=>region.value.district],load,{immediate:true})
  onBeforeUnmount(()=>{++sequence;controller?.abort()})
  return {guide,loading,error,reload:load}
}
