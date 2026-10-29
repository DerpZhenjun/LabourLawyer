<template>
  <div class="regional-page collection-page">
    <header class="region-heading"><div><span class="ll-eyebrow">公开指南核验 · 独立数据库</span><h1>地区采集与问题记录</h1><p>具体区县的核验范围与省级历史模板分开统计，不把样本当全国覆盖。</p></div><button class="ll-button secondary" @click="refreshAll" :disabled="loading">{{ loading?'正在读取…':'刷新报告' }}</button></header>
    <p class="region-notice">这是本地公开采集信息查看页，无管理写入权限。生产部署仍需为管理后台配置身份认证；本页不展示个人文书。</p>
    <p v-if="error" role="alert" class="region-notice danger">{{ error }}</p>
<section v-if="report" class="region-panel"><h2>OpenClaw 实际状态</h2><p>{{ report.openclaw.status==='ACKNOWLEDGED_OPENCLAW'?'已收到完整事件编号确认':'问题记录已保存，等待 OpenClaw 确认' }}</p><p>投递状态：{{ report.openclaw.status }}</p><p>等待确认 {{ report.openclaw.pending_count }} 条。</p><p>最近调用：{{ report.openclaw.attempted_at || '尚未调用' }}</p><p v-if="report.openclaw.status==='PENDING_OPENCLAW'">目前没有完整事件编号确认，不能把本地报告称为 OpenClaw 已接收。页面不会自动调用模型。手动重新同步命令：<code>python scripts/sync-regional-openclaw.py --timeout 45</code></p><button class="ll-button secondary" @click="exportReport">导出公开问题报告</button></section>
    <section v-if="report?.cross_province_checks?.length" class="region-panel"><h2>跨省来源复核（不计入区县覆盖）</h2><article v-for="s in report.cross_province_checks" :key="s.source_id" class="regional-material"><h3>浙江省级事项页面 · 部分核对</h3><p>{{ s.limitation }}</p><p>实施主体：{{ s.raw_fields['实施主体'] }} · 承诺时限：{{ s.raw_fields['承诺办结时限'] }} · {{ s.material_requirement }}</p><p>网上入口要求官网登录；未提交申请。核验：{{ s.verified_at }}</p><a :href="s.source_url" target="_blank" rel="noopener noreferrer" class="ll-button secondary">查看实际官方来源 ↗</a></article></section>
    <RegionalRollout ref="rollout" />
    <RegionalVerification />
    <section class="region-panel"><h2>已采集地区</h2><article v-for="g in report?.regions||[]" :key="g.region_id" class="regional-material"><h3>{{ g.province_name }} / {{ g.city }} / {{ g.district }}</h3><p>{{ g.authority }} · {{ g.service_name }}</p><p>办理形式：{{ g.channel.raw_value }} · 网办状态：{{ channelLabels[g.channel.online_status]||'待核实' }} · 附件 {{ g.templates.length }} 个</p><p>源 ID：<code>{{ g.source_id }}</code> · 核验 {{ g.verified_at }}</p><div class="region-actions"><RouterLink :to="{path:`/province/${g.province}`,query:{city:g.city,district:g.district}}" class="ll-button secondary">查看地区页面</RouterLink><a :href="g.source_url" target="_blank" rel="noopener noreferrer" class="ll-button secondary">核对官方来源 ↗</a><button class="ll-button secondary" @click="showVersions(g)">查看版本记录</button></div><div v-if="versions[g.region_id]"><p v-for="v in versions[g.region_id]" :key="v.content_hash" class="file-hash">{{ v.verified_at }} · 内容 SHA256：{{ v.content_hash }}</p></div></article></section>
    <section v-if="report" class="region-panel"><h2>可追溯的问题报告</h2><details v-for="(events,name) in report.categories" :key="name" class="original-section"><summary>{{ name }} · {{ events.length }} 条</summary><p v-if="!events.length">本次没有记录此类事件，不代表全国不存在此类问题。</p><article v-for="e in events" :key="e.id" class="regional-material"><h3>{{ e.district || provinces.find(p=>p.slug===e.province)?.name || '公开事项搜索' }} · {{ e.type }}</h3><p>{{ e.reason }}</p><p>处理：{{ e.remediation }} · 尝试 {{ e.attempts }} 次</p><p>最终状态：{{ e.final_status }} · {{ e.delivery_status }}</p><p class="file-hash">事件 ID：{{ e.id }} · {{ e.occurred_at }}</p><div class="region-actions"><a v-if="e.url" :href="e.url" target="_blank" rel="noopener noreferrer" class="ll-button secondary">查看原始来源 ↗</a><a v-if="e.screenshot" :href="`${regionalAPI}/evidence/${e.screenshot}`" target="_blank" rel="noopener noreferrer" class="ll-button secondary">查看真实截图 ↗</a></div></article></details></section>
  </div>
</template>
<script setup>
import {ref,onMounted} from 'vue'
import {RouterLink} from 'vue-router'
import RegionalRollout from '@/components/RegionalRollout.vue'
import RegionalVerification from '@/components/RegionalVerification.vue'
import {provinces} from '@/data/provinces'
import {regionalAPI,regionQuery} from '@/composables/useRegionalGuide'
import '@/regional-guide.css'
const report=ref(null),loading=ref(false),error=ref(''),versions=ref({}),rollout=ref(null)
const channelLabels={unavailable:'仅窗口办理',auth_required:'官方网上入口要求登录',verified:'网上入口已核验',conflict:'来源冲突，待核实',unverified:'尚未核实'}
function refreshAll(){load();rollout.value?.refresh()}
async function load(){loading.value=true;error.value='';try{const r=await fetch(`${regionalAPI}/report`);if(!r.ok)throw new Error('无法读取报告，请确认后端已启动');report.value=await r.json()}catch(e){error.value=e.message}finally{loading.value=false}}
async function showVersions(g){try{const r=await fetch(`${regionalAPI}/versions?${regionQuery(g)}`);if(!r.ok)throw new Error('版本读取失败');versions.value[g.region_id]=(await r.json()).items}catch(e){error.value=e.message}}
function exportReport(){const blob=new Blob([JSON.stringify(report.value,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='地区指南-公开问题报告.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
onMounted(load)
</script>
<style scoped>.collection-page{padding:28px;max-width:1200px}.coverage-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.coverage-item{display:grid;gap:8px;background:var(--ll-background);border:1px solid var(--ll-border);padding:18px;border-radius:10px}.coverage-item span{color:var(--ll-secondary);font-size:14px}.coverage-item a{color:var(--ll-primary);min-height:44px;padding-top:8px}.collection-page code{overflow-wrap:anywhere;color:var(--ll-primary)}@media(max-width:800px){.coverage-grid{grid-template-columns:1fr 1fr}.collection-page{padding:18px}}@media(max-width:500px){.coverage-grid{grid-template-columns:1fr}.collection-page{padding:12px}}</style>
