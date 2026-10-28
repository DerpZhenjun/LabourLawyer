import {ref,watch,onBeforeUnmount} from 'vue'
export const regionalAPI=(import.meta.env.VITE_API_BASE_URL||'http://127.0.0.1:8000').replace(/\/$/,'')+'/api/regional-guides'
export const regionQuery=region=>new URLSearchParams({province:region.province||'',city:region.city||'',district:region.district||''}).toString()
export const templateURL=(region,id)=>`${regionalAPI}/templates/${encodeURIComponent(id)}?${regionQuery(region)}`
export function useRegionalGuide(region){
  const guide=ref(null),loading=ref(false),error=ref('')
  let controller,sequence=0
  async function load(){
    const ticket=++sequence;controller?.abort();controller=new AbortController()
    // Clear immediately: never display a previous district while the next is loading.
    guide.value=null;error.value='';loading.value=true
    try{
      const response=await fetch(`${regionalAPI}/lookup?${regionQuery(region.value)}`,{signal:controller.signal})
      if(!response.ok)throw new Error('无法读取当地指南，请确认服务已启动后重试。')
      const result=await response.json()
      if(ticket===sequence)guide.value=result
    }catch(e){if(ticket===sequence&&e.name!=='AbortError')error.value=e instanceof TypeError?'无法连接指南服务，请确认后端已启动后重试。':e.message}
    finally{if(ticket===sequence)loading.value=false}
  }
  // Compare locality values, not a newly allocated array on every route update.
  // Hash navigation must keep the guide mounted and preserve the anchor target.
  watch([()=>region.value.province,()=>region.value.city,()=>region.value.district],load,{immediate:true})
  onBeforeUnmount(()=>{++sequence;controller?.abort()})
  return {guide,loading,error,reload:load}
}
