<template>
  <Transition name="panel">
    <section v-if="open" ref="dialog" class="assistant-panel" role="dialog" aria-modal="true" aria-label="AI 法律助手" tabindex="-1">
      <header>
        <div class="assistant-identity"><span><i class="fa-solid fa-scale-balanced" aria-hidden="true"></i></span><div><strong>AI 劳动法律助手</strong><small>帮你理清问题，准备材料</small></div></div>
        <div class="header-actions"><button class="digital-entry" title="打开法律数字人" aria-label="数字人：打开法律数字人" @click="$emit('open-digital-human')"><i class="fa-solid fa-user-tie"></i><span>数字人</span></button><button title="清空对话" aria-label="清空对话" @click="clearHistory"><i class="fa-regular fa-trash-can"></i></button><button title="关闭" aria-label="关闭" @click="$emit('close')"><i class="fa-solid fa-xmark"></i></button></div>
      </header>
      <div class="assistant-context"><i class="fa-solid fa-circle-info"></i>回答仅用于辅助梳理，不替代执业律师意见；重要结论请结合原始材料核验。</div>
      <div ref="chatRef" class="chat-stream">
        <div v-for="(msg,index) in messages" :key="index" class="message" :class="msg.role">
          <span v-if="msg.role==='ai'" class="assistant-avatar">法</span>
          <div><small>{{ msg.role==='ai' ? 'AI 助手' : '你' }}</small><div class="bubble" v-html="renderMarkdown(msg.content)"></div></div>
        </div>
        <div v-if="isLoading" class="message ai"><span class="assistant-avatar">法</span><div><small>AI 助手</small><div class="bubble typing"><i></i><i></i><i></i></div></div></div>
      </div>
      <div v-if="messages.length<2" class="suggestions"><button v-for="item in prompts" :key="item" @click="inputQuery=item">{{ item }}</button></div>
      <form @submit.prevent="sendMessage">
        <label for="assistant-question" class="assistant-input-label">说说你遇到的问题</label>
        <textarea id="assistant-question" v-model="inputQuery" rows="2" placeholder="例如：公司拖欠了两个月的工资……" :disabled="isLoading" @keydown.enter.exact.prevent="sendMessage"></textarea>
        <div><span><i class="fa-solid fa-lock" aria-hidden="true"></i> 请勿填写完整身份证号等信息</span><button type="submit" aria-label="发送问题" :disabled="isLoading||!inputQuery.trim()"><i class="fa-solid fa-arrow-up" aria-hidden="true"></i></button></div>
        <span class="sr-only" role="status">{{ isLoading ? '正在回答，请稍候' : '' }}</span>
      </form>
    </section>
  </Transition>
  <Transition name="fade"><div v-if="open" class="assistant-mask" data-dialog-backdrop aria-hidden="true" @click="$emit('close')"></div></Transition>
</template>
<script setup>
import { nextTick, onMounted, ref, watch } from 'vue'; import { marked } from 'marked'; import DOMPurify from 'dompurify'
import { useDialogFocus } from '@/composables/useDialogFocus'
const props=defineProps({ open:{type:Boolean,default:false} }); const emit=defineEmits(['close','open-digital-human'])
const dialog=ref(null)
useDialogFocus(()=>props.open,dialog,()=>emit('close'))
const API_BASE=(import.meta.env.VITE_API_BASE_URL||'http://127.0.0.1:8000').replace(/\/$/,'')
const inputQuery=ref(''); const messages=ref([]); const isLoading=ref(false); const chatRef=ref(null)
const prompts=['公司没有签劳动合同，我能主张什么？','帮我梳理申请劳动仲裁需要的证据','违法解除赔偿金怎么计算？']
const welcome={role:'ai',content:'你好，我是你的劳动法律助手。\n\n工资没发、没有签合同，或是不知道怎么申请仲裁？说说发生了什么，我可以帮你理清思路和需要准备的材料。'}
const renderMarkdown=text=>DOMPurify.sanitize(marked.parse(text||'')); const scroll=async()=>{await nextTick();if(chatRef.value)chatRef.value.scrollTop=chatRef.value.scrollHeight}; const save=()=>localStorage.setItem('labourlawyer.chat.v1',JSON.stringify(messages.value))
const clearHistory=()=>{messages.value=[welcome];save()}
const sendMessage=async()=>{
  const text=inputQuery.value.trim(); if(!text||isLoading.value)return; messages.value.push({role:'user',content:text});inputQuery.value='';isLoading.value=true;scroll()
  try{const history=messages.value.filter(item=>item!==welcome).slice(-12).map(item=>({role:item.role==='ai'?'assistant':'user',content:item.content}));const response=await fetch(`${API_BASE}/api/ask`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:text,history})});if(!response.ok)throw new Error('服务暂不可用');const reader=response.body.getReader();const decoder=new TextDecoder();const index=messages.value.push({role:'ai',content:''})-1;while(true){const{value,done}=await reader.read();if(done)break;messages.value[index].content+=decoder.decode(value,{stream:true});scroll()}}
  catch{messages.value.push({role:'ai',content:'当前无法连接本地模型服务。你仍可继续整理案件和生成文书；启动后端与 Ollama 后再重试。'})}finally{isLoading.value=false;save();scroll()}
}
onMounted(()=>{try{messages.value=JSON.parse(localStorage.getItem('labourlawyer.chat.v1'))||[welcome]}catch{messages.value=[welcome]}});watch(messages,save,{deep:true})
</script>
<style scoped>
.assistant-panel{position:fixed;inset:16px 16px 16px auto;z-index:90;width:min(460px,calc(100vw - 32px));display:flex;flex-direction:column;border:1px solid var(--ll-border);border-radius:16px;background:var(--ll-surface);box-shadow:0 24px 80px #122d3233;overflow:hidden}.assistant-mask{position:fixed;inset:0;z-index:80;background:#122d3266}header{padding:16px;display:flex;align-items:center;justify-content:space-between;gap:12px;color:#fff;background:var(--ll-primary);min-height:80px}.assistant-identity{display:flex;align-items:center;gap:12px}.assistant-identity>span{width:40px;height:40px;display:grid;place-items:center;background:#ffffff18;border-radius:8px}.assistant-identity strong{display:block;font-size:16px}.assistant-identity small{display:block;margin-top:4px;font-size:12px;color:#e0eee8}.header-actions{display:flex;gap:4px}.header-actions button{width:44px;height:44px;border:0;border-radius:8px;color:#fff;background:transparent}.header-actions button:hover{background:#ffffff20}.header-actions .digital-entry{display:flex;align-items:center;gap:6px;width:auto;padding:8px;font-size:12px;background:#ffffff18}.header-actions .digital-entry span{font-size:12px}.assistant-context{padding:12px 16px;color:var(--ll-warning);background:var(--ll-gold-soft);font-size:12px;line-height:1.75}.chat-stream{flex:1;min-height:0;overflow:auto;padding:20px 16px;background:var(--ll-background)}.message{display:flex;gap:8px;margin-bottom:20px;min-width:0}.message>div{min-width:0}.message.user{justify-content:flex-end}.message.user>div{max-width:88%}.message small{display:block;margin-bottom:6px;font-size:12px;color:var(--ll-secondary)}.message.user small{text-align:right}.assistant-avatar{display:grid;place-items:center;flex:0 0 32px;height:32px;background:var(--ll-primary);color:#fff;border-radius:8px;font-family:serif}.bubble{border:1px solid var(--ll-border);background:#fff;border-radius:2px 12px 12px;padding:14px;color:var(--ll-text);font-size:15px;line-height:1.8;overflow-wrap:anywhere}.user .bubble{color:#fff;background:var(--ll-primary);border-color:var(--ll-primary);border-radius:12px 2px 12px 12px}.bubble :deep(p){margin:0 0 12px}.bubble :deep(p:last-child){margin-bottom:0}.bubble :deep(ul),.bubble :deep(ol){padding-left:20px}.typing{display:flex;gap:8px}.typing i{width:8px;height:8px;border-radius:50%;background:var(--ll-primary);animation:pulse 1s infinite alternate}.typing i:nth-child(2){animation-delay:.2s}.typing i:nth-child(3){animation-delay:.4s}.suggestions{padding:0 16px 12px;display:flex;flex-wrap:wrap;gap:8px;background:var(--ll-background)}.suggestions button{border:1px solid var(--ll-border-strong);border-radius:8px;padding:10px 12px;min-height:44px;background:#fff;color:var(--ll-primary);font-size:13px;text-align:left;white-space:normal}form{padding:16px;border-top:1px solid var(--ll-border);background:#fff}.assistant-input-label{display:block;color:var(--ll-text);font-size:14px;font-weight:650;margin-bottom:8px}textarea{border:1px solid var(--ll-border-strong);border-radius:8px;padding:12px;width:100%;resize:none;color:var(--ll-text);font-size:16px;line-height:1.65}textarea::placeholder{color:var(--ll-secondary)}form>div{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:8px}form span{font-size:12px;color:var(--ll-secondary)}form button{width:44px;height:44px;flex:0 0 44px;border:0;border-radius:8px;background:var(--ll-primary);color:#fff}form button:disabled{opacity:.45}.panel-enter-active,.panel-leave-active{transition:transform 180ms,opacity 180ms}.panel-enter-from,.panel-leave-to{transform:translateX(20px);opacity:0}.fade-enter-active,.fade-leave-active{transition:opacity 160ms}.fade-enter-from,.fade-leave-to{opacity:0}.sr-only{position:absolute;width:1px;height:1px;padding:0;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap}@keyframes pulse{to{opacity:.4}}
@media(max-width:560px){.assistant-panel{inset:0;width:100%;height:100dvh;border-radius:0}.assistant-identity>span{display:none}.assistant-identity strong{font-size:15px}.assistant-identity small{font-size:11px}header{padding:12px;gap:8px}.header-actions .digital-entry{padding:8px 6px}.assistant-context{font-size:12px}.assistant-panel form{padding-bottom:max(16px,env(safe-area-inset-bottom))}}
</style>
