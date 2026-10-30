<template>
  <div class="page cases-page">
    <div class="page-heading">
      <div><h1>案件中心</h1><p>将案情、证据、诉求和关键时限放在同一个工作区。</p></div>
      <button class="primary-action" @click="showCreate = true"><i class="fa-solid fa-plus"></i> 新建案件</button>
    </div>
    <p v-if="storageIssue" role="status">{{ storageIssue }}</p>
    <div class="filter-bar panel">
      <label class="search-box"><i class="fa-solid fa-magnifying-glass"></i><input v-model="query" data-global-search="" placeholder="搜索案件号、当事人或单位"></label>
      <div class="filter-tabs">
        <button v-for="item in stages" :key="item" :class="{ active: stage === item }" @click="stage = item">{{ item }}</button>
      </div>
      <button class="filter-button"><i class="fa-solid fa-sliders"></i> 筛选</button>
    </div>
    <div class="summary-strip">
      <span><b>{{ filtered.length }}</b> 件案件</span><span><b>{{ activeCases.length }}</b> 件进行中</span><span><b>2</b> 件需优先处理</span>
    </div>
    <div class="panel case-table-wrap">
      <table>
        <thead><tr><th>案件</th><th>地区 / 对方当事人</th><th>阶段</th><th>材料</th><th>关键日期</th><th>争议金额</th><th></th></tr></thead>
        <tbody>
          <tr v-for="item in filtered" :key="item.id">
            <td><strong>{{ item.title }}</strong><small>{{ item.id }} · {{ item.client }}</small></td>
            <td><strong>{{ item.region }}</strong><small>{{ item.employer }}</small></td>
            <td><span class="status" :class="item.risk">{{ item.stage }}</span></td>
            <td><div class="progress-cell"><span><i :style="{ width: item.evidenceReady + '%' }"></i></span><small>{{ item.evidenceReady }}%</small></div></td>
            <td><strong>{{ item.deadline }}</strong><small>最后更新 {{ item.updatedAt }}</small></td>
            <td class="money">¥ {{ item.amount.toLocaleString() }}</td>
            <td><button class="more"><i class="fa-solid fa-ellipsis"></i></button></td>
          </tr>
        </tbody>
      </table>
      <div v-if="!filtered.length" class="empty-state"><i class="fa-regular fa-folder-open"></i>没有找到符合条件的案件</div>
    </div>

    <div v-if="showCreate" class="modal-backdrop" @click.self="closeCreate">
      <form class="create-modal" @submit.prevent="createCase">
        <div class="modal-head"><div><small>第一步，共三步</small><h2>建立案件档案</h2></div><button type="button" @click="closeCreate"><i class="fa-solid fa-xmark"></i></button></div>
        <p class="modal-note"><i class="fa-solid fa-lock"></i> 先记录最少信息，之后可在案件中继续补充。</p>
        <p v-if="createError" class="modal-note" role="alert">{{ createError }}</p>
        <div class="form-grid">
          <label class="wide">争议类型<span>*</span><select v-model="form.title" required><option disabled value="">请选择</option><option>工资及加班费争议</option><option>违法解除劳动合同</option><option>未签劳动合同双倍工资</option><option>工伤待遇争议</option><option>社会保险争议</option></select></label>
          <label>申请人<input v-model="form.client" required placeholder="例如：张某"></label>
          <label>争议金额<input v-model="form.amount" type="number" min="0" placeholder="人民币金额"></label>
          <label class="wide">用人单位<input v-model="form.employer" required placeholder="单位完整名称"></label>
          <label>案件地区<select v-model="form.region"><option>浙江·杭州</option><option>浙江·宁波</option><option>广东·深圳</option><option>广东·广州</option><option>其他地区</option></select></label>
          <label>预计提交日<input v-model="form.deadline" type="date"></label>
        </div>
        <div class="modal-actions"><button type="button" @click="closeCreate">取消</button><button class="primary-action" type="submit">创建并开始梳理 <i class="fa-solid fa-arrow-right"></i></button></div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useWorkspace } from '@/composables/useWorkspace'
import type {NewCaseInput} from '@/composables/useWorkspace'
const { state, activeCases, addCase, storageIssue } = useWorkspace()
const route = useRoute(); const router = useRouter()
const query = ref(''); const stage = ref('全部'); const showCreate = ref(route.query.new === '1')
const stages = ['全部', '案情梳理', '材料准备', '待提交', '审理中', '已结案']
const createError=ref('')
const form = reactive<Required<NewCaseInput>>({ title: '', client: '', employer: '', region: '浙江·杭州', amount: '', deadline: '' })
const filtered = computed(() => state.cases.filter(item => {
  const text = `${item.id}${item.title}${item.client}${item.employer}${item.region}`.toLowerCase()
  return (stage.value === '全部' || item.stage === stage.value) && text.includes(query.value.toLowerCase())
}))
watch(() => route.query.new, value => { if (value === '1') showCreate.value = true })
const closeCreate = () => { showCreate.value = false; if (route.query.new) router.replace('/admin/cases') }
const createCase = () => { const result=addCase(form);if(!result.ok){createError.value=result.error;return};createError.value='';closeCreate(); Object.assign(form, { title:'', client:'', employer:'', region:'浙江·杭州', amount:'', deadline:'' }) }
</script>

<style scoped>
.filter-bar { min-height:64px; padding:10px 12px; display:flex; align-items:center; gap:14px; box-shadow:none; }.search-box { width:min(360px,35%); height:42px; padding:0 13px; display:flex; align-items:center; gap:9px; border:1px solid var(--line); border-radius:9px; background:#f9fafb; color:#98a3af; }.search-box input { width:100%; border:0; outline:0; background:transparent; font-size:13px; }.filter-tabs { display:flex; gap:3px; overflow:auto; }.filter-tabs button,.filter-button { white-space:nowrap; padding:9px 11px; border:0; border-radius:8px; color:#6d7a8b; background:transparent; font-size:12px; }.filter-tabs button.active { color:#0d746d; background:#eaf6f5; font-weight:700; }.filter-button { margin-left:auto; border:1px solid var(--line); }.summary-strip { display:flex; gap:22px; padding:17px 4px 12px; color:#7a8796; font-size:12px; }.summary-strip b { color:#26384f; }.case-table-wrap { overflow:auto; }table { width:100%; border-collapse:collapse; min-width:920px; }th { padding:13px 18px; color:#7b8796; background:#f7f9fb; text-align:left; font-size:11px; font-weight:600; }td { padding:17px 18px; border-top:1px solid var(--line); color:#33445a; font-size:12px; }td strong,td small { display:block; }td strong { margin-bottom:5px; font-size:12px; }td small { color:#84909e; font-size:10px; }.progress-cell { display:flex; align-items:center; gap:8px; }.progress-cell > span { width:66px; height:5px; overflow:hidden; border-radius:5px; background:#e6ecef; }.progress-cell i { display:block; height:100%; background:var(--teal); }.money { font-weight:700; }.more { border:0; color:#8e99a6; background:transparent; }
.modal-backdrop { position:fixed; inset:0; z-index:100; display:grid; place-items:center; padding:20px; background:rgba(7,22,42,.55); backdrop-filter:blur(4px); }.create-modal { width:min(580px,100%); border-radius:16px; background:#fff; box-shadow:0 28px 80px rgba(0,0,0,.2); overflow:hidden; }.modal-head { padding:21px 24px 16px; display:flex; justify-content:space-between; border-bottom:1px solid var(--line); }.modal-head small { color:var(--teal-dark); font-size:10px; }.modal-head h2 { margin:4px 0 0; font-size:20px; }.modal-head button { width:34px;height:34px;border:0;border-radius:8px;color:#778493;background:#f4f6f8;}.modal-note { margin:18px 24px 4px; padding:10px 12px; border-radius:8px; color:#5d7085; background:#edf6f5; font-size:11px; }.modal-note i { margin-right:6px;color:var(--teal);}.form-grid { padding:16px 24px 24px; display:grid; grid-template-columns:1fr 1fr; gap:15px; }.form-grid label { color:#4d5b6b; font-size:12px; font-weight:600; }.form-grid label span { color:#c13a49; }.form-grid .wide { grid-column:1/-1; }.form-grid input,.form-grid select { width:100%; height:42px; margin-top:7px; padding:0 11px; border:1px solid #dce2e8; border-radius:8px; outline:none; background:#fff; font-size:13px; }.form-grid input:focus,.form-grid select:focus { border-color:var(--teal); box-shadow:0 0 0 3px rgba(13,148,136,.10); }.modal-actions { padding:15px 24px; display:flex; justify-content:flex-end; gap:10px; border-top:1px solid var(--line); background:#fafbfc; }.modal-actions > button:first-child { border:0;color:#677587;background:transparent;}.modal-actions .primary-action i { margin:0 0 0 8px; }
@media (max-width:760px){.filter-bar{align-items:stretch;flex-direction:column}.search-box{width:100%}.filter-tabs{width:100%}.filter-button{display:none}.form-grid{grid-template-columns:1fr}.form-grid .wide{grid-column:auto}.summary-strip{overflow:auto}.case-table-wrap{margin:0 -16px;border-radius:0}}
</style>
