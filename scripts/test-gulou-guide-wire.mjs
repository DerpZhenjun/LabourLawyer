/** Fixed Gulou wire/display assertions against the actual production TS modules.
 * Stdin supplies JSON guide data only, never code, module paths or commands.
 */
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import * as strict from '../packages/regional-contracts/src/index.ts'
import * as display from '../frontend/src/data/regionalGuidePresentation.ts'

const data=JSON.parse(readFileSync(0,'utf8'))
const region={province:'fujian',city:'福州市',district:'鼓楼区'}
if(!Array.isArray(data)) {
  assert.equal(data.mode,'wire')
  const guide=strict.assertRegionalGuide(data.lookup,region)
  assert.equal(display.readGuideDisplay(guide).verification_status,'partial')
  assert.equal(guide.source_id,'3e2246aa2a534d2b37f6c6c5')
  assert.equal(guide.can_generate,true)
  assert.equal(guide.published,false)
  assert.deepEqual(display.readInventory(data.inventory).items.map(row=>row.region_code),['350102'])
  assert.equal(data.forms.length,2)
  const ids={application:'F4048D8C91E2FF882AC6C62CC0EC4D86',evidence:'CC300F5D9DD5DC404D65C68116D50C55'}
  const examples={}
  for(const [index,kind] of ['application','evidence'].entries()) {
    const form=strict.assertFormContract(data.forms[index],{...region,region_code:'350102',source_id:guide.source_id,
      version:guide.version,template_id:ids[kind],kind,mode:'blank',adapter:'fujian_gulou_own_blank_oct31h_v1'})
    assert.equal(form.policy.capacity_is_official_requirement,false)
    assert.equal(form.policy.text_controls,'newline_only')
    assert.deepEqual(form.fields.map(f=>f.key),kind==='application'
      ?['applicantName','agentName','respondentName','requests','factsReason']:['evidenceList'])
    if(kind==='evidence') {
      assert.equal(form.defaults.evidenceList.length,1)
      assert.deepEqual(form.fields[0].fields.map(f=>f.key),['name','pageCount','originalType','purpose','pageRange'])
    }
    const example=strict.createExampleForm(form)
    assert.equal(strict.validateForm(form,example).valid,true)
    assert.match(JSON.stringify(example),/虚构/)
    if(kind==='evidence')assert.equal(example.evidenceList.length,1)
    examples[kind]=strict.buildGenerateRequest(form,example)
    for(const change of [{schema_version:2},{defaults:{unexpected:''}}])
      assert.throws(()=>strict.assertFormContract({...form,...change},form.context))
  }
  console.log('PASS Gulou actual lookup/inventory/form contracts and shared fictional example requests')
  console.log(JSON.stringify({examples}))
  process.exit(0)
}
const guides=data
assert(Array.isArray(guides))
assert.equal(guides.length,3)
for(const [index,value] of guides.entries()) {
  const guide=strict.assertRegionalGuide(value,region)
  assert.equal(guide.source_id,'3e2246aa2a534d2b37f6c6c5')
  assert.equal(guide.region_code,'350102')
  assert.equal(guide.verification_status,'partial')
  assert.equal(guide.can_generate,index!==0)
  assert.equal(guide.published,index===2)
  assert.equal(display.readGuideDisplay(guide).source_id,guide.source_id)
  assert.equal(display.guideField(guide,'承诺时限'),'受理后5个工作日')
  assert.equal(display.guideField(guide,'咨询方式'),'0591-87710981')
  assert.equal(display.guideField(guide,'无来源字段'),'待核实')
  assert.deepEqual(display.readGuideDisplay(guide).materials.map(row=>row.copies),[2,2,2])
  assert.equal(display.hasGenerationKind(guide,'application'),index!==0)
  assert.equal(display.hasGenerationKind(guide,'evidence'),index!==0)
  assert.equal(guide.channel.online_status,'auth_required')
  const samples=guide.templates.filter(t=>t.official_kind==='sample')
  assert.equal(samples.length,3)
  for(const t of samples){assert.equal(t.can_generate,false);assert.deepEqual(t.document_types,[])}
  for(const change of [{sections:undefined},{district:'其他区'},{version:true}])
    assert.throws(()=>strict.assertRegionalGuide({...guide,...change},region))
}
console.log('PASS Gulou fixed source/stage/final wire and display replay; no browser/publication approval')
