<template>
  <header class="public-header">
    <a href="#main-content" class="skip-link">跳到主要内容</a>
    <div class="header-inner ll-container">
      <RouterLink to="/" class="public-brand" aria-label="LabourLawyer 首页"><BrandMark :size="32" /><span class="public-brand-name"><strong>LabourLawyer</strong><small>让劳动维权更简单</small></span></RouterLink>
      <button class="nav-toggle" :aria-expanded="menuOpen" aria-controls="public-navigation" @click="menuOpen=!menuOpen"><i :class="menuOpen?'fa-solid fa-xmark':'fa-solid fa-bars'" aria-hidden="true"></i><span>{{ menuOpen?'关闭':'菜单' }}</span></button>
      <nav id="public-navigation" :class="{expanded:menuOpen}" aria-label="网站导航"><RouterLink to="/#provinces" :class="{current:route.path==='/'&&!['#process','#faq'].includes(route.hash)}" @click="menuOpen=false">选择省份</RouterLink><RouterLink to="/#process" :class="{current:route.hash==='#process'}" @click="menuOpen=false">申请流程</RouterLink><RouterLink to="/#faq" :class="{current:route.hash==='#faq'}" @click="menuOpen=false">常见问题</RouterLink><RouterLink to="/admin" class="admin-entry" @click="menuOpen=false"><i class="fa-regular fa-user" aria-hidden="true"></i> 管理后台</RouterLink></nav>
    </div>
  </header>
</template>
<script setup>
import { ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import BrandMark from './BrandMark.vue'
const menuOpen=ref(false),route=useRoute()
watch(()=>route.fullPath,()=>{menuOpen.value=false})
</script>
<style scoped>
.public-header{position:sticky;top:0;z-index:40;background:var(--ll-surface);border-bottom:1px solid var(--ll-border)}.header-inner{display:flex;align-items:center;justify-content:space-between;min-height:80px;gap:24px}.public-brand{display:flex;align-items:center;gap:12px;min-height:44px;flex-shrink:0}.public-brand-name{min-width:0}.public-brand strong,.public-brand small{display:block}.public-brand strong{font-size:20px;letter-spacing:-.4px;color:var(--ll-text)}.public-brand small{font-size:12px;color:var(--ll-secondary);margin-top:2px}.public-header nav{display:flex;align-items:center;gap:32px}.public-header nav a{display:inline-flex;align-items:center;min-height:44px;gap:8px;color:var(--ll-secondary);font-size:14px;position:relative}.public-header nav a:hover,.public-header nav a.current{color:var(--ll-primary)}.public-header nav a.current:after{content:'';position:absolute;bottom:0;left:0;right:0;height:2px;background:var(--ll-primary)}.public-header nav .admin-entry{border-left:1px solid var(--ll-border);padding-left:24px;font-size:13px}.nav-toggle{display:none;min-height:44px;border:1px solid var(--ll-border-strong);border-radius:8px;background:var(--ll-surface);color:var(--ll-primary);padding:8px 12px;gap:8px;font-size:14px}
@media(max-width:700px){.header-inner{min-height:72px;gap:12px}.public-brand strong{font-size:18px}.public-brand small{font-size:11px}.public-brand{gap:8px}.nav-toggle{display:flex;align-items:center}.public-header nav{display:none;position:absolute;top:100%;left:0;right:0;padding:12px 20px;background:var(--ll-surface);border-bottom:1px solid var(--ll-border);box-shadow:var(--ll-shadow);gap:4px}.public-header nav.expanded{display:grid}.public-header nav a{padding:8px 12px}.public-header nav a.current:after{display:none}.public-header nav .admin-entry{border-left:0;border-top:1px solid var(--ll-border);padding-left:12px;margin-top:8px}}
</style>
