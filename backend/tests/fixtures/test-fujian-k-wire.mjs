/** Actual K staged ASGI JSON -> production TS contracts/examples; no fetch. */
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import * as strict from '../../../packages/regional-contracts/src/index.ts'
import * as display from '../../../frontend/src/data/regionalGuidePresentation.ts'
globalThis.fetch=()=>{throw new Error('K reads/examples/cancel must not send requests')}
const wire=JSON.parse(readFileSync(0,'utf8'))
const expected=[['350111','晋安区','09dcedf106cd2fd411a09546'],['350121','闽侯县','70d8f78ba93e94e9afecf7f3'],['350105','马尾区','0aa50441bacd05b2245fb5f1']]
assert.equal(wire.regions.length,3);assert.equal(display.readInventory(wire.inventory).items.length,3)
const examples=[],contracts=[]
for(const [i,[code,district,id]] of expected.entries()) {
 const region={province:'fujian',city:'福州市',district},row=wire.regions[i]
 const guide=strict.assertRegionalGuide(row.lookup,region),view=display.readGuideDisplay(guide)
 assert.equal(guide.source_id,id);assert.equal(guide.region_code,code)
 assert.equal(guide.published,false);assert.equal(guide.can_generate,true);assert.equal(guide.publication_status,'staged_own_word_qa')
 assert.equal(guide.committee_full_name,null);assert.equal(guide.committee_autofill_allowed,false)
 assert.deepEqual(view.materials.map(m=>display.originalCopyLabel(m)),['原件','原件','复印件'])
 assert.deepEqual(view.materials.map(m=>m.copies),[2,2,2]);assert.match(view.materials[0].instructions,/被申请人人数/)
 assert.equal(display.guideField(guide,'承诺办结时限'),guide.fields['承诺时限'].raw_value)
 const kinds=code==='350111'?['application','evidence']:['application']
 assert.equal(row.forms.length,kinds.length)
 for(const [j,kind] of kinds.entries()) {
  const form=strict.assertFormContract(row.forms[j],{...region,region_code:code,source_id:id,version:guide.version,kind,mode:'blank',adapter:'fujian_three_own_blank_oct31k_v1'})
  assert.equal(form.context.schema_id,`fujian-k-${code}-${kind}-v1`)
  assert.equal(form.context.source_version,guide.source_version)
  assert.equal(form.policy.text_controls,'newline_only');assert.equal(form.policy.trim_text,true)
  if(kind==='evidence') {assert.equal(form.fields[0].maxItems,9);assert.equal(form.defaults.evidenceList.length,1)}
  else assert.deepEqual(form.fields.map(f=>f.key),['applicantName','agentName','respondentName','requests','factsReason'])
  const example=strict.createExampleForm(form);assert.equal(strict.validateForm(form,example).valid,true);assert.match(JSON.stringify(example),/虚构/)
  examples.push(strict.buildGenerateRequest(form,example));contracts.push(form.contract_id)
  assert.throws(()=>strict.assertFormContract(form,{...form.context,source_id:expected[(i+1)%3][2]}))
 }
 if(code!=='350111')assert.equal(guide.templates.filter(t=>t.can_generate).flatMap(t=>t.document_types).includes('evidence'),false)
 assert.equal(guide.templates.filter(t=>t.download_status==='metadata_only').length,code==='350111'?4:5)
 if(code==='350121') {assert.equal(guide.fields['权责清单'].normalized_value,null);assert.equal(guide.fields['权责清单'].verification_status,'unverified')}
}
assert.equal(new Set(contracts).size,4)
console.log(JSON.stringify({scope:'actual K staged ASGI -> production TS -> four fictional requests; no publication',examples,cancel_posts:0,network_requests:0}))
