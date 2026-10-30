<template>
 <main id="main-content" class="connection-page" tabindex="-1">
  <p class="ll-eyebrow">连接设置</p><h1>连接你的服务</h1><p>手机和电脑可以连接同一个已部署服务，不必一直通过USB转发。</p>
  <form @submit.prevent="test"><label for="api-address">文书与AI服务地址</label><input id="api-address" v-model="api" type="url" placeholder="https://你的服务域名" required autocomplete="url"/><p class="hint">公网使用HTTPS；局域网预览可以填写服务器的私有IP和端口。地址由服务维护人员提供。</p><label for="digital-address">数字人服务地址（可选）</label><input id="digital-address" v-model="digital" type="url" placeholder="https://数字人服务域名"/><p class="hint">数字人需要另行部署。留空使用本安装包原有配置。</p><p v-if="message" role="status">{{message}}</p><p v-if="error" role="alert">{{error}}</p><div class="actions"><button class="ll-button secondary" :disabled="testing" type="submit">{{testing?'正在检查…':'检查连接'}}</button><button class="ll-button" type="button" :disabled="!verified||testing" @click="save">保存并使用</button><button class="ll-button secondary" type="button" @click="restore">恢复默认</button></div><p class="hint">切换服务将退出当前账号。以后主动生成文书或提问时，内容会发送到你填写的服务；请只连接自己信任的地址。</p></form>
 </main>
</template>
<script setup lang="ts">
import {ref,watch} from 'vue'
import {normalizeServiceAddress} from '../../../packages/client-contracts/src/index.ts'
import {savedConnection,saveConnection,clearConnection} from '@/api/connection'
import {authSession} from '@/api/authSession'
const current=savedConnection(),api=ref(current?.api||''),digital=ref(current?.digital||''),message=ref(''),error=ref(''),testing=ref(false),verified=ref(false)
watch([api,digital],()=>{verified.value=false;message.value='';error.value=''})
async function test(){
 testing.value=true;error.value='';message.value='';verified.value=false
 const selected=api.value,avatar=digital.value
 try{const base=normalizeServiceAddress(selected);if(avatar)normalizeServiceAddress(avatar);const r=await fetch(base+'/health',{signal:AbortSignal.timeout(10000),cache:'no-store'});const data:unknown=await r.json();if(!r.ok||!data||typeof data!=='object'||!('service' in data)||data.service!=='api')throw Error('此地址没有返回本项目的服务状态');if(selected!==api.value||avatar!==digital.value)return;verified.value=true;message.value='服务已响应。请确认地址可信，再保存。'}catch(e){error.value=e instanceof Error?e.message:'暂时无法连接服务'}finally{testing.value=false}
}
function save(){if(!verified.value)return;try{saveConnection({api:api.value,digital:digital.value});authSession.clear();location.assign('/')}catch{error.value='设置未保存，请检查地址和浏览器存储权限。'}}
function restore(){try{clearConnection();authSession.clear();location.assign('/')}catch{error.value='暂时无法清除设置。'}}
</script>
<style scoped>
.connection-page{max-width:760px;margin:0 auto;padding:48px 24px 80px}.connection-page h1{font-size:30px;color:var(--ll-text)}.connection-page>p{line-height:1.8;color:var(--ll-secondary)}form{padding:28px;border:1px solid var(--ll-border);border-radius:14px;background:var(--ll-surface);margin-top:28px}label{display:block;margin:20px 0 10px;font-size:15px;font-weight:600}input{width:100%;padding:12px;border:1px solid var(--ll-border-strong);border-radius:8px;font:inherit}.hint{font-size:13px;line-height:1.8;color:var(--ll-secondary)}.actions{display:flex;gap:12px;flex-wrap:wrap;margin:24px 0}.connection-page [role=alert]{color:#9b3427}.connection-page [role=status]{color:var(--ll-primary)}@media(max-width:600px){.connection-page{padding:28px 16px 48px}form{padding:20px}.actions>button{width:100%}}
</style>
