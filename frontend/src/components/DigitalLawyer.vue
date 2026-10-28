<template>
  <div class="digital-mask" data-dialog-backdrop aria-hidden="true" @click="$emit('close')"></div>
  <section ref="dialog" class="digital-lawyer-modal" role="dialog" aria-modal="true" aria-label="法律数字人" tabindex="-1" :class="{ 'is-expanded': expanded }">
    <header class="digital-header">
      <div class="digital-brand"><span class="brand-icon"><i class="fa-solid fa-user-tie" aria-hidden="true"></i></span><div><small>面对面，聊聊你的问题</small><strong>阿律 · 法律数字人</strong></div></div>
      <div class="window-actions"><button @click="expanded=!expanded" :aria-label="expanded ? '缩小窗口' : '扩大窗口'"><i :class="expanded ? 'fa-solid fa-compress' : 'fa-solid fa-expand'"></i></button><button @click="$emit('close')" aria-label="关闭数字人"><i class="fa-solid fa-xmark"></i></button></div>
    </header>
    <div class="digital-content">
      <iframe v-if="state==='ready'" :key="frameKey" :src="embeddedUrl" title="阿律法律数字人咨询界面" allow="microphone" class="vrm-iframe"></iframe>
      <div v-else class="connection-state" role="status">
        <span class="connection-art"><i :class="state==='loading' ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-plug-circle-exclamation'"></i></span>
        <small>法律数字人</small>
        <h2>{{ state==='loading' ? '正在连接阿律' : '数字人暂未连接' }}</h2>
        <p>{{ state==='loading' ? '正在检查数字人服务，请稍候。' : '数字人服务尚未启动或连接中断。请在项目启动菜单中启动网页端，再重试。' }}</p>
        <button v-if="state==='error'" class="retry-btn" @click="connect"><i class="fa-solid fa-arrow-rotate-right"></i>重新连接</button>
        <a v-if="state==='error'" :href="digitalLawyerUrl" target="_blank" rel="noopener">在独立页面打开 <i class="fa-solid fa-arrow-up-right-from-square"></i></a>
      </div>
    </div>
    <footer><span class="status-dot" :class="state"></span>{{ state==='ready' ? '数字人服务已连接' : state==='loading' ? '正在连接服务' : '连接不可用' }}<span class="footer-note">劳动争议信息辅助</span></footer>
  </section>
</template>
<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useDialogFocus } from '@/composables/useDialogFocus'
const emit=defineEmits(['close'])
const dialog=ref(null)
useDialogFocus(()=>true,dialog,()=>emit('close'))
const digitalLawyerUrl = import.meta.env.VITE_DIGITAL_LAWYER_URL || 'http://127.0.0.1:3000'
const embeddedUrl=new URL(digitalLawyerUrl); embeddedUrl.searchParams.set('embed','1')
const state=ref('loading'), expanded=ref(false), frameKey=ref(0)
let controller, poll, disposed=false
async function connect() {
  controller?.abort(); controller=new AbortController()
  state.value='loading'
  const timeout=setTimeout(()=>controller?.abort(),15000)
  try {
    const response=await fetch(new URL('api/health/',digitalLawyerUrl.endsWith('/')?digitalLawyerUrl:digitalLawyerUrl+'/'),{signal:controller.signal,cache:'no-store'})
    if(!response.ok) throw new Error('Unavailable')
    const status=await response.json()
    if(status.service!=='digital-human') throw new Error('Unexpected service')
    if(!disposed){frameKey.value++;state.value='ready'}
  } catch { if(!disposed) state.value='error' } finally {clearTimeout(timeout)}
}
onMounted(()=>{connect();poll=setInterval(async()=>{if(state.value!=='ready')return;try{const r=await fetch(new URL('api/health/',digitalLawyerUrl.endsWith('/')?digitalLawyerUrl:digitalLawyerUrl+'/'),{signal:AbortSignal.timeout(5000),cache:'no-store'});if(!r.ok)throw new Error('Unavailable')}catch{if(!disposed)state.value='error'}},30000)})
onUnmounted(()=>{disposed=true;controller?.abort();clearInterval(poll)})
</script>
<style scoped>
.digital-lawyer-modal{position:fixed;right:18px;bottom:18px;z-index:100;width:min(540px,calc(100vw - 36px));height:min(820px,calc(100dvh - 36px));display:flex;flex-direction:column;overflow:hidden;border:1px solid #bed1d4;border-radius:22px;background:#f2f7f7;box-shadow:0 24px 90px #09273c38}.digital-lawyer-modal.is-expanded{width:min(1050px,calc(100vw - 36px));height:calc(100dvh - 36px)}.digital-header{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:16px 18px;background:#102b3b;color:#fff}.digital-brand{display:flex;align-items:center;gap:11px}.brand-icon{width:40px;height:40px;display:grid;place-items:center;border:1px solid #3a7278;border-radius:12px;background:#164650;color:#bdf8ea}.digital-brand small{display:block;font-size:9px;letter-spacing:2px;color:#88bdbd;margin-bottom:5px}.digital-brand strong{font-size:15px}.window-actions{display:flex;gap:5px}.window-actions button{width:32px;height:32px;border:0;border-radius:8px;background:#ffffff0d;color:#c4dadf;cursor:pointer}.window-actions button:hover{background:#ffffff20;color:#fff}.digital-content{position:relative;flex:1;min-height:0}.vrm-iframe{width:100%;height:100%;border:0;display:block}.connection-state{height:100%;display:flex;align-items:center;justify-content:center;flex-direction:column;text-align:center;padding:32px;background:radial-gradient(ellipse at 50% 30%,#e0f1ed,transparent 65%),#f5f8f8}.connection-art{display:grid;place-items:center;width:86px;height:86px;border-radius:26px;color:#267974;background:#e6f2ef;border:1px solid #c4dfd8;font-size:28px;margin-bottom:26px}.connection-state small{letter-spacing:2px;font-size:10px;color:#4c8581}.connection-state h3{font-size:22px;color:#143949;margin:12px 0}.connection-state p{max-width:320px;font-size:13px;line-height:1.9;color:#65808b}.retry-btn{margin:18px 0 14px;padding:11px 20px;display:flex;gap:8px;align-items:center;border:0;border-radius:10px;background:#0f766e;color:#fff;font-size:13px;cursor:pointer}.connection-state a{font-size:11px;color:#66868d}footer{display:flex;align-items:center;gap:7px;padding:10px 16px;border-top:1px solid #dce7e8;background:#fff;font-size:10px;color:#607b85}.footer-note{margin-left:auto;color:#8a9da4}.status-dot{width:6px;height:6px;border-radius:50%;background:#bb8956}.status-dot.ready{background:#20a98b}@media(max-width:560px){.digital-lawyer-modal,.digital-lawyer-modal.is-expanded{inset:0;width:100%;height:100dvh;border-radius:0;border:0}.digital-header{padding:12px 14px}.window-actions button:first-child{display:none}}
</style>
<style scoped>
.digital-mask{position:fixed;inset:0;z-index:95;background:#122d3266}.digital-header{background:var(--ll-primary)}.digital-lawyer-modal{border-radius:16px;border-color:var(--ll-border)}.digital-brand small{font-size:12px;letter-spacing:0;color:#e0eee8}.digital-brand strong{font-size:17px}.window-actions button{width:44px;height:44px;color:#fff}.connection-state h2{font-size:24px;color:var(--ll-text);margin:12px 0}.connection-state p{font-size:15px;color:var(--ll-secondary)}.connection-state small{font-size:13px;letter-spacing:0;color:var(--ll-primary)}.connection-state a{font-size:14px;min-height:44px;display:inline-flex;align-items:center;gap:8px}.retry-btn{font-size:15px;min-height:48px;background:var(--ll-primary)}footer{font-size:12px;color:var(--ll-secondary)}.footer-note{color:var(--ll-secondary)}
@media(max-width:560px){.digital-lawyer-modal{border-radius:0}.digital-brand strong{font-size:16px}}
</style>
