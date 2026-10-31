/** K-only actual parser/display replay; stdin is public JSON, never code. */
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import * as strict from '../../../packages/regional-contracts/src/index.ts'
import * as display from '../../../frontend/src/data/regionalGuidePresentation.ts'
globalThis.fetch=()=>{throw new Error('K display replay forbids network/generation')}
const guides=JSON.parse(readFileSync(0,'utf8'))
assert.equal(guides.length,3)
const collection=display.readCollectionReport({openclaw:{status:'NO_EVENTS',pending_count:0,total_count:0,acknowledged_count:0,exported_count:0,ai_reviewed_count:0},categories:{},regions:guides})
assert.deepEqual(collection.regions.map(g=>g.province_name),['福建省','福建省','福建省'])
const identities={'350111':['晋安区','09dcedf106cd2fd411a09546'],'350121':['闽侯县','70d8f78ba93e94e9afecf7f3'],'350105':['马尾区','0aa50441bacd05b2245fb5f1']}
const aliases={'承诺办结时限':'承诺时限','法定办结时限':'法定时限','咨询方式':'联系电话','必须到现场原因':'必须现场办理原因','服务对象':'申报对象'}
const results=[]
for(const input of guides) {
 const [district,id]=identities[input.region_code]
 const guide=strict.assertRegionalGuide(input,{province:'fujian',city:'福州市',district}),view=display.readGuideDisplay(guide)
 assert.equal(guide.source_id,id);assert.equal(guide.can_generate,false);assert.equal(guide.published,false)
 assert.equal(guide.committee_full_name,null)
 const fields={}
 for(const [alias,raw] of Object.entries(aliases)) {
  fields[alias]=display.guideField(view,alias)
  assert.equal(fields[alias],guide.fields[raw].raw_value,`${district}: ${alias} must expose own ${raw}`)
  assert.deepEqual(guide.fields[alias],guide.fields[raw])
 }
 const labels=view.materials.map(m=>display.originalCopyLabel(m))
 assert.deepEqual(labels,['原件','原件','复印件'])
 assert.deepEqual(view.materials.map(m=>m.copies),[2,2,2])
 for(const [index,m] of view.materials.entries()) {
  assert.equal(m.paper_copies,2);assert.equal(m.copies_source_literal,index===2?'复印件份数2份':'原件份数2份')
  assert.match(m.raw_source_text,new RegExp(`材料类型：${labels[index]}`))
  assert.match(m.raw_source_text,new RegExp(m.copies_source_literal))
  const match=m.raw_source_text.match(/(?:^|\n)填报须知\t[ \t]*([\s\S]*?)(?=\n附件下载\t)/)
  if(match) {
   const ownInstruction=match[1].trim()
   assert.equal(m.instructions,ownInstruction)
   assert.equal(display.materialDetails(m)['填报须知'],ownInstruction)
   assert.equal(display.materialDetails(m)['填写与份数说明'],ownInstruction)
  } else {
   // Mawei's third own panel has no captured 填报须知; do not borrow another panel's text.
   assert.equal(m.instructions,'')
   assert.equal(display.materialDetails(m)['填写与份数说明'],undefined)
  }
 }
 assert.match(view.materials[0].instructions,/被申请人人数/)
 assert.match(view.materials[1].instructions,/当事人人数/)
 if(guide.region_code==='350121') {
  assert.equal(guide.fields['权责清单'].raw_value,'企业年金方案报备')
  assert.equal(guide.fields['权责清单'].normalized_value,null)
  assert.equal(guide.fields['权责清单'].verification_status,'unverified')
  assert.ok(view.warnings.includes('官网部分说明与此事项不一致，需向办理机构核对'))
 }
 const downloadable=view.templates.filter(t=>t.download_status==='downloaded')
 assert.equal(downloadable.length,guide.region_code==='350111'?2:1)
 assert.ok(view.templates.every(t=>t.can_generate===false))
 results.push({region_code:guide.region_code,source_id:id,fields,material_types:labels,copy_counts:view.materials.map(m=>m.copies),party_copy_remarks:view.materials.slice(0,2).map(m=>m.instructions),unadapted_evidence_generate:false})
}
console.log(JSON.stringify({scope:'K actual strict TypeScript parser/display, public JSON only; synthetic store version for replay',regions:results,network_requests:0,generation_posts:0}))
