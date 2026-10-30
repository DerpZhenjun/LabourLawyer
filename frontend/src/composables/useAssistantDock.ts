import {onMounted,onUnmounted,ref,watch} from 'vue'
import type {CSSProperties,Ref} from 'vue'
import {resolveAssistantDock} from '@/data/assistantDockGeometry'

export function useAssistantDock(button:Readonly<Ref<HTMLElement|null>>){
  const style=ref<CSSProperties>({}),hidden=ref(false)
  let frame=0,observer:MutationObserver|undefined
  const update=()=>{
    frame=0
    const element=button.value
    if(!element)return
    const size=element.getBoundingClientRect()
    const targets=[...document.querySelectorAll<HTMLButtonElement>('form button[type="submit"], form button:not([type]), .region-generation button')]
      .filter(el=>!el.disabled).map(el=>el.getBoundingClientRect())
    const position=resolveAssistantDock({width:innerWidth,height:innerHeight},size,targets,innerWidth<=700?16:24)
    style.value={right:position.right+'px',bottom:position.bottom+'px',visibility:position.hidden?'hidden':undefined}
    hidden.value=position.hidden
  }
  const schedule=()=>{if(!frame)frame=requestAnimationFrame(update)}
  watch(button,schedule,{flush:'post'})
  onMounted(()=>{
    window.addEventListener('scroll',schedule,{passive:true,capture:true})
    window.addEventListener('resize',schedule,{passive:true})
    observer=new MutationObserver(schedule)
    observer.observe(document.body,{childList:true,subtree:true})
    schedule()
  })
  onUnmounted(()=>{
    if(frame)cancelAnimationFrame(frame)
    observer?.disconnect()
    window.removeEventListener('scroll',schedule,true)
    window.removeEventListener('resize',schedule)
  })
  return {style,hidden}
}
