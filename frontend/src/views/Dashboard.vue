<template>
  <div class="page dashboard-page">
    <p v-if="storageIssue" role="status">{{ storageIssue }}</p>
    <section class="welcome-row">
      <div>
        <p class="date-line">{{ today }} · 工作进度已同步</p>
        <h1>早上好，先处理最紧急的事项</h1>
        <p>你有 <b>2 项时效提醒</b> 和 <b>3 份待补充材料</b>。</p>
      </div>
      <div class="quick-actions">
        <RouterLink to="/admin/documents"><i class="fa-regular fa-file-lines"></i> 模板管理</RouterLink>
        <RouterLink to="/admin/cases?new=1" class="solid"><i class="fa-solid fa-plus"></i> 新建案件</RouterLink>
      </div>
    </section>

    <section class="metric-grid">
      <article v-for="metric in metrics" :key="metric.label" class="metric-card">
        <span class="metric-icon" :class="metric.tone"><i :class="metric.icon"></i></span>
        <div><small>{{ metric.label }}</small><strong>{{ metric.value }}</strong><p>{{ metric.note }}</p></div>
      </article>
    </section>

    <div class="dashboard-grid">
      <section class="case-section">
        <div class="section-title"><h2>进行中的案件</h2><RouterLink to="/admin/cases">查看全部 <i class="fa-solid fa-arrow-right"></i></RouterLink></div>
        <div class="panel case-list">
          <article v-for="item in activeCases.slice(0, 3)" :key="item.id" class="case-row">
            <div class="case-emblem">{{ item.region.slice(0, 1) }}</div>
            <div class="case-main">
              <div class="case-title-line"><strong>{{ item.title }}</strong><span class="status" :class="item.risk">{{ item.stage }}</span></div>
              <p>{{ item.id }} · {{ item.client }} 诉 {{ item.employer }}</p>
              <div class="case-progress"><span><i :style="{ width: item.evidenceReady + '%' }"></i></span><small>材料完整度 {{ item.evidenceReady }}%</small></div>
            </div>
            <div class="case-meta"><small>争议金额</small><strong>¥ {{ item.amount.toLocaleString() }}</strong><span><i class="fa-regular fa-clock"></i> {{ item.deadline }}</span></div>
            <button aria-label="查看案件"><i class="fa-solid fa-chevron-right"></i></button>
          </article>
        </div>
      </section>

      <aside class="right-column">
        <div class="section-title"><h2>待办与时效</h2><RouterLink to="/admin/deadlines">管理日程</RouterLink></div>
        <div class="panel timeline-card">
          <div v-for="todo in todos" :key="todo.title" class="timeline-item" :class="todo.level">
            <div class="timeline-date"><strong>{{ todo.day }}</strong><small>{{ todo.month }}</small></div>
            <div><strong>{{ todo.title }}</strong><p>{{ todo.case }}</p><span>{{ todo.note }}</span></div>
          </div>
        </div>
      </aside>
    </div>

    <section class="tools-section">
      <div class="section-title"><h2>常用工具</h2><RouterLink to="/admin/documents">全部工具</RouterLink></div>
      <div class="tool-grid">
        <RouterLink v-for="tool in tools" :key="tool.title" :to="tool.to" class="tool-card">
          <span :class="tool.tone"><i :class="tool.icon"></i></span><div><strong>{{ tool.title }}</strong><p>{{ tool.desc }}</p></div><i class="fa-solid fa-arrow-up-right-from-square arrow"></i>
        </RouterLink>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useWorkspace } from '@/composables/useWorkspace'

const { activeCases, totalAmount, storageIssue } = useWorkspace()
const today = new Intl.DateTimeFormat('zh-CN', { month: 'long', day: 'numeric', weekday: 'long' }).format(new Date())
const metrics = computed(() => [
  { label: '进行中案件', value: activeCases.value.length, note: '较上月新增 2 件', icon: 'fa-solid fa-briefcase', tone: 'teal' },
  { label: '待完善证据', value: '8', note: '3 项需要优先补充', icon: 'fa-solid fa-folder-open', tone: 'gold' },
  { label: '7 日内关键节点', value: '2', note: '最近节点为 9 月 19 日', icon: 'fa-regular fa-calendar', tone: 'red' },
  { label: '在办争议金额', value: `¥${Math.round(totalAmount.value / 10000)}万`, note: '按当前请求金额统计', icon: 'fa-solid fa-chart-line', tone: 'navy' },
])
const todos = [
  { day: '19', month: '9月', title: '提交仲裁申请材料', case: 'PL-2026-017 · 违法解除', note: '剩余 3 天', level: 'urgent' },
  { day: '22', month: '9月', title: '补充工资流水', case: 'PL-2026-018 · 工资争议', note: '剩余 6 天', level: 'normal' },
  { day: '08', month: '10月', title: '仲裁庭开庭', case: 'PL-2026-015 · 工伤待遇', note: '宁波市劳动人事仲裁院', level: 'later' },
]
const tools = [
  { title: '仲裁申请书', desc: '按地区模板生成并校验必填项', to: '/admin/documents', icon: 'fa-solid fa-file-signature', tone: 'teal' },
  { title: '证据清单', desc: '统一编号并关联证明目的', to: '/admin/evidence', icon: 'fa-solid fa-list-check', tone: 'navy' },
  { title: '赔偿试算', desc: '工资、加班费与经济补偿', to: '/admin/documents', icon: 'fa-solid fa-calculator', tone: 'gold' },
  { title: 'AI 案情分析', desc: '梳理请求权、举证责任与风险', to: '/admin/knowledge', icon: 'fa-solid fa-wand-magic-sparkles', tone: 'violet' },
]
</script>

<style scoped>
.welcome-row { display:flex; align-items:flex-end; justify-content:space-between; gap:22px; margin-bottom:24px; }
.date-line { color:#8090a3 !important; font-size:12px !important; }
.welcome-row h1 { margin:5px 0 7px; font-size:clamp(25px,2.2vw,34px); letter-spacing:-.05em; }
.welcome-row p { margin:0; color:var(--muted); font-size:14px; }
.welcome-row p b { color:#b23a47; }
.quick-actions { display:flex; gap:10px; }
.quick-actions a { height:42px; padding:0 15px; display:flex; align-items:center; gap:8px; border:1px solid var(--line); border-radius:10px; background:#fff; font-size:13px; font-weight:600; }
.quick-actions .solid { border-color:var(--teal-dark); color:#fff; background:var(--teal-dark); }
.metric-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:28px; }
.metric-card { display:flex; gap:14px; padding:19px; border:1px solid var(--line); border-radius:var(--radius); background:#fff; box-shadow:var(--shadow); }
.metric-icon { flex:0 0 42px; height:42px; display:grid; place-items:center; border-radius:11px; }
.metric-icon.teal { color:#087e75; background:#e4f7f4; }.metric-icon.gold { color:#a26915; background:#fff4dc; }.metric-icon.red { color:#b33a48; background:#ffedf0; }.metric-icon.navy { color:#244c78; background:#eaf1f9; }
.metric-card small,.metric-card strong,.metric-card p { display:block; }
.metric-card small { color:var(--muted); font-size:12px; }.metric-card strong { margin:3px 0 1px; color:#17283f; font-size:24px; }.metric-card p { margin:0; color:#8290a0; font-size:11px; }
.dashboard-grid { display:grid; grid-template-columns:minmax(0,1.75fr) minmax(300px,.75fr); gap:20px; margin-bottom:28px; }
.case-list { overflow:hidden; }.case-row { display:grid; grid-template-columns:42px minmax(0,1fr) 130px 28px; align-items:center; gap:14px; padding:18px 20px; border-bottom:1px solid var(--line); }.case-row:last-child { border:0; }
.case-emblem { width:40px; height:40px; display:grid; place-items:center; border-radius:11px; color:#176b68; background:#e9f5f4; font-weight:800; }
.case-title-line { display:flex; align-items:center; gap:9px; }.case-title-line strong { color:#1b2a3f; font-size:14px; }.case-main p { margin:5px 0 9px; color:#788697; font-size:11px; }
.case-progress { display:flex; align-items:center; gap:8px; }.case-progress > span { width:105px; height:4px; overflow:hidden; border-radius:5px; background:#e8edf1; }.case-progress i { display:block; height:100%; border-radius:5px; background:var(--teal); }.case-progress small { color:#7d8998; font-size:10px; }
.case-meta { text-align:right; }.case-meta small,.case-meta strong,.case-meta span { display:block; }.case-meta small { color:#8793a2; font-size:10px; }.case-meta strong { margin:2px 0 7px; color:#24344b; font-size:14px; }.case-meta span { color:#8b5960; font-size:10px; }.case-row > button { border:0; color:#9ca8b5; background:transparent; }
.timeline-card { padding:6px 18px; }.timeline-item { position:relative; display:grid; grid-template-columns:48px 1fr; gap:13px; padding:16px 0; border-bottom:1px solid var(--line); }.timeline-item:last-child { border:0; }.timeline-date { width:44px; height:49px; display:grid; place-content:center; border-radius:10px; color:#37516f; background:#edf3f8; text-align:center; }.timeline-date strong,.timeline-date small { display:block; line-height:1.1; }.timeline-date strong { font-size:17px; }.timeline-date small { margin-top:3px; font-size:9px; }.timeline-item.urgent .timeline-date { color:#aa3341; background:#ffedf0; }
.timeline-item > div:last-child > strong { font-size:13px; }.timeline-item p { margin:4px 0; color:#778597; font-size:10px; }.timeline-item span { color:#9a6970; font-size:10px; }
.tool-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:14px; }.tool-card { position:relative; display:flex; align-items:center; gap:12px; min-height:88px; padding:17px; border:1px solid var(--line); border-radius:13px; background:#fff; transition:.18s ease; }.tool-card:hover { transform:translateY(-2px); border-color:#bfd2d0; box-shadow:var(--shadow); }.tool-card > span { width:39px; height:39px; flex:0 0 39px; display:grid; place-items:center; border-radius:10px; }.tool-card .teal { color:#087e75; background:#e4f7f4; }.tool-card .navy { color:#244c78; background:#eaf1f9; }.tool-card .gold { color:#a26915; background:#fff4dc; }.tool-card .violet { color:#7252a7; background:#f1ecfa; }.tool-card strong { display:block; color:#23334a; font-size:13px; }.tool-card p { margin:5px 20px 0 0; color:#7c8998; font-size:10px; line-height:1.5; }.tool-card .arrow { position:absolute; right:14px; top:16px; color:#a9b3bd; font-size:10px; }
@media (max-width:1200px) { .metric-grid,.tool-grid { grid-template-columns:repeat(2,1fr); } .dashboard-grid { grid-template-columns:1fr; } }
@media (max-width:680px) { .welcome-row { align-items:flex-start; flex-direction:column; }.quick-actions { width:100%; }.quick-actions a { flex:1; justify-content:center; }.metric-grid,.tool-grid { grid-template-columns:1fr 1fr; }.metric-card { padding:15px; }.metric-icon { display:none; }.case-row { grid-template-columns:36px 1fr; padding:15px; }.case-meta,.case-row > button { display:none; }.case-emblem { width:34px;height:34px;}.tool-grid { grid-template-columns:1fr; } }
</style>
