<template>
  <main v-if="province" class="province-page" id="main-content" tabindex="-1" :style="palette">
    <section class="hero"><div class="hero-inner"><div>
      <nav aria-label="当前位置"><RouterLink to="/">选择省份</RouterLink> / {{ province.name }}</nav>
      <span class="eyebrow">劳动仲裁办事指南</span>
      <h1>{{ province.name }}劳动仲裁</h1><p>先看办理地区，再准备材料。一步一步来。</p>
      <a class="portal-button" :href="officialLink" target="_blank" rel="noopener noreferrer">打开官方办事指南 ↗</a>
    </div><figure><img :src="theme.art" alt="" width="380" height="260"></figure></div></section>
    <section class="documents-panel"><span class="eyebrow">填写文书</span><h2>选择要填写的文书</h2><p>当前表格适用于：<strong>{{ province.scope }}</strong>。填完核对信息，打印后本人手写签名。</p><p>在其他地区办理？先查看当地的官方表格。</p>
      <div class="document-options">
        <RouterLink v-if="province.applicationRoute" :to="province.applicationRoute"><i aria-hidden="true" class="fa-regular fa-file-word"></i><span><strong>仲裁申请书</strong><small>写你的要求和事情经过</small></span><b>开始填写 →</b></RouterLink><p v-else>暂时不能在线填写申请书，请下载官方表格。</p>
        <RouterLink v-if="province.evidenceRoute" :to="province.evidenceRoute"><i aria-hidden="true" class="fa-solid fa-list-check"></i><span><strong>证据清单</strong><small>列出材料，以及能证明什么</small></span><b>开始填写 →</b></RouterLink><p v-else>暂时不能在线填写证据清单，请按官方要求准备。</p>
      </div><details><summary>查看表格来源</summary><p>{{ province.authority }} · {{ province.scope }}</p><a :href="province.officialUrl" target="_blank" rel="noopener noreferrer">打开官方来源 ↗</a></details>
    </section>
    <section class="source-strip">
      <div><span>这份指南的办理地区</span><strong>{{ experience.scope || '官方页面未标明地区' }}</strong></div>
      <div><span>这个入口办理什么</span><strong>{{ serviceLabel }}</strong></div>
      <div><span>信息记录时间</span><strong>{{ (experience.captured_at || '').slice(0,10) || '尚未确认' }}</strong></div>
      <p v-if="experience.state !== 'fresh'">{{ experience.state === 'historical' ? '这是之前查到的信息，请打开官网确认有没有变化。' : '还没查到具体步骤，请先打开官网。' }}</p>
      <p v-if="!experience.capital_confirmed">先查{{ experience.preferred_city }}。不同地区的要求可能不同。</p>
    </section>
    <section class="how-to"><div class="steps-panel">
      <span class="eyebrow">先做什么</span><h2>{{ experience.service_kind === 'mediation' ? '先了解调解怎么办理' : '按这几步准备' }}</h2>
      <ol class="steps"><li v-for="(step,index) in experience.steps" :key="index"><b>{{ index+1 }}</b><div><h3>{{ step.title }}</h3><p>{{ step.text }}</p></div></li></ol>
      <a :href="officialLink" target="_blank" rel="noopener noreferrer">不清楚？打开官方指南查看 ↗</a>
    </div><aside>
      <div class="materials-panel"><span class="eyebrow">带什么</span><h2>材料先准备好</h2><ul v-if="experience.materials?.length"><li v-for="item in experience.materials" :key="item">{{ item }}</li></ul><p>要带哪些材料、各带几份？请看官网的“申请材料”。</p>
        <div v-if="templateLinks.length" class="downloads"><strong>该官方入口的表格</strong><a v-for="(item,index) in templateLinks" :key="index" :href="item.url" target="_blank" rel="noopener noreferrer">{{ item.name }} <small>{{ item.kind==='sample' ? '样例' : item.kind==='blank' ? '空白表格' : '查看下载区域' }}</small> ↗</a><p>样例用来参考，请先查看是否另有空白表格。</p></div>
      </div><div class="notes-panel"><span class="eyebrow">注意什么</span><h2>这几件事别漏了</h2><ul><li v-for="note in experience.notes" :key="note">{{ note }}</li></ul></div>
    </aside></section>
    <details class="more-guides"><summary>换个地区？查看其他地区的指南</summary><DistrictWorkflow :slug="province.slug" /></details>
    <footer>请在政府网站提交材料。签名请本人手写。</footer>
  </main><main v-else class="empty"><h1>暂未找到该省份</h1><RouterLink to="/">返回选择省份</RouterLink></main>
</template>
<script setup lang="ts">
import { computed, ref, watch, onBeforeUnmount } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import {publicClient} from '@/api/public'
import {readExperience} from '@/data/regionalGuidePresentation'
import type {ProvinceExperience} from '@/data/regionalGuidePresentation'
import DistrictWorkflow from '@/components/DistrictWorkflow.vue'
import { findProvince } from '@/data/provinces'
import snapshot from '@/data/provinceExperiences.json'
import themes from '../../../config/province_themes.json'
const route=useRoute(), live=ref<ProvinceExperience|null>(null)
const slug=computed(()=>typeof route.params.slug==='string'?route.params.slug:'')
const province=computed(()=>findProvince(slug.value))
const experienceSnapshots:Record<string,unknown>=snapshot.provinces,themeCatalog:Record<string,typeof themes.zhejiang>=themes
const experience=computed(()=>live.value || readExperience(experienceSnapshots[slug.value] || {slug:slug.value,steps:[]},slug.value))
const theme=computed(()=>themeCatalog[slug.value] || themes.zhejiang)
const palette=computed(()=>({'--accent':theme.value.accent,'--wash':theme.value.wash}))
const officialLink=computed(()=>experience.value.source_url || experience.value.portal_url || province.value?.officialUrl)
const serviceLabel=computed(()=>experience.value.service_kind==='mediation' ? '劳动争议调解（不是仲裁申请）' : experience.value.service_kind==='arbitration' ? '劳动人事争议仲裁申请' : '请在官方入口查询')
const templateLinks=computed(()=>(experience.value.templates || []).map(t=>({name:t.material_name || t.text || '查看文书表格',kind:t.kind,url:t.url || officialLink.value})).filter(t=>/^https?:\/\//.test(t.url || '')))
let version=0,controller:AbortController|undefined,timer:ReturnType<typeof setTimeout>|undefined
watch(slug,async selected=>{
  const request=++version;clearTimeout(timer);controller?.abort();live.value=null
  if(!findProvince(selected))return
  const own=new AbortController();controller=own
  const timeout=setTimeout(()=>own.abort(),15000);timer=timeout
  try{
    const data=await publicClient.experience(selected,own.signal)
    if(request===version&&!own.signal.aborted)live.value=data
  }catch{}finally{clearTimeout(timeout)}
},{immediate:true,flush:'sync'})
onBeforeUnmount(()=>{++version;clearTimeout(timer);controller?.abort()})
</script>
<style scoped>
.province-page{background:var(--ll-background);color:var(--ll-text);padding-bottom:40px}.province-page a{color:var(--ll-primary)}.hero{background:var(--ll-wash);border-bottom:1px solid var(--ll-border)}.hero-inner{max-width:1224px;margin:auto;padding:24px 32px 32px;display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:32px;align-items:center}.hero nav{font-size:14px;color:var(--ll-secondary);margin-bottom:24px;min-height:32px}.hero nav a{display:inline-flex;align-items:center;min-height:36px}.eyebrow{color:var(--ll-primary);font-size:13px;font-weight:650}.hero h1{font-size:40px;margin:12px 0;line-height:1.4;font-weight:700;letter-spacing:-.03em}.hero p{font-size:16px;margin:0;line-height:1.8;color:var(--ll-secondary)}.portal-button{display:inline-flex;align-items:center;min-height:44px;padding:8px 0;margin-top:12px;font-size:14px;font-weight:650;text-decoration:underline;text-underline-offset:5px}.hero figure{margin:0}.hero img{width:100%;height:auto;max-height:210px;object-fit:contain}
.documents-panel{max-width:1160px;margin:32px auto 24px;padding:28px;background:var(--ll-surface);border:1px solid var(--ll-border);border-radius:12px}.documents-panel h2{font-size:26px;margin:8px 0 12px}.documents-panel>p{font-size:14px;color:var(--ll-secondary);line-height:1.8;margin:4px 0}.document-options{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:24px 0}.document-options a{display:flex;gap:16px;align-items:center;padding:24px;border:1px solid var(--ll-border-strong);border-radius:8px;background:var(--ll-wash)}.document-options a:hover{border-color:var(--ll-primary);box-shadow:var(--ll-shadow)}.document-options i{font-size:28px;color:var(--ll-primary)}.document-options span{flex:1;min-width:0}.document-options strong{display:block;font-size:20px;color:var(--ll-text)}.document-options small{display:block;font-size:14px;color:var(--ll-secondary);margin-top:4px}.document-options b{font-size:14px;color:var(--ll-primary);white-space:nowrap}
.source-strip{max-width:1160px;margin:24px auto;display:grid;grid-template-columns:1fr 1.4fr 1fr;gap:20px;padding:20px 24px;border:1px solid var(--ll-border);border-radius:8px;background:var(--ll-surface)}.source-strip span{display:block;color:var(--ll-secondary);font-size:13px;margin-bottom:4px}.source-strip strong{font-size:14px}.source-strip p{grid-column:1/-1;margin:0;font-size:13px;color:var(--ll-secondary);line-height:1.8}
.how-to{max-width:1224px;margin:auto;padding:0 32px 24px;display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:24px;align-items:start}.how-to h2{font-size:24px;margin:8px 0 24px}.how-to h3{font-size:18px;margin:0 0 8px}.how-to p,.how-to li{font-size:15px;line-height:1.85;color:var(--ll-secondary);overflow-wrap:anywhere}.steps-panel,.materials-panel,.notes-panel{padding:28px;border:1px solid var(--ll-border);border-radius:12px;background:var(--ll-surface)}.steps{list-style:none;padding:0;margin:0 0 24px}.steps li{display:flex;gap:16px;padding:20px 0;border-top:1px solid var(--ll-border)}.steps li>b{width:32px;height:32px;flex:0 0 32px;display:grid;place-items:center;color:var(--ll-primary);background:var(--ll-wash);border-radius:8px;font-size:13px}.steps p{margin:0 0 8px}.steps li>div{min-width:0}.steps-panel>a{font-size:14px;text-decoration:underline}.how-to ul{padding-left:20px}.how-to ul li{padding-bottom:12px}.notes-panel{margin-top:24px;background:var(--ll-gold-soft)}.notes-panel .eyebrow{color:var(--ll-warning)}.downloads{border-top:1px solid var(--ll-border);padding-top:20px}.downloads strong{display:block;font-size:15px}.downloads a{display:block;padding:12px 0;font-size:14px;text-decoration:underline;overflow-wrap:anywhere}.downloads small{font-size:12px;color:var(--ll-secondary)}.downloads p{font-size:13px}
.province-page details{font-size:14px}.province-page summary{min-height:44px;padding:8px 0;cursor:pointer;color:var(--ll-primary)}.province-page details p{font-size:14px;color:var(--ll-secondary);white-space:pre-wrap;line-height:1.8}.more-guides{max-width:1160px;margin:auto;border-top:1px solid var(--ll-border);padding-top:16px}.province-page>footer{max-width:1160px;margin:24px auto 0;color:var(--ll-secondary);font-size:13px}.empty{padding:80px 24px;text-align:center}
@media(max-width:1224px){.documents-panel,.source-strip,.more-guides,.province-page>footer{margin-left:32px;margin-right:32px}}
@media(max-width:1000px){.how-to{grid-template-columns:1fr}.how-to aside{display:grid;grid-template-columns:1fr 1fr;gap:20px}.notes-panel{margin-top:0}.document-options a{flex-wrap:wrap}.document-options b{width:100%;padding-left:44px}}
@media(max-width:700px){.hero-inner{padding:20px 16px 24px;grid-template-columns:1fr}.hero figure{display:none}.hero h1{font-size:30px}.hero nav{margin-bottom:20px}.documents-panel,.source-strip,.more-guides,.province-page>footer{margin-left:16px;margin-right:16px}.documents-panel{padding:20px 16px;margin-top:24px}.documents-panel h2{font-size:23px}.document-options{grid-template-columns:1fr}.document-options a{padding:20px}.document-options b{padding-left:44px}.source-strip{grid-template-columns:1fr;padding:20px;gap:16px}.how-to{padding:0 16px 24px}.steps-panel,.materials-panel,.notes-panel{padding:20px 16px}.how-to aside{grid-template-columns:1fr}.how-to h2{font-size:22px}}
</style>
