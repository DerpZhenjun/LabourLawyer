<template>
  <div class="page">
    <p v-if="storageIssue" role="status">{{ storageIssue }}</p>
    <div class="page-heading"><div><h1>证据中心</h1><p>按“证据—事实—请求”建立关联，避免材料堆积却无法证明关键事实。</p></div><button class="primary-action"><i class="fa-solid fa-cloud-arrow-up"></i> 上传材料</button></div>
    <div class="evidence-layout">
      <aside class="panel case-tree">
        <div class="panel-header"><h3>案件目录</h3><button><i class="fa-solid fa-plus"></i></button></div>
        <button v-for="(item,index) in cases" :key="item.id" :class="{ active:index===0 }"><span>{{ item.region.slice(0,1) }}</span><div><strong>{{ item.title }}</strong><small>{{ item.id }} · {{ item.evidence }} 项材料</small></div></button>
      </aside>
      <section class="panel evidence-main">
        <div class="evidence-head"><div><small>PL-2026-018</small><h2>工资及加班费争议</h2></div><div class="evidence-score"><span>材料完整度</span><strong>75%</strong><i><b style="width:75%"></b></i></div></div>
        <div class="evidence-alert"><i class="fa-solid fa-circle-exclamation"></i><div><strong>还缺少 3 项关键材料</strong><p>建议补充 2025 年 10—12 月考勤记录、工资构成说明和解除通知送达证明。</p></div><button>查看清单</button></div>
        <div class="category-tabs"><button class="active">全部材料 <b>12</b></button><button>劳动关系 <b>3</b></button><button>工资报酬 <b>5</b></button><button>考勤加班 <b>3</b></button><button>解除材料 <b>1</b></button></div>
        <div class="evidence-table">
          <div v-for="file in files" :key="file.name" class="evidence-row">
            <span class="file-icon" :class="file.type"><i :class="file.icon"></i></span>
            <div><strong>{{ file.name }}</strong><p>{{ file.meta }}</p></div>
            <div class="purpose"><small>证明目的</small><span>{{ file.purpose }}</span></div>
            <span class="quality" :class="file.qualityClass"><i class="fa-solid fa-circle-check"></i> {{ file.quality }}</span>
            <button><i class="fa-solid fa-ellipsis"></i></button>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>
<script setup lang="ts">
import { useWorkspace } from '@/composables/useWorkspace'
const { state, storageIssue } = useWorkspace(); const cases = state.cases.slice(0,3)
const files=[
  {name:'劳动合同.pdf',meta:'PDF · 2.4 MB · 今天 09:32',purpose:'证明劳动关系、岗位与工资标准',quality:'已校验',qualityClass:'good',type:'pdf',icon:'fa-solid fa-file-pdf'},
  {name:'2026年工资流水.xlsx',meta:'Excel · 184 KB · 今天 09:36',purpose:'证明工资支付情况与欠付金额',quality:'信息完整',qualityClass:'good',type:'xls',icon:'fa-solid fa-file-excel'},
  {name:'钉钉考勤截图（1-8月）.zip',meta:'压缩包 · 18.6 MB · 昨天 18:24',purpose:'证明延时加班及休息日出勤',quality:'待整理',qualityClass:'wait',type:'zip',icon:'fa-solid fa-file-zipper'},
  {name:'解除劳动关系微信记录.jpg',meta:'图片 · 3.1 MB · 09-14 13:08',purpose:'证明用人单位提出解除',quality:'需补原图',qualityClass:'warn',type:'img',icon:'fa-solid fa-file-image'},
]
</script>
<style scoped>
.evidence-layout{display:grid;grid-template-columns:270px 1fr;gap:18px}.case-tree{align-self:start;overflow:hidden}.case-tree .panel-header button{border:0;color:var(--teal);background:transparent}.case-tree>button{width:100%;padding:15px 16px;display:flex;align-items:center;gap:11px;border:0;border-top:1px solid var(--line);background:#fff;text-align:left}.case-tree>button.active{background:#edf7f6;box-shadow:inset 3px 0 var(--teal)}.case-tree>button>span{width:34px;height:34px;display:grid;place-items:center;border-radius:9px;color:#24615f;background:#e2f1ef;font-weight:700}.case-tree strong,.case-tree small{display:block}.case-tree strong{font-size:12px}.case-tree small{margin-top:4px;color:#8793a1;font-size:9px}.evidence-main{overflow:hidden}.evidence-head{padding:20px 22px;display:flex;align-items:center;justify-content:space-between}.evidence-head small{color:#8995a2;font-size:10px}.evidence-head h2{margin:4px 0 0;font-size:18px}.evidence-score{display:grid;grid-template-columns:auto auto;gap:4px 10px;text-align:right}.evidence-score span{color:#83909e;font-size:10px}.evidence-score strong{font-size:16px}.evidence-score i{grid-column:1/-1;width:130px;height:5px;overflow:hidden;border-radius:5px;background:#e5ebef}.evidence-score b{display:block;height:100%;background:var(--teal)}.evidence-alert{margin:0 22px 18px;padding:14px;display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:12px;border:1px solid #f1ddb8;border-radius:10px;background:#fffaf0}.evidence-alert>i{color:#b77c20}.evidence-alert strong{font-size:12px}.evidence-alert p{margin:3px 0 0;color:#806e51;font-size:10px}.evidence-alert button{border:0;color:#9a6817;background:transparent;font-size:11px;font-weight:700}.category-tabs{padding:0 22px;display:flex;gap:20px;border-bottom:1px solid var(--line);overflow:auto}.category-tabs button{padding:11px 0;border:0;border-bottom:2px solid transparent;color:#778493;background:transparent;white-space:nowrap;font-size:11px}.category-tabs button.active{border-color:var(--teal);color:#146f69;font-weight:700}.category-tabs b{padding:1px 5px;border-radius:8px;background:#edf1f4;font-size:9px}.evidence-row{display:grid;grid-template-columns:40px minmax(160px,1fr) minmax(180px,1fr) 85px 20px;align-items:center;gap:12px;padding:15px 22px;border-bottom:1px solid var(--line)}.file-icon{width:38px;height:38px;display:grid;place-items:center;border-radius:9px}.file-icon.pdf{color:#b3414c;background:#fff0f1}.file-icon.xls{color:#167a58;background:#eaf7f1}.file-icon.zip{color:#9b6b1e;background:#fff5e2}.file-icon.img{color:#536e9e;background:#edf2fb}.evidence-row strong{font-size:12px}.evidence-row p{margin:4px 0 0;color:#8a96a3;font-size:9px}.purpose small,.purpose span{display:block}.purpose small{color:#909ba7;font-size:9px}.purpose span{margin-top:3px;color:#536173;font-size:10px}.quality{font-size:10px}.quality.good{color:#0c7f60}.quality.wait{color:#9c6b19}.quality.warn{color:#b1434e}.evidence-row>button{border:0;color:#98a2ad;background:transparent}@media(max-width:900px){.evidence-layout{grid-template-columns:1fr}.case-tree{display:none}.evidence-row{grid-template-columns:40px 1fr 80px 20px}.purpose{display:none}}@media(max-width:600px){.evidence-head{align-items:flex-start}.evidence-alert{grid-template-columns:auto 1fr}.evidence-alert button{display:none}.evidence-row{padding:13px 14px}.quality{display:none}.evidence-row{grid-template-columns:38px 1fr 20px}}
</style>
