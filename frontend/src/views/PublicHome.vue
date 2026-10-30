<template>
  <main class="public-home" id="main-content" tabindex="-1">
    <section class="welcome-section ll-container">
      <div class="welcome-copy">
        <span class="ll-eyebrow"><i class="fa-solid fa-scale-balanced" aria-hidden="true"></i> 为每一位劳动者</span>
        <h1>准备劳动仲裁材料，<br><em>一步一步，清楚明白。</em></h1>
        <p>选择办理省份，按提示填写申请书、整理证据。<br class="desktop-break">让你的诉求，有条理地写下来。</p>
        <label class="province-search" for="province-query"><i class="fa-solid fa-magnifying-glass" aria-hidden="true"></i><input id="province-query" v-model="query" type="search" aria-label="搜索办理省份" placeholder="搜索办理省份，如浙江、广东" aria-describedby="province-search-help"><button v-if="query" type="button" @click="query=''" aria-label="清空省份搜索"><i class="fa-solid fa-xmark" aria-hidden="true"></i></button></label>
        <p class="location-help" id="province-search-help"><i class="fa-solid fa-location-dot" aria-hidden="true"></i> 一般选择实际工作地或公司所在地的省份。</p>
      </div>
      <ServiceIllustration />
    </section>
    <div class="journey-strip ll-container" aria-label="使用步骤"><span><b>01</b> 选择省份</span><i class="fa-solid fa-chevron-right" aria-hidden="true"></i><span><b>02</b> 填写并下载文书</span><i class="fa-solid fa-chevron-right" aria-hidden="true"></i><span><b>03</b> 按官方流程提交</span><small><i class="fa-solid fa-lock" aria-hidden="true"></i> 填写草稿保存在当前设备</small></div>

    <section class="province-section ll-container" id="provinces" aria-labelledby="province-title">
      <div class="ll-section-heading"><div><span class="ll-eyebrow">从这里开始</span><h2 id="province-title">{{ query.trim() ? '找到你的办理省份' : '你准备在哪个省份办理？' }}</h2></div><p>按当地模板填写，办理前核对适用地区。</p></div>
      <p v-if="query.trim()" class="search-count" role="status">找到 {{ filteredProvinces.length }} 个省份</p>
      <div v-if="query.trim() && !filteredProvinces.length" class="no-result"><i class="fa-solid fa-map-location-dot" aria-hidden="true"></i><h3>没有找到这个省份</h3><p>试试省份简称，例如“浙江”或“广东”。</p><button class="ll-button secondary" @click="query=''">查看全部省份</button></div>
      <div v-else class="province-grid" id="province-cards"><ProvinceCard v-for="item in visibleProvinces" :key="item.slug" :province="item" /></div>
      <button v-if="!query.trim()" type="button" class="all-provinces" :aria-expanded="showAllProvinces" aria-controls="province-cards" @click="showAllProvinces=!showAllProvinces"><span>{{ showAllProvinces ? '收起省份' : `查看全国 ${provinces.length} 个省份` }}</span><i class="fa-solid fa-chevron-down" aria-hidden="true"></i></button>
    </section>

    <section class="process-section" id="process"><div class="ll-container">
      <div class="ll-section-heading"><div><span class="ll-eyebrow">第一次办理也不用慌</span><h2>先了解，再动手准备</h2></div><p>各地细节不同，以官方办事指南为准。</p></div>
      <ol class="process-list"><li v-for="(item,index) in plainProcess" :key="item.title"><span class="process-number">{{ String(index+1).padStart(2,'0') }}</span><h3>{{ item.title }}</h3><p>{{ item.text }}</p></li></ol>
      <div class="deadline-warning"><i class="fa-regular fa-clock" aria-hidden="true"></i><div><strong>别忘了申请时间</strong><p>一般劳动争议的仲裁时效为一年。拖欠工资等情况有特别规则，不确定时可咨询当地仲裁委员会或拨打 12333。</p></div></div>
    </div></section>

    <section class="faq-section ll-container" id="faq"><div class="faq-intro"><span class="ll-eyebrow">把疑问说清楚</span><h2>你可能还想知道</h2><p>从选哪里办理，到准备哪些材料，<br>先看几个常见问题。</p><a class="hotline" href="tel:12333"><i class="fa-solid fa-headset" aria-hidden="true"></i><span>人社咨询热线<strong>12333</strong></span></a></div><div class="faq-list"><details v-for="item in faqs" :key="item.q"><summary>{{ item.q }}<i class="fa-solid fa-plus" aria-hidden="true"></i></summary><p>{{ item.a }}</p></details></div></section>
  </main>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ProvinceCard from '@/components/ProvinceCard.vue'
import ServiceIllustration from '@/components/ServiceIllustration.vue'
import { commonProcess, provinces } from '@/data/provinces'
import type {ProvinceDefinition} from '@/data/provinces'
const route=useRoute(), router=useRouter()
const query=ref(typeof route.query.q==='string'?route.query.q:'')
const showAllProvinces=ref(false)
watch(query,value=>{if(route.path==='/')router.replace({query:{...route.query,q:value.trim()||undefined},hash:route.hash})})
watch(()=>route.query.q,value=>{query.value=typeof value==='string'?value:''})
const plainProcess=commonProcess.map((item,index)=>({...item,title:['确认办理地点','准备好材料','提交申请','留意受理通知','调解或参加开庭'][index]||item.title,text:item.text.replaceAll('有管辖权的','负责受理的').replaceAll('补正','补充材料')}))
const featuredProvinces=computed(()=>['zhejiang','guangdong','jiangsu','beijing','shandong','sichuan'].map(slug=>provinces.find(item=>item.slug===slug)).filter((item):item is ProvinceDefinition=>item!==undefined))
const filteredProvinces=computed(()=>provinces.filter(item=>`${item.name}${item.shortName}`.includes(query.value.trim())))
const orderedProvinces=computed(()=>[...featuredProvinces.value,...provinces.filter(item=>!featuredProvinces.value.some(featured=>featured.slug===item.slug))])
const visibleProvinces=computed(()=>query.value.trim()?filteredProvinces.value:showAllProvinces.value?orderedProvinces.value:featuredProvinces.value)
const faqs=[
  {q:'应该向哪里的仲裁委员会申请？',a:'一般可向实际工作地或公司所在地的劳动人事争议仲裁委员会申请。两地不同的，可先查看当地官方指南或拨打 12333 咨询。'},
  {q:'没有劳动合同，还能申请仲裁吗？',a:'可以。工资流水、社保缴费记录、工牌、考勤、工作聊天记录等都可能帮助证明劳动关系。请保留原始材料。'},
  {q:'申请劳动仲裁收费吗？',a:'劳动争议仲裁不收费。委托律师、打印复印、鉴定等其他费用需按实际情况承担。'},
  {q:'网上提交以后多久知道是否受理？',a:'通常仲裁委员会在收到申请后五日内审查是否符合受理条件；材料不完整的，会通知补充。请留意当地平台和仲裁委员会的通知。'},
]
</script>

<style scoped>
.public-home{background:var(--ll-background);color:var(--ll-text)}.welcome-section{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);gap:48px;align-items:center;padding-top:56px;padding-bottom:40px}.welcome-copy h1{font-size:clamp(36px,3.8vw,52px);line-height:1.35;letter-spacing:-.035em;margin:16px 0 20px;font-weight:750}.welcome-copy h1 em{font-style:normal;color:var(--ll-primary)}.welcome-copy>p{font-size:17px;color:var(--ll-secondary);line-height:1.85;margin:0 0 24px}.province-search{display:flex;align-items:center;gap:12px;max-width:560px;background:var(--ll-surface);border:1px solid var(--ll-border-strong);border-radius:var(--ll-radius);padding:4px 8px 4px 20px;min-height:60px;box-shadow:var(--ll-shadow)}.province-search>i{color:var(--ll-primary)}.province-search:focus-within{outline:3px solid var(--ll-focus);outline-offset:2px}.province-search input{min-width:0;flex:1;border:0;outline:none;background:transparent;color:var(--ll-text);padding:12px 0;font-size:16px}.province-search input::-webkit-search-cancel-button{display:none}.province-search button{width:44px;height:44px;border:0;border-radius:8px;background:var(--ll-wash);color:var(--ll-primary)}.welcome-copy .location-help{font-size:14px;margin:12px 0 0;display:flex;gap:8px;align-items:flex-start}.location-help i{margin-top:6px}.journey-strip{display:flex;align-items:center;gap:24px;padding-top:20px;padding-bottom:20px;border-top:1px solid var(--ll-border);border-bottom:1px solid var(--ll-border);font-size:14px}.journey-strip span{display:flex;align-items:center;gap:10px}.journey-strip b{font-size:12px;color:var(--ll-primary);font-variant-numeric:tabular-nums}.journey-strip>i{font-size:10px;color:var(--ll-secondary)}.journey-strip small{margin-left:auto;color:var(--ll-secondary);font-size:13px}.journey-strip small i{margin-right:6px}.province-section{padding-top:48px;padding-bottom:48px}.province-grid{display:grid;grid-auto-rows:1fr;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.search-count{color:var(--ll-secondary);font-size:14px}.all-provinces{display:flex;justify-content:center;align-items:center;gap:16px;width:100%;margin-top:24px;padding:16px;min-height:56px;border:1px solid var(--ll-border);border-radius:var(--ll-radius);background:var(--ll-surface);font-weight:650;color:var(--ll-primary);cursor:pointer}.all-provinces:hover{border-color:var(--ll-primary)}.all-provinces[aria-expanded="true"] i{transform:rotate(180deg)}.no-result{text-align:center;padding:40px 24px;border:1px dashed var(--ll-border-strong);border-radius:12px}.no-result>i{font-size:28px;color:var(--ll-primary)}.no-result h3{font-size:22px;margin:16px 0 8px}.no-result p{color:var(--ll-secondary)}.process-section{padding:48px 0;background:var(--ll-surface);border-block:1px solid var(--ll-border)}.process-list{list-style:none;display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:24px;margin:0;padding:0}.process-list li{padding-top:16px;border-top:2px solid var(--ll-border)}.process-number{color:var(--ll-primary);font-size:14px;font-weight:700}.process-list h3{font-size:18px;margin:16px 0 12px}.process-list p{font-size:14px;line-height:1.8;color:var(--ll-secondary);margin:0}.deadline-warning{margin-top:32px;display:flex;gap:16px;padding:20px 24px;border-radius:8px;background:var(--ll-gold-soft);color:var(--ll-warning)}.deadline-warning>i{margin-top:4px}.deadline-warning strong{font-size:15px}.deadline-warning p{margin:4px 0 0;font-size:14px;line-height:1.75}.faq-section{padding-top:56px;padding-bottom:56px;display:grid;grid-template-columns:1fr 1.7fr;gap:64px}.faq-intro h2{font-size:28px;margin:12px 0 16px}.faq-intro p{color:var(--ll-secondary);font-size:15px;line-height:1.8}.hotline{display:inline-flex;align-items:center;gap:12px;margin-top:16px;color:var(--ll-primary)}.hotline>i{font-size:24px}.hotline span{font-size:13px}.hotline strong{display:block;font-size:26px;letter-spacing:1px}.faq-list details{border-bottom:1px solid var(--ll-border)}.faq-list details:first-child{border-top:1px solid var(--ll-border)}.faq-list summary{display:flex;align-items:center;justify-content:space-between;gap:16px;min-height:72px;padding:20px 0;list-style:none;cursor:pointer;font-weight:650;font-size:16px}.faq-list summary i{font-size:12px;color:var(--ll-primary)}.faq-list details[open] summary i{transform:rotate(45deg)}.faq-list p{color:var(--ll-secondary);line-height:1.85;font-size:15px;margin:0 0 24px}
@media(max-width:1024px){.welcome-section{gap:24px}.journey-strip{gap:16px}.journey-strip small{display:none}.process-list{grid-template-columns:repeat(3,minmax(0,1fr))}.province-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.faq-section{gap:32px}}
@media(max-width:700px){.welcome-section{grid-template-columns:1fr;padding-top:32px;padding-bottom:24px;gap:0}.welcome-section :deep(.service-illustration){display:none}.welcome-copy h1{font-size:clamp(29px,7.8vw,40px)}.welcome-copy>p{font-size:16px}.desktop-break{display:none}.province-search{min-height:56px;padding-left:16px}.journey-strip{justify-content:space-between;gap:8px;font-size:12px}.journey-strip span{flex-direction:column;gap:4px;align-items:flex-start}.journey-strip b{font-size:12px}.province-section{padding-top:32px;padding-bottom:32px}.province-grid{grid-template-columns:1fr;gap:12px}.process-section{padding:32px 0}.process-list{grid-template-columns:1fr;gap:24px}.process-list li{display:grid;grid-template-columns:32px 1fr;column-gap:12px;padding-top:16px}.process-list h3{margin:0 0 8px}.process-list p{grid-column:2}.deadline-warning{padding:16px}.faq-section{grid-template-columns:1fr;gap:24px;padding-block:32px}.faq-intro p br{display:none}.hotline{margin-top:0}}
</style>
