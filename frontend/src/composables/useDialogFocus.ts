import { nextTick, onBeforeUnmount, watch } from 'vue'
import type {Ref} from 'vue'

// Keep modal keyboard focus inside, make background inert, and restore the trigger.
export function useDialogFocus(open:()=>boolean, element:Readonly<Ref<HTMLElement|null>>, close:()=>void) {
  let previous:Element|null=null, affected:[HTMLElement,boolean][]=[], originalOverflow='', active=false
  const focusable=()=>Array.from(element.value?.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), iframe, [tabindex="0"]')||[]).filter(node=>node.getClientRects().length)
  function keydown(event:KeyboardEvent) {
    if(event.key==='Escape'){event.preventDefault();close();return}
    if(event.key!=='Tab')return
    const nodes=focusable(), first=nodes[0], last=nodes[nodes.length-1]
    if(!first){event.preventDefault();element.value?.focus();return}
    if(event.shiftKey&&(document.activeElement===first||!element.value?.contains(document.activeElement))){event.preventDefault();(last??first).focus()}
    else if(!event.shiftKey&&(document.activeElement===last||!element.value?.contains(document.activeElement))){event.preventDefault();first.focus()}
  }
  function release() {
    if(!active)return
    active=false
    document.removeEventListener('keydown',keydown)
    affected.forEach(([node,inert])=>{node.inert=inert});affected=[]
    document.body.style.overflow=originalOverflow
    nextTick(()=>{const target=previous instanceof HTMLElement&&previous.isConnected&&previous!==document.body&&previous!==document.documentElement?previous:document.querySelector<HTMLElement>('.assistant-fab');target?.focus({preventScroll:true})})
  }
  watch(open,async enabled=>{
    if(!enabled){release();return}
    previous=document.activeElement
    await nextTick()
    if(!open()||!element.value)return
    active=true;originalOverflow=document.body.style.overflow;document.body.style.overflow='hidden'
    let node=element.value
    while(node.parentElement){
      for(const sibling of node.parentElement.children){if(sibling instanceof HTMLElement&&sibling!==node&&!sibling.hasAttribute('data-dialog-backdrop')){affected.push([sibling,sibling.inert]);sibling.inert=true}}
      node=node.parentElement;if(node===document.body)break
    }
    document.addEventListener('keydown',keydown)
    ;(focusable()[0]||element.value).focus({preventScroll:true})
  },{immediate:true,flush:'post'})
  onBeforeUnmount(release)
}
