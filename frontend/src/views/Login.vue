<template>
  <main id="main-content" class="login-page" tabindex="-1">
    <section class="login-intro"><BrandMark :size="48"/><p class="eyebrow">LabourLawyer · 管理入口</p><h1>登录你的工作区</h1><p>管理案件和核验官方资料。每个账号只能查看自己保存的案件。</p><RouterLink to="/">只想填写文书？返回首页直接开始 <span aria-hidden="true">→</span></RouterLink></section>
    <form class="login-form" @submit.prevent="submit">
      <h2>账号登录</h2><p v-if="route.query.logout==='local-only'" role="status" class="hint">本机登录已退出。网络中断，服务端尚未确认撤销；原会话最迟8小时后失效。公共设备使用后请关闭页面。</p><p class="hint">账号由管理员开通。没有默认账号或通用密码。</p>
      <label for="username">账号</label><input id="username" v-model="username" autocomplete="username" required maxlength="64" :disabled="busy"/>
      <label for="password">密码</label><input id="password" v-model="password" type="password" autocomplete="current-password" required maxlength="128" :disabled="busy"/>
      <p v-if="error" role="alert" class="error">{{error}}</p>
      <button :disabled="busy" type="submit">{{busy?'正在登录…':'登录'}}</button>
      <p class="hint">登录状态仅保存在当前标签页，8小时后失效。公共电脑使用后请退出登录。</p>
      <details><summary>首次使用如何开通账号？</summary><p>由本机维护人员运行账号管理命令创建首位管理员；已有案件不会自动归到新账号。</p></details>
    </form>
  </main>
</template>
<script setup lang="ts">
import {ref,onBeforeUnmount} from 'vue'
import {RouterLink,useRoute,useRouter} from 'vue-router'
import BrandMark from '@/components/BrandMark.vue'
import {login,currentUser,safeAdminPath,logout,cancelPendingLogin} from '@/api/auth'
const route=useRoute(),router=useRouter(),username=ref(''),password=ref(''),error=ref(''),busy=ref(false)
onBeforeUnmount(cancelPendingLogin)
async function submit(){
 if(busy.value)return;busy.value=true;error.value=''
 try{if(!await login(username.value,password.value))return;password.value='';if(currentUser.value?.role!=='admin'){await logout();error.value='此入口仅供管理员使用，请联系维护人员。';return}await router.replace(safeAdminPath(route.query.next))}
 catch(e){error.value=e instanceof Error?e.message:'暂时无法登录，请重试'}finally{busy.value=false}
}
</script>
<style scoped>
.login-page{max-width:1040px;margin:0 auto;padding:76px 24px 100px;display:grid;grid-template-columns:1fr 1fr;gap:80px;align-items:center}.eyebrow{font-size:12px;color:var(--ll-primary);margin-top:24px}.login-intro h1{font-size:32px;line-height:1.4;color:var(--ll-text);margin:12px 0}.login-intro>p:not(.eyebrow){line-height:1.9;color:var(--ll-secondary)}.login-intro a{display:inline-block;margin-top:24px;color:var(--ll-primary);line-height:1.8}.login-form{padding:32px;border:1px solid var(--ll-border);border-radius:16px;background:var(--ll-surface)}h2{font-size:22px;margin:0 0 10px}.hint,details p{font-size:13px;line-height:1.8;color:var(--ll-secondary)}label{display:block;font-size:14px;margin:24px 0 8px}input{width:100%;padding:12px 14px;border:1px solid var(--ll-border-strong);border-radius:8px;font:inherit}input:focus-visible{outline:3px solid #91ccc5;outline-offset:2px}button{margin:24px 0 8px;width:100%;min-height:48px;border:0;border-radius:8px;background:var(--ll-primary);color:white;font:inherit;font-weight:600}button:disabled{opacity:.65}.error{color:#a23627;background:#fff2ef;padding:12px;border-radius:8px;font-size:14px;line-height:1.7}details{font-size:13px;margin-top:18px;color:var(--ll-secondary)}summary{cursor:pointer;min-height:28px}@media(max-width:700px){.login-page{padding:32px 16px 48px;grid-template-columns:1fr;gap:28px}.login-intro h1{font-size:26px}.login-form{padding:24px}.login-intro a{margin-top:8px}}
</style>
