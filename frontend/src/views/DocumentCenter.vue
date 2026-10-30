<template>
  <div class="page documents-page">
    <div class="page-heading"><div><h1>文书工坊</h1><p>基于案件事实复用信息，按地区要求生成可编辑的标准文书。</p></div><span class="safe-note"><i class="fa-solid fa-shield-halved"></i> 生成前自动检查缺失字段</span></div>
    <section class="generator-hero">
      <div><span>智能文书生成</span><h2>少填重复信息，多做关键判断</h2><p>选择案件和文书类型后，系统会自动带入当事人、劳动关系与证据数据。</p><button @click="scrollToTemplates">选择模板 <i class="fa-solid fa-arrow-down"></i></button></div>
      <div class="hero-checklist"><div><i class="fa-solid fa-check"></i><span><strong>字段一致性校验</strong><small>姓名、日期、金额跨文书保持一致</small></span></div><div><i class="fa-solid fa-check"></i><span><strong>地区模板适配</strong><small>按已取得的各地官方模板开放</small></span></div><div><i class="fa-solid fa-check"></i><span><strong>Word 原格式导出</strong><small>生成后仍可继续审阅和编辑</small></span></div></div>
    </section>
    <section ref="templatesRef" class="template-section">
      <div class="section-title"><h2>选择文书模板</h2><div class="region-switch"><button v-for="item in regions" :key="item" :class="{active:region===item}" @click="region=item">{{ item }}</button></div></div>
      <div class="template-grid">
        <RouterLink v-for="item in filteredTemplates" :key="item.title" :to="item.to" class="template-card">
          <span class="doc-icon" :class="item.tone"><i :class="item.icon"></i></span>
          <div class="template-copy"><span>{{ item.category }}</span><h3>{{ item.title }}</h3><p>{{ item.desc }}</p><ul><li v-for="tag in item.tags" :key="tag">{{ tag }}</li></ul></div>
          <div class="template-foot"><span><i class="fa-regular fa-clock"></i> 约 {{ item.time }} 分钟</span><b>开始生成 <i class="fa-solid fa-arrow-right"></i></b></div>
        </RouterLink>
      </div>
    </section>
    <section class="panel report-section">
      <h2>OpenClaw 浏览器补采</h2>
      <p>普通采集没找到指南时，让 OpenClaw 自己查看网页、搜索、选择地区、打开指南并保存材料和流程。</p>
      <label>补采省份 <select v-model="agentProvince"><option value="">所有仍待补全的省份</option><option v-for="p in provinces" :key="p.slug" :value="p.slug">{{p.name}}</option></select></label>
      <button :disabled="agentBusy" @click="startAgent">{{agentBusy?'OpenClaw 正在采集…':'让 OpenClaw 补采'}}</button>
      <p role="status">{{agentMessage}}</p>
      <div v-for="task in agentTasks" :key="task.id" class="report-row">
        <strong>{{task.id}}</strong><span> · {{agentState(task.state)}} · {{task.completed||0}} / {{task.total||'待确定'}}</span>
        <p v-if="task.current_task">当前省份：{{provinceName(task.current)}} · {{agentFlags(task.current_task.status)}} <a v-if="task.current_task.screenshot" :href="agentEvidence(task.id,task.current,task.current_task.screenshot)" target="_blank" rel="noopener noreferrer">查看截图 ↗</a></p>
        <p v-for="(result,slug) in task.provinces" :key="slug">{{provinceName(slug)}}：{{agentFlags(result.status)}} <a v-if="result.screenshot" :href="agentEvidence(task.id,slug,result.screenshot)" target="_blank" rel="noopener noreferrer">查看截图 ↗</a><small v-if="result.error"> · {{result.error}}</small></p>
        <p v-if="task.error">{{task.error}}</p>
        <button v-if="['failed','complete_with_gaps','interrupted','review_incomplete'].includes(task.state)" :disabled="agentBusy" @click="startAgent(task.id)">继续这个任务</button>
      </div>
    </section>
    <section class="panel report-section">
      <h2>政务服务门户观察报告</h2>
      <p><button @click="downloadExperience(false)">下载省份指南更新报告</button><button @click="downloadExperience(true)">下载省份指南 AI 复核报告</button></p>
      <p>分别搜索三个关键词，保存结果截图，并尝试进入公开办事指南的材料区域。全国采集和模型复核耗时较长，可在此查看进度。</p>
      <label><input v-model="withVision" type="checkbox"> 使用 OpenClaw / Ubuntu Qwen3.8:27b 复核截图并生成 AI 验证报告</label>
      <button :disabled="reportBusy" @click="createReport">{{reportBusy?'报告处理中…':'采集全国门户并生成报告'}}</button>
      <p role="status">{{reportMessage}}</p>
      <p class="report-help">默认展示最新完整全国报告。其他文件夹可能是专项试跑或中断记录，时间靠后不代表内容更完整。</p>
      <div v-for="report in visibleReports" :key="report.id" class="report-row">
        <strong>{{ report.recommended ? '当前完整全国报告' : report.scope_label }}</strong>
        <small>已保存 {{report.regions_saved}} 个地区 · {{report.searches_saved}} 项检索</small>
        <span>{{report.id}} · {{reportProgress(report)}} {{report.current}}</span>
        <button v-if="report.state==='complete'" @click="downloadReport(report.id)">下载门户观察报告</button>
        <button v-if="report.state==='complete' && report.ai_report" @click="downloadReport(report.id,true)">下载 AI 验证报告</button>
        <small v-if="report.ai_report">AI 截图复核完整地区：{{report.ai_completed}} / {{report.total}}{{report.ai_state==='incomplete'?'（仍有调用未完成，详见报告）':''}}</small>
        <small v-if="report.error">{{report.error}}</small>
      </div>
      <details v-if="historyReports.length"><summary>历史与未完成批次（{{historyReports.length}}）</summary><div v-for="report in historyReports" :key="report.id" class="report-row"><span>{{report.id}} · {{report.scope_label}} · {{reportProgress(report)}} · 已保存 {{report.regions_saved}} 个地区</span><button v-if="report.report_ready" @click="downloadReport(report.id)">下载历史报告</button><small v-if="report.error">{{report.error}}</small></div></details>
    </section>
    <section class="recent-section"><div class="section-title"><h2>最近生成</h2><button class="text-button">全部记录</button></div><div class="panel recent-empty"><i class="fa-regular fa-file-lines"></i><div><strong>生成的文书会保留在这里</strong><p>你可以随时重新下载或基于原数据创建新版本。</p></div></div></section>
  </div>
</template>
<script setup lang="ts">
import {computed,ref,onMounted,onBeforeUnmount} from 'vue'
import {RouterLink} from 'vue-router'
import axios from 'axios'
import {provinces} from '@/data/provinces'
import {downloadDocument} from '@/composables/downloadDocument'
import {parsePortalReports,parseAgentTasks,responseIdentifier,workspaceError} from '../../../packages/regional-contracts/src/workspace'
import type {PortalReport,AgentTask} from '../../../packages/regional-contracts/src/workspace'
const region=ref('全部'),templatesRef=ref<HTMLElement|null>(null)
const regions=['全部',...provinces.filter(p=>p.hasApplication||p.hasEvidence).map(p=>p.shortName)]
const templates=provinces.flatMap(p=>[
  ...(p.hasApplication&&p.applicationRoute?[{region:p.shortName,category:'官方仲裁文书',title:`劳动仲裁申请书（${p.shortName}）`,desc:p.note,tags:[p.scope,'原模板填充','手写签名'],time:10,to:p.applicationRoute,tone:'teal',icon:'fa-solid fa-file-signature'}]:[]),
  ...(p.hasEvidence&&p.evidenceRoute?[{region:p.shortName,category:'官方证据材料',title:`证据清单（${p.shortName}）`,desc:p.materialNote,tags:[p.scope,'自动编号','按当地表头填写'],time:5,to:p.evidenceRoute,tone:'gold',icon:'fa-solid fa-list-check'}]:[])
])
const filteredTemplates=computed(()=>region.value==='全部'?templates:templates.filter(i=>i.region===region.value))
const scrollToTemplates=()=>templatesRef.value?.scrollIntoView({behavior:'smooth'})
const reports=ref<PortalReport[]>([]),reportMessage=ref(''),reportBusy=ref(false),withVision=ref(true)
const API_BASE=(import.meta.env.VITE_API_BASE_URL||'http://127.0.0.1:8000').replace(/\/$/,'')
let reportTimer:ReturnType<typeof setTimeout>|undefined,agentTimer:ReturnType<typeof setTimeout>|undefined,disposed=false
const agentProvince=ref(''),agentTasks=ref<AgentTask[]>([]),agentBusy=ref(false),agentMessage=ref('')
const downloadExperience=async(ai:boolean)=>{
  try{const {data}=await axios.get<Blob>(`${API_BASE}/api/portal-reports/experience-reports/latest/${ai?'ai':'main'}`,{responseType:'blob',timeout:30000});await downloadDocument(data,ai?'各省劳动争议办事指南AI复核报告.docx':'各省劳动争议办事指南更新报告.docx')}
  catch{if(!disposed)reportMessage.value='省份指南报告尚未生成，或报告服务暂时无法连接。'}
}
const visibleReports=computed(()=>reports.value.filter(r=>r.recommended||r.state==='running'))
const historyReports=computed(()=>reports.value.filter(r=>!r.recommended&&r.state!=='running'))
const provinceName=(slug:string)=>provinces.find(p=>p.slug===slug)?.name||slug
const agentEvidence=(id:string,slug:string,filename:string)=>`${API_BASE}/api/portal-reports/openclaw-tasks/${encodeURIComponent(id)}/${encodeURIComponent(slug)}/evidence/${encodeURIComponent(filename)}`
const stateLabels:Record<string,string>={queued:'等待开始',running:'正在采集',reviewing:'复核新截图并更新三端',review_incomplete:'AI 复核未完成，尚未更新三端',complete:'采集完成',complete_with_gaps:'已结束，部分仍未找到',failed:'任务失败',interrupted:'任务中断'}
const agentState=(state:string)=>stateLabels[state]||state
const flagLabels=[['site_opened','网页已打开'],['guide_found','指南已找到'],['template_downloaded','模板已下载'],['fill_verified','已验证可填写']] as const
const agentFlags=(flags?:Record<string,boolean>)=>flags?flagLabels.map(([key,label])=>`${label}：${flags[key]?'是':'否'}`).join(' · '):'等待结果'
const refreshAgent=async()=>{
  try{
    const {data}=await axios.get<unknown>(`${API_BASE}/api/portal-reports/openclaw-tasks`,{timeout:15000})
    if(disposed)return
    const items=parseAgentTasks(data);agentTasks.value=items;agentBusy.value=items.some(t=>['queued','running','reviewing'].includes(t.state))
    clearTimeout(agentTimer);if(agentBusy.value)agentTimer=setTimeout(refreshAgent,8000)
  }catch{if(!disposed){agentMessage.value='暂时无法读取 OpenClaw 任务，请确认后端已启动。';if(agentBusy.value)agentTimer=setTimeout(refreshAgent,15000)}}
}
const startAgent=async(resume?:string|MouseEvent)=>{
  agentBusy.value=true;agentMessage.value='正在安排后台采集…'
  try{
    const payload=typeof resume==='string'?{resume}:agentProvince.value?{provinces:[agentProvince.value]}:{}
    const {data}=await axios.post<unknown>(`${API_BASE}/api/portal-reports/openclaw-tasks`,payload,{timeout:15000})
    if(disposed)return
    agentMessage.value=`任务 ${responseIdentifier(data)} 已安排，可离开此页。`;await refreshAgent()
  }catch(error:unknown){if(!disposed){agentBusy.value=false;agentMessage.value=workspaceError(error,'OpenClaw 任务启动失败')}}
}
const reportProgress=(report:PortalReport)=>{
  const states:Record<string,string>={complete:'报告已生成',interrupted:'任务中断，可续跑',failed:'任务失败',running:'处理中'}
  const phases:Record<string,string>={materials:'材料截图校验',workflows:'地区指南与流程采集',vision:'Ubuntu AI 截图复核'}
  return report.state==='running'?`${phases[report.phase]||'门户检索采集'} ${report.completed} / ${report.total}`:(states[report.state]||report.state)
}
const refreshReports=async()=>{
  try{
    const {data}=await axios.get<unknown>(`${API_BASE}/api/portal-reports`)
    if(disposed)return
    const items=parsePortalReports(data);reports.value=items;reportBusy.value=items.some(r=>r.state==='running')
    clearTimeout(reportTimer);if(reportBusy.value)reportTimer=setTimeout(refreshReports,5000)
  }catch{if(!disposed)reportMessage.value='暂时无法连接报告服务，请确认后端已启动。'}
}
const createReport=async()=>{
  reportMessage.value='正在开始采集…'
  try{const {data}=await axios.post<unknown>(`${API_BASE}/api/portal-reports`,{vision:withVision.value});if(disposed)return;reportMessage.value=`报告编号：${responseIdentifier(data)}；可离开本页，后端会继续采集。`;await refreshReports()}
  catch(error:unknown){if(!disposed)reportMessage.value=workspaceError(error,'报告任务启动失败')}
}
const downloadReport=async(id:string,ai=false)=>{
  try{const {data}=await axios.get<Blob>(`${API_BASE}/api/portal-reports/${encodeURIComponent(id)}/${ai?'download-ai':'download'}`,{responseType:'blob'});await downloadDocument(data,ai?'劳动仲裁政务服务门户AI验证报告.docx':'劳动仲裁政务服务门户观察报告.docx')}
  catch{if(!disposed)reportMessage.value='报告下载失败'}
}
onMounted(()=>{void refreshReports();void refreshAgent()})
onBeforeUnmount(()=>{disposed=true;clearTimeout(reportTimer);clearTimeout(agentTimer)})
</script>
<style scoped>
.safe-note{color:#667a8e;font-size:11px}.safe-note i{margin-right:6px;color:var(--teal)}.generator-hero{position:relative;overflow:hidden;min-height:230px;margin-bottom:28px;padding:34px 38px;display:grid;grid-template-columns:1.2fr .8fr;align-items:center;gap:28px;border-radius:17px;color:#fff;background:linear-gradient(120deg,#0b243f,#113a50 62%,#0b5e5c)}.generator-hero:after{content:'法';position:absolute;right:-20px;bottom:-90px;color:rgba(255,255,255,.035);font:260px serif}.generator-hero>div{position:relative;z-index:1}.generator-hero>div:first-child>span{color:#83d9d1;font-size:11px;letter-spacing:.12em}.generator-hero h2{margin:7px 0 9px;font-size:27px}.generator-hero p{max-width:560px;margin:0 0 18px;color:#b9cad8;font-size:12px;line-height:1.7}.generator-hero button{padding:10px 15px;border:1px solid rgba(255,255,255,.25);border-radius:9px;color:#fff;background:rgba(255,255,255,.1);font-size:12px}.generator-hero button i{margin-left:8px}.hero-checklist{padding:4px 0 4px 25px;border-left:1px solid rgba(255,255,255,.15)}.hero-checklist>div{display:flex;gap:11px;margin:16px 0}.hero-checklist>div>i{width:25px;height:25px;display:grid;place-items:center;border-radius:50%;color:#9be4dc;background:rgba(53,193,179,.16);font-size:10px}.hero-checklist strong,.hero-checklist small{display:block}.hero-checklist strong{font-size:12px}.hero-checklist small{margin-top:3px;color:#aebfcd;font-size:10px}.region-switch{display:flex;padding:3px;border:1px solid var(--line);border-radius:9px;background:#fff}.region-switch button{padding:6px 11px;border:0;border-radius:6px;color:#718092;background:transparent;font-size:11px}.region-switch button.active{color:#fff;background:#173653}.template-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:15px}.template-card{min-height:238px;padding:19px;display:flex;flex-direction:column;border:1px solid var(--line);border-radius:14px;background:#fff;transition:.2s}.template-card:hover{transform:translateY(-3px);border-color:#bacdcb;box-shadow:var(--shadow)}.doc-icon{width:42px;height:42px;display:grid;place-items:center;border-radius:11px}.doc-icon.teal{color:#0a7e75;background:#e6f7f4}.doc-icon.navy{color:#315d8a;background:#eaf1f8}.doc-icon.gold{color:#9e6b1b;background:#fff4df}.doc-icon.violet{color:#6e54a0;background:#f1edfa}.doc-icon.red{color:#b43c49;background:#ffedf0}.template-copy>span{display:block;margin-top:16px;color:#82909e;font-size:9px}.template-copy h3{margin:4px 0 7px;font-size:15px}.template-copy p{margin:0;color:#6f7e8f;font-size:10px;line-height:1.6}.template-copy ul{display:flex;gap:5px;flex-wrap:wrap;margin:11px 0 0;padding:0;list-style:none}.template-copy li{padding:3px 6px;border-radius:4px;color:#6f7d8c;background:#f1f4f6;font-size:8px}.template-foot{margin-top:auto;padding-top:13px;display:flex;justify-content:space-between;border-top:1px solid var(--line);font-size:10px}.template-foot>span{color:#8793a0}.template-foot b{color:var(--teal-dark)}.recent-section{margin-top:28px}.recent-empty{padding:22px;display:flex;align-items:center;gap:14px}.recent-empty>i{width:42px;height:42px;display:grid;place-items:center;border-radius:10px;color:#788da3;background:#edf2f7}.recent-empty strong{font-size:12px}.recent-empty p{margin:4px 0 0;color:#84909d;font-size:10px}@media(max-width:1050px){.template-grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:700px){.generator-hero{grid-template-columns:1fr;padding:26px 22px}.hero-checklist{display:none}.template-grid{grid-template-columns:1fr}.safe-note{display:none}.section-title{align-items:flex-start;gap:12px;flex-direction:column}.region-switch{width:100%;overflow:auto}}
.report-section{margin-top:24px;padding:24px}.report-section p{font-size:13px;line-height:1.7}.report-section button{margin:10px;padding:9px 14px;border:1px solid #b9ceca;border-radius:8px;background:#f0f8f5}.report-section label{font-size:12px}.report-row{padding:9px 0;border-top:1px solid #e4ece9;font-size:12px}.region-switch{flex-wrap:wrap;max-width:70%}</style>
