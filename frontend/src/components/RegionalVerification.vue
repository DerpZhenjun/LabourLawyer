<template>
  <section class="region-panel reviews" aria-labelledby="regional-reviews-title" data-regional-reviews>
    <div class="reviews-heading"><div><span class="ll-eyebrow">逐地查证 · 不计入已发布覆盖</span><h2 id="regional-reviews-title">逐地核验记录</h2></div><span class="reviews-count">本批 {{ items.length }} 地</span></div>
    <p>“尚未核验”“本次已查来源未找到”“官方明确未提供”分别记录。找到模板还需完成填写、版式与网页验收，才能开放生成。</p>
    <p class="reviews-scope">本批有空白申请书 {{ blankCount }} 地；官方明确未提供申请书 {{ absenceCount }} 地（仅限有原文声明的已查来源）。其他地区不因此标记为缺少模板。下列是采集复核记录，已发布范围仍以上方统计为准。</p>
    <label class="reviews-search">搜索地区<input v-model="query" type="search" aria-label="搜索逐地核验记录" placeholder="输入城市、区县或功能区名称" /></label>
    <p role="status" class="reviews-result">显示 {{ filtered.length }} 条核验记录</p>
    <ul v-if="filtered.length" class="reviews-list">
      <li v-for="row in filtered" :key="row.review_id" data-review-row>
        <div class="review-title"><h3>{{ provinceName(row.province) }} · {{ row.city }} · {{ row.district }}</h3><span>{{ row.guide_status==='candidate'?'已找到当地指南 · 待验收':'已查官方目录 · 指南待定位' }}</span></div>
        <dl><div><dt>仲裁申请书</dt><dd>{{ labels[row.application_template_status] }}</dd></div><div><dt>证据清单</dt><dd>{{ labels[row.evidence_template_status] }}</dd></div></dl>
        <p>{{ row.note }}</p>
        <details v-if="row.templates.length"><summary>查看已下载附件及原件校验值 · {{ row.templates.length }} 份</summary><div v-for="t in row.templates" :key="`${t.sha256}-${t.original_name}`" class="review-file"><strong>{{ t.original_name }}</strong><span>{{ {blank:'官方空白表格',sample:'官方填写样例',instruction:'材料说明'}[t.kind] }}</span><code>SHA256：{{ t.sha256 }}</code></div></details>
        <div class="review-source"><a :href="row.source_url" target="_blank" rel="noopener noreferrer">核对本地官方来源 ↗</a><span>核验 {{ date(row.checked_at) }}</span></div>
        <p v-if="row.authority" class="review-authority">办理机关：{{ row.authority }}</p>
      </li>
    </ul>
    <p v-else class="region-notice">尚未登记本批核验结果，不代表官方没有提供。历史发布状态请查看上方统计。</p>
  </section>
</template>
<script setup>
import {computed,ref} from 'vue'
import registry from '@/data/regionalVerification.json'
import {provinces} from '@/data/provinces'
const items=registry.items,query=ref('')
const labels={not_checked:'尚未核验',blank_found:'已找到并下载本地空白模板',sample_only:'仅查到本地填写样例',not_found_in_checked_sources:'本次已查来源未找到',officially_not_provided:'官方明确未提供（限已查来源）'}
const filtered=computed(()=>items.filter(r=>`${provinceName(r.province)} ${r.city} ${r.district}`.includes(query.value.trim())))
const blankCount=items.filter(r=>r.application_template_status==='blank_found').length
const absenceCount=items.filter(r=>r.application_template_status==='officially_not_provided').length
const provinceName=slug=>provinces.find(p=>p.slug===slug)?.name||slug
const date=value=>new Intl.DateTimeFormat('zh-CN',{year:'numeric',month:'2-digit',day:'2-digit',timeZone:'Asia/Shanghai'}).format(new Date(value))
</script>
<style scoped>
.reviews-heading,.review-title,.review-source{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}.reviews-count{border:1px solid var(--ll-border);border-radius:8px;padding:8px 12px;color:var(--ll-primary);font-size:14px}.reviews h2{margin:8px 0}.reviews-scope,.reviews-result,.review-authority{color:var(--ll-secondary);font-size:14px}.reviews-search{display:grid;gap:8px;max-width:420px;margin:24px 0 12px;font-weight:600}.reviews-search input{min-height:44px;width:100%;font:inherit;font-weight:400;color:var(--ll-text);border:1px solid var(--ll-border);border-radius:8px;padding:10px 12px;background:var(--ll-surface,#fff)}.reviews-list{list-style:none;padding:0;margin:0;display:grid;gap:16px}.reviews-list>li{border:1px solid var(--ll-border);border-radius:10px;padding:20px;min-width:0}.review-title h3{font-size:17px;margin:0}.review-title>span{font-size:13px;color:var(--ll-secondary)}.reviews dl{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:16px 0;background:var(--ll-background);border-radius:8px;padding:16px}.reviews dt{color:var(--ll-secondary);font-size:13px}.reviews dd{margin:6px 0 0;font-size:14px;font-weight:600}.reviews p{line-height:1.8}.reviews :is(p,code,h3,dd){overflow-wrap:anywhere}.reviews summary{min-height:44px;cursor:pointer;padding:12px 0;color:var(--ll-primary);font-size:14px}.review-file{display:grid;gap:6px;padding:12px 0;border-top:1px solid var(--ll-border);font-size:13px}.review-file code{font-size:12px;color:var(--ll-secondary)}.review-source a{display:inline-flex;align-items:center;min-height:44px;color:var(--ll-primary);font-weight:600;font-size:14px}.review-source>span{font-size:13px;color:var(--ll-secondary)}.review-authority{margin-bottom:0}.reviews :is(a,input,summary):focus-visible{outline:3px solid var(--ll-primary);outline-offset:3px}@media(max-width:600px){.reviews-list>li{padding:16px}.reviews dl{grid-template-columns:1fr}.review-title{align-items:flex-start;flex-direction:column}.review-source{align-items:flex-start;flex-direction:column;gap:0}}
</style>
