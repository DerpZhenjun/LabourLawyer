import {ref,watch,onBeforeUnmount} from 'vue'
import {regionalAPI} from './useRegionalGuide'

/** Lazy per-province/city suggestions. Old regions never survive a changed key. */
export function useRegionDirectory(region){
  const cityAreas=ref([]),districtAreas=ref([]),directoryLoading=ref(false),directoryError=ref('')
  let controller=null,timer=null
  watch([()=>region.value.province,()=>region.value.city],()=>{
    clearTimeout(timer);controller?.abort()
    cityAreas.value=[];districtAreas.value=[];directoryError.value='';directoryLoading.value=true
    const place={...region.value},active=new AbortController();controller=active
    timer=setTimeout(async()=>{
      try{
        const load=async city=>{
          const query=new URLSearchParams({province:place.province,...(city?{city}:{})})
          const response=await fetch(`${regionalAPI}/areas?${query}`,{signal:active.signal})
          if(!response.ok)throw new Error('地区目录暂时无法读取，可直接输入城市和区县。')
          return (await response.json()).items
        }
        const result=await Promise.all([load(''),place.city?load(place.city):Promise.resolve([])])
        if(controller!==active)return
        cityAreas.value=result[0];districtAreas.value=result[1]
      }catch(error){if(error.name!=='AbortError'&&controller===active)directoryError.value=error.message}
      finally{if(controller===active)directoryLoading.value=false}
    },180)
  },{immediate:true})
  onBeforeUnmount(()=>{clearTimeout(timer);controller?.abort()})
  return {cityAreas,districtAreas,directoryLoading,directoryError}
}
