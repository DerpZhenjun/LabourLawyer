<template>
  <main id="main-content" tabindex="-1" class="regional-page ll-container">
    <nav class="region-breadcrumb" aria-label="当前位置"><RouterLink to="/">选择省份</RouterLink><span aria-hidden="true">/</span><span>{{ province?.name || '地区办理指南' }}</span></nav>
    <header class="region-heading"><div><span class="ll-eyebrow"><i class="fa-solid fa-location-dot" aria-hidden="true"></i> 填写文书 · 生成下载</span><h1>选好地区，开始填写文书</h1><p>选择你准备办理的地区，在下方填写申请书或证据清单。</p></div><span class="region-tool-note">劳动仲裁辅助工具<br>非官方政务服务网站</span></header>
    <section class="region-panel selector-panel" aria-labelledby="region-select-title">
      <h2 id="region-select-title">在哪里办理？</h2>
      <div class="region-selectors">
        <label>省份<select aria-label="办理省份" :value="region.province" @change="changeProvince(eventValue($event))"><option v-for="p in provinces" :key="p.slug" :value="p.slug">{{ p.name }}</option></select></label>
        <label>城市<input aria-label="办理城市" list="known-cities" placeholder="输入或选择城市" :value="region.city" @input="changePlace('city',eventValue($event))"></label>
        <label>区县<input aria-label="办理区县" list="known-districts" placeholder="输入或选择区县" :value="region.district" @input="changePlace('district',eventValue($event))"></label>
      </div>
      <datalist id="known-cities"><option v-for="city in cities" :key="city" :value="city" /></datalist><datalist id="known-districts"><option v-for="d in districts" :key="d" :value="d" /></datalist>
      <p class="region-small">这里选择的是办理地区，不是户籍所在地。是否由该机构受理，请向机构确认。</p>
      <p class="region-small" role="status" v-if="directoryLoading">正在读取官方地区目录…</p>
      <p class="region-small" role="status" v-else-if="directoryError">{{ directoryError }}</p>
      <details v-if="region.city && districtChoices.length && !(region.province==='sichuan' && region.city==='成都市')" class="region-directory">
        <summary>查看本市全部区县与功能区 · {{ districtChoices.length }} 个地区</summary>
        <label>选择本市区县或功能区<select aria-label="选择本市区县或功能区" :value="region.district" @change="changePlace('district',eventValue($event))"><option value="" disabled>选择准备办理的地区</option><option v-for="a in districtChoices" :key="a.district" :value="a.district">{{ a.district }} · {{ a.can_generate?'可填写生成':a.source_id?'已收录指南':'待核验' }}</option></select></label>
        <p class="region-small">目录收录不代表文书已支持。“待核验”不会套用其他地区的资料；你也可以在上方直接输入地区名称。</p>
      </details>
      <div class="region-examples" v-if="region.province==='sichuan' && (!region.city || region.city==='成都市')"><span>常用成都入口：</span><button v-for="d in ['天府新区','锦江区','武侯区']" :key="d" type="button" :aria-pressed="region.city==='成都市' && region.district===d" @click="selectExample(d)">{{ d }}</button></div>
      <details v-if="region.province==='sichuan' && (!region.city || region.city==='成都市') && chengduAreas.length" class="region-directory">
        <summary>查看成都全部 {{ chengduAreas.length }} 个地区</summary>
        <label>选择成都区县<select aria-label="选择成都区县" :value="region.city==='成都市'?region.district:''" @change="selectExample(eventValue($event))"><option value="" disabled>选择准备办理的区县</option><option v-for="a in chengduAreas" :key="a.region_code" :value="a.district">{{ a.district }} · {{ a.can_generate?'可填写生成':a.source_id?'已收录指南':'待核验' }}</option></select></label>
        <p class="region-small">“可填写生成”依据当地官网参考样表，不保证受理；“待核验”不会套用其他区县资料。功能区名称与编码保留官网标注。</p>
      </details>
    </section>
    <DocumentWorkspace :region="region" :province="province" :guide="guide" :loading="loading" :error="error" />
    <p v-if="loading" class="region-panel" role="status">正在读取这个地区的指南…</p>
    <div v-else-if="error" class="region-notice danger" role="alert"><p>{{ error }}</p><button class="ll-button secondary" @click="reload">重新读取</button></div>
    <section v-else-if="!guide?.source_id" class="region-panel empty-guide" data-guide-state="unverified">
      <i class="fa-regular fa-compass" aria-hidden="true"></i><h2>{{ region.city && region.district ? '该地区办事指南尚未核验' : '请选择城市和区县' }}</h2><p>不会用其他地区的材料和办理要求代替。你仍可以打开官网查询，或查看已有文书的具体适用范围。</p>
      <div class="region-actions"><a v-if="province?.officialUrl" :href="province.officialUrl" target="_blank" rel="noopener noreferrer" class="ll-button secondary">打开已收录的官方来源 ↗</a><RouterLink :to="`/province/${region.province}/templates`" class="ll-button secondary">已有文书及适用范围</RouterLink></div>
    </section>
    <div v-else :data-source-id="guide.source_id" :data-region-code="guide.region_code" class="verified-guide">
      <section class="region-panel guide-overview" id="regional-overview">
        <div class="guide-title-row"><span class="ll-eyebrow">{{ province?.name }} · {{ guide.city }} · {{ guide.district }}</span><span class="region-badge" :class="{'caution':guide.verification_status!=='verified'}">{{ guide.verification_status==='conflict'?'部分信息有冲突':guide.verification_status==='partial'?'部分内容待核实':'已核对公开指南' }}</span></div>
        <h2>{{ guide.service_name }}</h2><p class="region-authority">办理机关：{{ guide.authority || '待核实' }}</p>
        <dl class="guide-facts"><div><dt><i class="fa-solid fa-building" aria-hidden="true"></i> 办理形式</dt><dd data-field="handling-form">{{ field('办理形式') }}</dd></div><div><dt>官网显示的办理时限</dt><dd>{{ field('承诺办结时限') }}</dd></div><div><dt>是否收费</dt><dd>{{ field('是否收费') }}</dd></div><div><dt>到现场次数</dt><dd>{{ visitCountLabel(guide) }}</dd></div></dl>
        <p class="region-small">这里的时限是官网事项办理信息，不表示争议案件将在这个时间内裁决。</p>
        <div v-for="warning in guide.warnings" :key="warning" class="region-notice" role="note"><i class="fa-solid fa-circle-exclamation" aria-hidden="true"></i><p>{{ plainWarning(warning) }}</p></div>
        <div class="guide-source"><a :href="guide.source_url" target="_blank" rel="noopener noreferrer">核对官方原文 ↗</a><span>核验：{{ date(guide.verified_at) }} · 官网版本 {{ guide.official_version || '未提供' }}</span></div>
      </section>
      <nav class="guide-jumps" aria-label="指南内容"><a href="#regional-submit">怎样提交</a><a href="#regional-materials">准备材料</a><a href="#regional-documents">文书与下载</a><a href="#regional-original">完整原文</a></nav>
      <section class="region-panel" id="regional-submit">
        <span class="ll-eyebrow">01 · 怎样提交</span><h2>{{ guide.channel.online_status==='unavailable'?'带材料到窗口办理':'先核对办理渠道' }}</h2>
        <p v-if="guide.channel.online_status==='unavailable'" data-channel-state="unavailable">当前核验的官方办事指南显示，该事项采用窗口办理方式，是否网办为“否”。这不是网站故障。</p>
        <div v-else-if="['auth_required','verified'].includes(guide.channel.online_status)" :data-channel-state="guide.channel.online_status"><p v-if="onlineEntry?.direct">{{ guide.channel.online_status==='auth_required'?'官网明确列出网上办理。实际点击入口后需要登录，我们已停止操作；请你自行在官网登录，不在本平台提交申请。':'已核验官网公开网上入口，后续申请由你在官网自行完成。' }}</p><p v-else>本页未提供已核验的直达入口。请核对官方指南中的网上入口、登录要求和后续流程，或向办理机关确认。</p><a v-if="onlineEntry" class="ll-button" :href="onlineEntry.href" target="_blank" rel="noopener noreferrer" data-online-entry>{{ onlineEntry.direct?(guide.channel.online_status==='auth_required'?'打开官网，登录后选择在线申请':'打开官方网上入口'):'打开官方指南，核对在线入口' }} ↗</a></div>
        <p v-else class="region-notice" :data-channel-state="guide.channel.online_status">网上办理情况待核实。{{ guide.channel.online_status==='conflict'?'官网不同栏目说法不一致。':'没有核实到有效入口，不代表当地一定不支持网上办理。' }}{{ guide.channel.entry_check?.status==='http_502'?'流程中的入口本次访问返回 HTTP 502。':'' }}请先向办理机关确认。</p>
        <dl class="window-details"><div><dt>窗口地点</dt><dd>{{ field('办理地点') }}</dd></div><div><dt>办公时间</dt><dd>{{ field('办理时间') }}</dd></div><div><dt>咨询电话</dt><dd>{{ field('咨询方式') }}</dd></div><div><dt>必须到现场原因</dt><dd>{{ field('必须到现场原因') }}</dd></div><div><dt>服务对象</dt><dd>{{ field('服务对象') }}</dd></div></dl>
      </section>
      <section class="region-panel" id="regional-materials"><span class="ll-eyebrow">02 · 准备材料</span><h2>这份当地指南列出的材料</h2><p>下面保留官网名称和份数。签字、复印和其他情形请同时核对详细说明。</p>
        <div class="regional-material" v-for="(m,index) in guide.materials" :key="m.id"><div class="material-top"><span class="material-number">{{ index+1 }}</span><div><h3>{{ m.name }}</h3><p>{{ m.required || '是否必需待核实' }} · {{ originalCopyLabel(m) }} · {{ m.format || '形式待核实' }} · {{ materialCopiesLabel(m.copies) }}</p><p v-for="badge in m.official_badges || []" :key="badge" class="region-small">官网另有标记“{{ badge }}”，适用条件尚待确认；不要据此自行省略这项材料。</p></div></div><details><summary>查看这项材料的详细要求</summary><p class="region-small">材料用途与适用情形：{{ m.purpose || '官网未单列说明，待核实；不要自行省略必要材料。' }}</p><dl class="window-details"><div v-for="(value,key) in materialDetails(m)" :key="key"><dt>{{ key }}</dt><dd>{{ value || '官网未填写，待核实' }}</dd></div></dl></details></div>
        <p v-if="!guide.materials.length" class="region-notice">材料清单尚未核验，不显示确定的当地要求。</p>
      </section>
      <section class="region-panel" id="regional-documents"><span class="ll-eyebrow">03 · 文书与下载</span><h2>看清来源，再填写</h2><p>“空白表格”和“示例样表”不是一回事。下载保留官网原文件，辅助填写不保证受理。</p>
        <div class="regional-template" v-for="t in guide.templates" :key="t.id"><i class="fa-regular fa-file-lines" aria-hidden="true"></i><div><h3>{{ t.original_name }}</h3><p>{{ t.official_kind==='blank'?'官方空白表格':t.official_kind==='sample'?'官方示例样表（不是空白模板）':'附件类型待核实' }}</p><details><summary>来源与文件校验</summary><p>适用地区编码：{{ t.region_code }}</p><p class="file-hash">SHA256：{{ t.sha256 || '未下载，待核验' }}</p><a :href="t.source_url" target="_blank" rel="noopener noreferrer">官方材料栏目 ↗</a></details></div><a v-if="t.download_status==='downloaded'" class="ll-button secondary" :href="originalTemplateLink(t.id)">下载原文件</a><span v-else>下载待核验</span></div>
        <div v-if="generatable" class="reference-fill"><h3>按{{ guide.district }}{{ blankGeneration?'官方空白表格':'参考样表' }}辅助填写</h3><p>{{ blankGeneration?'当前填写使用本地区官网提供、已核对的空白表格。':'官网将申请书附件列为示例样表。' }}页面上方可以直接填写；默认内容为本平台虚构示例，请替换为真实信息。签名位置留空，不自动提交申请。</p><div class="region-actions"><RouterLink v-if="hasGenerationKind(guide,'application')" :to="documentLink('application')" class="ll-button">填写申请书</RouterLink><RouterLink v-if="hasGenerationKind(guide,'evidence')" :to="documentLink('evidence')" class="ll-button secondary">填写证据清单</RouterLink></div></div>
        <p v-else class="region-notice">本地区附件尚未通过自动填写核验，{{ guide.templates.some(t=>t.download_status==='downloaded')?'可下载上方已核实的原文件参考。':'尚未核实可下载文件，请打开官方原文查询或向办理机构确认。' }}不会套用其他地区的文书。</p>
      </section>
      <section class="region-panel" id="regional-original"><span class="ll-eyebrow">04 · 完整原文</span><h2>核对受理条件和其他说明</h2><details v-for="(text,name) in guide.sections" :key="name" class="original-section"><summary>{{ guideSectionLabel(name) }}</summary><p class="official-raw">{{ text || '官网未提供，待核实' }}</p></details><p class="region-small">原文来自本次公开页面采集。页面内容更新后，应再次核验；不能替代办理机构对管辖、材料和受理条件的判断。</p></section>
    </div>
    <p class="region-disclaimer">LabourLawyer 是劳动仲裁辅助工具，不是政府网站，不收取或代交仲裁申请。已有模板仅在标注的来源范围内使用。</p>
  </main>
</template>
<script setup lang="ts">
import {guideField,visitCountLabel,originalCopyLabel,materialCopiesLabel,guideSectionLabel,materialDetails,hasGenerationKind,readGuideDisplay,publicError} from '@/data/regionalGuidePresentation'
import type {DirectoryArea} from '@/data/regionalGuidePresentation'
import {plainGuideWarning} from '../../../packages/regional-contracts/src/index.ts'
import type {DocumentKind} from '../../../packages/regional-contracts/src/index.ts'
import {publicClient} from '@/api/public'
import {computed,ref,onMounted,onBeforeUnmount} from 'vue'
import {useRoute,useRouter,RouterLink} from 'vue-router'
import {provinces,findProvince} from '@/data/provinces'
import {useRegionalGuide,templateURL} from '@/composables/useRegionalGuide'
import DocumentWorkspace from '@/components/DocumentWorkspace.vue'
import {useRegionDirectory} from '@/composables/useRegionDirectory'
import '@/regional-guide.css'
const route=useRoute(),router=useRouter(),inventory=ref<DirectoryArea[]>([]),coverage=ref<DirectoryArea[]>([])
const region=computed(()=>({province:String(route.params.slug||''),city:String(route.query.city||''),district:String(route.query.district||'')}))
const province=computed(()=>findProvince(region.value.province))
const {guide:rawGuide,loading,error:lookupError,reload}=useRegionalGuide(region)
const presentation=computed(()=>{try{return{guide:readGuideDisplay(rawGuide.value),error:''}}catch(cause:unknown){return{guide:null,error:publicError(cause)}}})
const guide=computed(()=>presentation.value.guide),error=computed(()=>lookupError.value||presentation.value.error)
function officialOnlineLink(entry:unknown,source:unknown):{href:string;direct:boolean}|null {
  const absent=entry===undefined||entry===null||typeof entry==='string'&&!entry.trim()
  const value=absent?source:entry
  if(typeof value!=='string'||!value.trim())return null
  try {
    const url=new URL(value)
    if(!['https:','http:'].includes(url.protocol)||!url.hostname.endsWith('.gov.cn')||url.username||url.password)return null
    return{href:url.href,direct:!absent}
  }catch{return null}
}
const onlineEntry=computed(()=>guide.value?officialOnlineLink(guide.value.channel.entry_url,guide.value.source_url):null)
const {cityAreas,districtAreas,directoryLoading,directoryError}=useRegionDirectory(region)
const cities=computed(()=>[...new Set([...cityAreas.value,...inventory.value.filter(g=>g.province===region.value.province)].map(g=>g.city))])
const districts=computed(()=>[...new Set([...inventory.value,...coverage.value,...districtAreas.value].filter(g=>g.province===region.value.province&&g.city===region.value.city).map(g=>g.district))])
const districtChoices=computed(()=>{
  const result=new Map<string,DirectoryArea>()
  for(const area of districtAreas.value){
    const previous=result.get(area.district)
    result.set(area.district,{...area,can_generate:Boolean(area.can_generate||previous?.can_generate),source_id:area.source_id||previous?.source_id||null})
  }
  return [...result.values()]
})
const chengduAreas=computed(()=>coverage.value.filter(g=>g.province==='sichuan'&&g.city==='成都市'))
const generatable=computed(()=>guide.value?.templates.some(t=>t.can_generate))
const blankGeneration=computed(()=>guide.value?.templates.filter(t=>t.can_generate).every(t=>t.official_kind==='blank'))
const plainWarning=(value:unknown)=>plainGuideWarning(String(value)).replaceAll('not_found_in_checked_sources','本次已查来源未找到').replaceAll('NOT_RUN','尚未核验')
const field=(name:string)=>guideField(guide.value,name)
const date=(value:string)=>value?new Date(value).toLocaleString('zh-CN',{hour12:false}):'待核实'
const eventValue=(event:Event)=>event.target instanceof HTMLInputElement||event.target instanceof HTMLSelectElement?event.target.value:''
const changeProvince=(slug:string)=>router.replace({path:`/province/${slug}`,query:{}})
const changePlace=(key:'city'|'district',value:string)=>router.replace({query:{...route.query,[key]:value,...(key==='city'?{district:''}:{})}})
const selectExample=(district:string)=>router.replace({query:{city:'成都市',district}})
const documentLink=(kind:DocumentKind)=>({path:`/local-documents/${region.value.province}/${kind}`,query:{city:region.value.city,district:region.value.district}})
const originalTemplateLink=(id:string)=>{
  const current=guide.value
  return current?.source_id&&typeof current.version==='number'&&Number.isSafeInteger(current.version)&&current.version>0?templateURL(region.value,id,{source_id:current.source_id,version:current.version}):undefined
}
const controller=new AbortController()
onMounted(async()=>{try{const result=await publicClient.inventory(controller.signal);if(!controller.signal.aborted){inventory.value=result.items;coverage.value=result.coverage}}catch{/* Lookup presents a retryable error; suggestions are optional. */}})
onBeforeUnmount(()=>controller.abort())
</script>
