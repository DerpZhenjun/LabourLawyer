<template>
 <div class="collector-page">
  <header><div><span class="ll-eyebrow">公开资料 · 等待核验</span><h1>官方指南采集</h1><p>明确地区和官网链接，再加入持久队列。这里不处理个人案件，也不调用模型。</p></div><button type="button" class="ll-button secondary" :disabled="loading" @click="refresh">{{loading?'正在刷新…':'刷新状态'}}</button></header>
  <p class="collector-notice">网页访问成功、下载了附件，都不代表已经核验。核对受理机关、材料、空白表格和填写结果后，才能接入当地文书生成。</p>
  <p v-if="error" class="collector-notice danger" role="alert">{{error}}</p><p v-if="message" class="collector-notice" role="status">{{message}}</p>
  <div v-if="data" class="collector-state" aria-live="polite"><strong>{{data.worker?.alive?'执行器在线':'执行器未在线，任务将保留等待'}}</strong><span>等待 {{data.counts.queued}} · 正在访问 {{data.counts.running}} · 访问结束 {{data.counts.complete}} · 已取消 {{data.counts.cancelled}}</span></div>
  <section class="collector-panel"><h2>添加一条当地指南</h2><form @submit.prevent="add">
   <div class="collector-fields"><label>省份<select v-model="region.province" required><option v-for="p in provinces" :key="p.slug" :value="p.slug">{{p.name}}</option></select></label><label>城市<input v-model.trim="region.city" required maxlength="80" placeholder="例如：苏州市"/></label><label>区县或功能区<input v-model.trim="region.district" required maxlength="80" placeholder="例如：张家港市"/></label><label>已核对的地区代码<input v-model.trim="region.region_code" required pattern="[0-9]{6,12}" inputmode="numeric" maxlength="12" placeholder="例如：320582"/></label></div>
   <label>该地区的官方办事指南链接<input v-model.trim="url" type="url" required maxlength="3000" placeholder="粘贴这个地区自身的官方指南链接"/></label>
   <p class="collector-hint">只接收已配置政府站点。不会用省级或其他区县的资料代替，也不会自动提交仲裁申请。</p><p v-if="data?.allowed_hosts.length" class="collector-hint">当前站点范围：{{data.allowed_hosts.join('、')}}</p>
   <button class="ll-button" type="submit" :disabled="busy||!data">{{busy?'正在保存…':'加入采集队列'}}</button>
  </form></section>
  <section class="collector-panel"><h2>最近任务</h2><p v-if="!data&&!loading">采集环境尚未就绪时不会创建任务，请查看上方提示。</p><p v-else-if="data&&!data.items.length">还没有采集任务。添加明确地区的官网链接后，会在这里显示进度。</p>
   <ol class="collector-jobs"><li v-for="job in data?.items||[]" :key="job.id"><div class="collector-job-heading"><h3>{{job.region.city}} · {{job.region.district}}</h3><span>{{jobLabels[job.state]}}</span></div><p class="collector-hint">{{job.region.region_code}} · 尝试 {{job.attempt}} 次 · {{job.updated_at}}</p><a :href="job.url" target="_blank" rel="noopener noreferrer">核对本条官方来源 ↗</a><p v-if="job.result">{{observationLabels[job.result.state]}}。仍待核验，不计入已支持地区。</p><p v-if="job.result?.title" class="collector-hint">实际页面标题：{{job.result.title}}</p>
    <div class="collector-actions"><button v-if="job.state==='queued'" type="button" class="ll-button secondary" :disabled="busy" @click="action(job,'cancel')">取消等待</button><button v-if="job.state==='complete'&&job.attempt<2" type="button" class="ll-button secondary" :disabled="busy" @click="action(job,'retry')">重试一次</button><button v-for="item in job.result?.evidence||[]" :key="item.file" type="button" class="ll-button secondary" :disabled="busy" @click="download(job,item)">下载{{evidenceLabel(item.file)}}</button></div>
   </li></ol>
  </section>
 </div>
</template>
<script setup lang="ts">
import {reactive,ref} from 'vue'
import {provinces} from '@/data/provinces'
import {useOfficialCollector} from '@/composables/useOfficialCollector'
import type {CollectorRegion,CollectorJobState,ObservationState} from '../../../packages/client-contracts/src/collector.ts'
const {data,loading,busy,error,message,refresh,submit,action,download}=useOfficialCollector()
const url=ref(''),region=reactive<CollectorRegion>({province:'jiangsu',city:'',district:'',region_code:''})
const jobLabels:Record<CollectorJobState,string>={queued:'等待访问',running:'正在访问',complete:'访问已结束',cancelled:'已取消'}
const observationLabels:Record<ObservationState,string>={guide_observed:'已看到指南内容',blocked:'访问受到限制',auth_required:'需要官网登录，已停止',captcha_required:'需要验证码，已停止',network_failed:'官网访问未完成',runtime_failed:'执行器运行未完成',unverified:'本次资料仍待核验',http_failed:'官网未返回正常内容',blank:'页面内容未完整加载',interrupted:'执行中断，资料仍保留'}
const evidenceLabel=(name:string)=>name.endsWith('.png')?'页面截图':name.endsWith('.txt')?'页面文字':'原始附件'
const add=()=>submit(url.value,{...region})
</script>
<style scoped>
.collector-page{max-width:1100px;padding:28px}.collector-page header{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;margin-bottom:20px}.collector-page h1{font-size:28px;color:var(--ll-text);margin:8px 0}.collector-page p{line-height:1.75;color:var(--ll-secondary)}.collector-notice{padding:16px 18px;border:1px solid var(--ll-border);border-radius:10px;background:var(--ll-background)}.collector-notice.danger{border-color:#e3b9b0;color:#963e32;background:#fff4f1}.collector-state{display:flex;flex-wrap:wrap;gap:10px 24px;padding:16px 0;color:var(--ll-primary)}.collector-panel{padding:24px;margin:18px 0;background:var(--ll-surface);border:1px solid var(--ll-border);border-radius:12px}.collector-panel h2{font-size:19px;margin:0 0 20px}.collector-fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}label{display:block;color:var(--ll-text);font-size:14px;font-weight:600;margin-bottom:16px}input,select{display:block;width:100%;min-height:44px;padding:10px 12px;border:1px solid var(--ll-border-strong);border-radius:8px;background:var(--ll-surface);color:var(--ll-text);font:inherit;margin-top:8px}.collector-hint{font-size:13px;overflow-wrap:anywhere}.collector-jobs{list-style:none;padding:0;margin:0}.collector-jobs li{padding:20px 0;border-top:1px solid var(--ll-border);overflow-wrap:anywhere}.collector-job-heading{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}.collector-job-heading h3{font-size:17px;margin:0}.collector-job-heading span{font-size:13px;color:var(--ll-primary);white-space:nowrap}.collector-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:12px}.collector-jobs a{color:var(--ll-primary);display:inline-flex;align-items:center;min-height:44px}@media(max-width:650px){.collector-page{padding:16px}.collector-page header{display:block}.collector-panel{padding:18px}.collector-fields{grid-template-columns:1fr}.collector-actions button{width:100%}}
</style>
