import {ref,watch,onBeforeUnmount} from 'vue'
import type {Ref} from 'vue'
import type {Region} from '../../../packages/regional-contracts/src/index.ts'
import type {DirectoryArea} from '../data/regionalGuidePresentation.ts'
import {publicError} from '../data/regionalGuidePresentation.ts'
import {publicClient} from '../api/public.ts'
/** Each lazy query belongs only to its current province/city. */
export function useRegionDirectory(region:Readonly<Ref<Region>>) {
 const cityAreas=ref<DirectoryArea[]>([]),districtAreas=ref<DirectoryArea[]>([]),directoryLoading=ref(false),directoryError=ref('')
 let controller:AbortController|undefined,timer:ReturnType<typeof setTimeout>|undefined
 watch([()=>region.value.province,()=>region.value.city],()=>{
  clearTimeout(timer);controller?.abort()
  cityAreas.value=[];districtAreas.value=[];directoryError.value='';directoryLoading.value=true
  const place={...region.value},active=new AbortController();controller=active
  timer=setTimeout(async()=>{
   try{const [cities,districts]=await Promise.all([publicClient.areas(place.province,'',active.signal),place.city?publicClient.areas(place.province,place.city,active.signal):Promise.resolve([])]);if(controller!==active||active.signal.aborted)return;cityAreas.value=cities;districtAreas.value=districts}
   catch(error:unknown){if(!active.signal.aborted&&controller===active)directoryError.value=publicError(error,'地区目录暂时无法读取，可直接输入城市和区县。')}
   finally{if(controller===active)directoryLoading.value=false}
  },180)
 },{immediate:true,flush:'sync'})
 onBeforeUnmount(()=>{clearTimeout(timer);controller?.abort()})
 return{cityAreas,districtAreas,directoryLoading,directoryError}
}
