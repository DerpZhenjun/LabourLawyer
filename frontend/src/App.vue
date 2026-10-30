<template>
  <div v-if="isAdmin" class="app-shell">
    <aside class="sidebar" :class="{ open: sidebarOpen }">
      <RouterLink class="brand" to="/admin"><BrandMark :size="36" /><span><strong>LabourLawyer</strong><small>管理后台</small></span></RouterLink>
      <nav class="main-nav" aria-label="后台导航">
        <RouterLink v-for="item in adminNav" :key="item.to" :to="item.to" @click="sidebarOpen=false"><i :class="item.icon"></i><span>{{item.label}}</span></RouterLink>
      </nav>
      <RouterLink to="/" class="back-public"><i class="fa-solid fa-arrow-left"></i> 返回群众服务首页</RouterLink>
      <button type="button" class="back-public" @click="signOut">退出登录</button><p v-if="logoutError" role="alert">{{logoutError}}</p><div class="org-switcher"><span class="org-avatar">PL</span><span><strong>{{currentUser?.username}}</strong><small>管理账号</small></span></div>
    </aside>
    <div v-if="sidebarOpen" class="sidebar-mask" @click="sidebarOpen=false"></div>
    <main class="main-stage" id="main-content" tabindex="-1">
      <header class="topbar">
        <div class="topbar-left"><button class="icon-button mobile-menu" aria-label="打开导航" @click="sidebarOpen=true"><i class="fa-solid fa-bars"></i></button><div><small>{{currentMeta.eyebrow}}</small><strong>{{currentMeta.title}}</strong></div></div>
        <div class="topbar-actions"><button class="primary-action" @click="go('/admin/cases?new=1')"><i class="fa-solid fa-plus"></i> 新建案件</button></div>
      </header>
      <RouterView :key="route.path+':'+(currentUser?.id??'anonymous')" />
    </main>
  </div>

  <div v-else class="public-site">
    <PublicHeader />
    <RouterView :key="route.path" />
    <footer class="public-footer">
      <div><div class="footer-brand"><BrandMark :size="32" /><div><strong>LabourLawyer</strong><small>劳动仲裁文书助手</small></div></div><p>帮助普通劳动者了解办理流程、准备申请文书和整理证据。</p></div>
      <div><strong>重要说明</strong><p>本平台提供文书和办事信息辅助，不替代律师法律意见。政务办理以当地仲裁委员会最新要求为准。</p></div>
      <div><strong>官方咨询</strong><p>人力资源和社会保障服务热线：<b>12333</b></p></div>
    </footer>
  </div>

  <button v-if="!assistantOpen && !digitalOpen" ref="assistantButton" class="assistant-fab" :style="assistantDock.style.value" :aria-hidden="assistantDock.hidden.value || undefined" @click="assistantOpen=true" aria-label="打开 AI 法律顾问"><BrandMark variant="assistant" :size="30" /><span>AI 法律顾问</span></button>
  <QA v-if="assistantOpen" :key="currentUser?.id??'anonymous'" :open="assistantOpen" @close="assistantOpen=false" @open-digital-human="openDigitalLawyer" />
  <DigitalLawyer v-if="digitalOpen" :key="currentUser?.id??'anonymous'" @close="digitalOpen=false" />
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, nextTick, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import BrandMark from '@/components/BrandMark.vue'
import {useAssistantDock} from '@/composables/useAssistantDock'
const DigitalLawyer = defineAsyncComponent(() => import('@/components/DigitalLawyer.vue'))
import {currentUser,logout} from '@/api/auth'
import PublicHeader from '@/components/PublicHeader.vue'
const QA = defineAsyncComponent(() => import('@/components/QA.vue'))

const route=useRoute();const router=useRouter();const sidebarOpen=ref(false);const assistantOpen=ref(false);const digitalOpen=ref(false)
const assistantButton=ref<HTMLElement|null>(null)
const assistantDock=useAssistantDock(assistantButton)
const isAdmin=computed(()=>route.meta.layout==='admin')
const currentMeta=computed(()=>({eyebrow:route.meta.eyebrow||'管理后台',title:route.meta.title||'LabourLawyer'}))
const adminNav=[
  {to:'/admin',label:'工作概览',icon:'fa-solid fa-table-cells-large'},
  {to:'/admin/cases',label:'案件管理',icon:'fa-solid fa-briefcase'},
  {to:'/admin/evidence',label:'证据管理',icon:'fa-solid fa-folder-tree'},
  {to:'/admin/documents',label:'模板管理',icon:'fa-regular fa-file-lines'},
  {to:'/admin/deadlines',label:'时效管理',icon:'fa-regular fa-calendar-check'},
  {to:'/admin/knowledge',label:'内容管理',icon:'fa-solid fa-book-open'},
  {to:'/admin/regions',label:'地区核验与问题',icon:'fa-solid fa-map-location-dot'},
  {to:'/admin/collector',label:'官方指南采集',icon:'fa-solid fa-globe'},
]
watch(currentUser,user=>{if(!user&&route.meta.layout==='admin')void router.replace({path:'/login',query:{next:route.fullPath}})})
watch(()=>currentUser.value?.id??'anonymous',()=>{assistantOpen.value=false;digitalOpen.value=false},{flush:'sync'})
const logoutError=ref('')
const signOut=async()=>{try{await logout();await router.replace('/login')}catch{await router.replace({path:'/login',query:{logout:'local-only'}})}}
const go=(path:string)=>router.push(path)
const openDigitalLawyer=()=>{assistantOpen.value=false;digitalOpen.value=true}
watch(()=>route.path,async()=>{await nextTick();document.querySelector<HTMLElement>('#main-content')?.focus({preventScroll:true})},{flush:'post'})
</script>

<style scoped>
.assistant-fab{display:inline-flex;align-items:center;gap:10px}
.back-public{margin-top:auto;padding:12px 13px;border:1px solid rgba(255,255,255,.1);border-radius:9px;color:#aebfd3;font-size:12px}.back-public i{margin-right:7px}.public-footer{max-width:1180px;margin:45px auto 0;padding:32px 24px 42px;display:grid;grid-template-columns:1.2fr 1.4fr .8fr;gap:50px;border-top:1px solid #e3e8eb;color:#6f7e8d}.public-footer>div>strong{color:#3d5064;font-size:13px}.public-footer p{margin:8px 0 0;font-size:12px;line-height:1.7}.public-footer b{color:#0f766e;font-size:16px}.footer-brand{display:flex;align-items:center;gap:9px}.footer-brand>span{width:32px;height:32px;display:grid;place-items:center;border-radius:8px;color:#fff;background:#16665f;font-family:serif}.footer-brand strong,.footer-brand small{display:block}.footer-brand strong{color:#273c51;font-size:14px}.footer-brand small{color:#8995a1;font-size:10px}@media(max-width:700px){.public-footer{margin-top:20px;padding:25px 16px 34px;grid-template-columns:1fr;gap:23px}}
</style>
