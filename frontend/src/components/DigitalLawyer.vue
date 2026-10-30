<template>
  <section ref="dialog" class="digital-lawyer-modal" role="dialog" aria-modal="false" aria-label="法律数字人" tabindex="-1" :class="{ 'is-collapsed': collapsed }">
    <header class="digital-header">
      <div class="digital-brand"><BrandMark variant="assistant" :size="32" /><div><strong>阿律 · 法律数字人</strong><small>{{ collapsed ? '点击展开，继续聊' : '说说你的问题，我来帮你梳理' }}</small></div></div>
      <div class="window-actions">
        <button :aria-label="collapsed ? '展开对话' : '收起对话'" :aria-expanded="!collapsed" aria-controls="digital-conversation" @click="collapsed=!collapsed"><i :class="collapsed ? 'fa-solid fa-chevron-up' : 'fa-solid fa-minus'" aria-hidden="true"></i></button>
        <button @click="$emit('close')" aria-label="关闭数字人"><i class="fa-solid fa-xmark" aria-hidden="true"></i></button>
      </div>
    </header>
    <div id="digital-conversation" v-show="!collapsed" class="digital-content">
      <iframe v-if="state==='ready'" ref="frame" :key="frameKey" :src="embeddedUrl.toString()" title="阿律法律数字人咨询界面" allow="microphone" class="vrm-iframe"></iframe>
      <div v-else class="connection-state" role="status">
        <BrandMark variant="assistant" :size="48" />
        <h2>{{ state==='loading' ? '正在连接阿律' : '暂时没有连接上' }}</h2>
        <p>{{ state==='loading' ? '稍等一下，很快就好。' : '请确认项目中的数字人服务正在运行，再试一次。' }}</p>
        <button v-if="state==='error'" class="retry-btn" @click="connect">重新连接</button>
      </div>
    </div>
    <footer v-show="!collapsed"><span class="status-dot" :class="state"></span>{{ state==='ready' ? '数字人已连接' : state==='loading' ? '正在连接' : '连接不可用' }}<span>劳动争议信息辅助</span></footer>
  </section>
</template>
<script setup lang="ts">
import { ref, nextTick, onMounted, onUnmounted } from 'vue'
import {savedConnection} from '@/api/connection'
import BrandMark from '@/components/BrandMark.vue'
const emit=defineEmits<{close:[]}>()
const dialog=ref<HTMLElement|null>(null), frame=ref<HTMLIFrameElement|null>(null), collapsed=ref(false)
const digitalLawyerUrl=savedConnection()?.digital||import.meta.env.VITE_DIGITAL_LAWYER_URL||'http://127.0.0.1:3000'
const serviceOrigin=new URL(digitalLawyerUrl).origin
const embeddedUrl=new URL(digitalLawyerUrl);embeddedUrl.searchParams.set('embed','1')
const state=ref<'loading'|'ready'|'error'>('loading'),frameKey=ref(0)
let controller:AbortController|undefined,poll:ReturnType<typeof setInterval>|undefined,disposed=false,previous:Element|null=null
async function connect(){
  controller?.abort();const current=new AbortController();controller=current;state.value='loading'
  const timeout=setTimeout(()=>current.abort(),15000)
  try{
    const r=await fetch(new URL('api/health/',digitalLawyerUrl.endsWith('/')?digitalLawyerUrl:digitalLawyerUrl+'/'),{signal:current.signal,cache:'no-store'})
    if(!r.ok||(await r.json()).service!=='digital-human')throw new Error('Unavailable')
    if(!disposed&&controller===current){frameKey.value++;state.value='ready'}
  }catch{if(!disposed&&controller===current)state.value='error'}finally{clearTimeout(timeout)}
}
function keydown(event:KeyboardEvent){if(event.key==='Escape'&&!event.defaultPrevented&&dialog.value?.contains(document.activeElement)){event.preventDefault();emit('close')}}
function frameMessage(event:MessageEvent<unknown>){
  if(event.origin===serviceOrigin&&event.source===frame.value?.contentWindow&&event.data!==null&&typeof event.data==='object'&&'type' in event.data&&event.data.type==='labourlawyer:digital-close')emit('close')
}
onMounted(()=>{
  previous=document.activeElement;nextTick(()=>dialog.value?.focus({preventScroll:true}))
  document.addEventListener('keydown',keydown);window.addEventListener('message',frameMessage)
  connect();poll=setInterval(async()=>{if(state.value!=='ready')return;try{const r=await fetch(new URL('api/health/',digitalLawyerUrl.endsWith('/')?digitalLawyerUrl:digitalLawyerUrl+'/'),{signal:AbortSignal.timeout(5000),cache:'no-store'});if(!r.ok)throw new Error('Unavailable')}catch{if(!disposed)state.value='error'}},30000)
})
onUnmounted(()=>{
  disposed=true;controller?.abort();clearInterval(poll)
  document.removeEventListener('keydown',keydown);window.removeEventListener('message',frameMessage)
  nextTick(()=>{const target=previous instanceof HTMLElement&&previous.isConnected&&previous!==document.body?previous:document.querySelector<HTMLElement>('.assistant-fab');target?.focus({preventScroll:true})})
})
</script>
<style scoped>
.digital-lawyer-modal{position:fixed;right:max(16px,env(safe-area-inset-right));bottom:max(16px,env(safe-area-inset-bottom));z-index:100;width:min(400px,calc(100vw - 32px));height:min(640px,calc(100dvh - 96px));display:flex;flex-direction:column;overflow:hidden;border:1px solid var(--ll-border);border-radius:16px;background:#fff;box-shadow:0 16px 48px #122d322b}
.digital-lawyer-modal.is-collapsed{height:68px;width:min(320px,calc(100vw - 32px))}.digital-header{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:12px;background:var(--ll-primary);color:#fff;flex-shrink:0;min-height:68px}.digital-brand{display:flex;align-items:center;gap:8px;min-width:0}.digital-brand strong{display:block;font-size:14px;line-height:1.5}.digital-brand small{display:block;font-size:11px;line-height:1.5;color:#e0eee8}.window-actions{display:flex;gap:4px}.window-actions button{display:grid;place-items:center;width:44px;height:44px;border:0;border-radius:8px;color:#fff;background:transparent;cursor:pointer}.window-actions button:hover{background:#ffffff20}.window-actions button:focus-visible{outline:2px solid #fff;outline-offset:-3px}.digital-content{position:relative;flex:1;min-height:0}.vrm-iframe{width:100%;height:100%;border:0;display:block}.connection-state{height:100%;display:flex;align-items:center;justify-content:center;flex-direction:column;text-align:center;gap:12px;padding:24px;color:var(--ll-text);background:var(--ll-background)}.connection-state h2{font-size:18px;margin:0}.connection-state p{font-size:14px;line-height:1.75;color:var(--ll-secondary);margin:0}.retry-btn{min-height:44px;border:0;border-radius:8px;padding:8px 20px;background:var(--ll-primary);color:#fff;cursor:pointer}footer{display:flex;align-items:center;gap:6px;flex-shrink:0;padding:8px 12px;border-top:1px solid var(--ll-border);font-size:11px;color:var(--ll-secondary)}footer>span:last-child{margin-left:auto}.status-dot{width:6px;height:6px;border-radius:50%;background:#b88b52}.status-dot.ready{background:#18836c}
@media(max-width:560px){.digital-lawyer-modal{right:12px;bottom:max(12px,env(safe-area-inset-bottom));width:calc(100vw - 24px)}.digital-lawyer-modal.is-collapsed{width:min(320px,calc(100vw - 24px))}}
</style>
