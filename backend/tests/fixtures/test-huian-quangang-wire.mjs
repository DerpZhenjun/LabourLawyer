/** Own ASGI data through the unchanged shared three-client contract and web display. */
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {createHash} from 'node:crypto'
import * as strict from '../../../packages/regional-contracts/src/index.ts'
import * as display from '../../../frontend/src/data/regionalGuidePresentation.ts'

let fetchCalls=0
globalThis.fetch=()=>{fetchCalls++;throw new Error('Own HQ offline replay must not request')}
const input=JSON.parse(readFileSync(0,'utf8'))
const identities=[
 {code:'350521',district:'惠安县',id:'5a2049b6dd7a240d496c29d7',source:'4a9697f5ea943d6dc02b5a9361da7bf6639a50cd6c76f357aa01d68686d4178b',app:'9D2094A6856CE70EEFB065965B549417',evidence:'3C7BF28B410DDBA48A6246EAFD4123C0'},
 {code:'350505',district:'泉港区',id:'4f9f8144ec2ae19a7f2e70cf',source:'c3d3dc26535ed2df27d53d4ad4f3fb723e1bfb740fa2ee6926c4a550783a6267',app:'AC4FB9C53EA01E760AAA60964DA50D65',evidence:'16BFF472076352C1A92C3BBA1E6921C1'}
]
const canonical=v=>Array.isArray(v)?v.map(canonical):v!==null&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v
const digest=v=>createHash('sha256').update(JSON.stringify(canonical(v))).digest('hex')
assert.equal(input.cases.length,2)
const examples=[]
let rejectedContexts=0
for(const [index,expected] of identities.entries()){
 const entry=input.cases[index],region={province:'fujian',city:'泉州市',district:expected.district}
 const guide=strict.assertRegionalGuide(entry.guide,region),view=display.readGuideDisplay(guide)
 assert.equal(guide.region_code,expected.code);assert.equal(guide.source_id,expected.id);assert.equal(guide.source_version,expected.source)
 assert.equal(guide.official_version,'1');assert.equal(guide.published,false);assert.equal(guide.committee_full_name,null);assert.equal(guide.committee_autofill_allowed,false)
 assert.equal(view.channel.raw_value,'窗口办，网上办，邮寄办');assert.equal(view.channel.online_status,'auth_required');assert.equal(view.channel.entry_url,'')
 assert.equal(guide.channel.online_depth_raw,'材料预审（Ⅱ级）');assert.deepEqual(guide.channel.service_linked_accept_types,['02']);assert.equal(guide.channel.submission_verified,false)
 assert.equal(view.materials.length,3)
 for(const material of view.materials){
  assert.ok(material.official_material_id);assert.equal(material.source_id,expected.id);assert.equal(material.legal_default_copies,null)
  assert.equal(material.format,material.raw_fields.medium)
  assert.equal(material.copies,material.raw_fields.medium+(material.raw_fields.medium==='原件'?material.raw_fields.pagenum:material.raw_fields.pagecopynum)+'份')
  if(material.instructions)assert.equal(display.materialDetails(material)['填写与份数说明'],material.instructions)
  else assert.equal(display.materialDetails(material)['填写与份数说明'],undefined)
 }
 for(const field of Object.values(guide.fields)){assert.equal(field.normalized_value,null);assert.equal(field.verification_status,'observed_unverified');assert.equal(field.source_id,expected.id);assert.equal(field.region_code,expected.code);assert.equal(field.verified_at,null)}
 assert.equal(display.guideField(view,'到办事现场次数'),'1')
 assert.equal(guide.templates.filter(t=>t.download_status==='metadata_only'&&!t.can_generate).length,4)
 assert.equal(guide.templates.filter(t=>t.download_status==='downloaded'&&t.can_generate).length,2)
 assert.throws(()=>strict.assertRegionalGuide(guide,{...region,district:identities[1-index].district}))
 for(const [formIndex,kind] of ['application','evidence'].entries()){
  const form=strict.assertFormContract(entry.forms[formIndex],{...region,region_code:expected.code,source_id:expected.id,version:guide.version,kind,mode:'blank',adapter:'fujian_huian_quangang_own_api_nov1_v1'})
  assert.equal(Object.keys(form.context).length,15);assert.equal(form.context.source_version,expected.source)
  assert.equal(form.context.template_id,kind==='application'?expected.app:expected.evidence)
  assert.equal(form.context.schema_id,'fujian-huian-quangang-'+expected.code+'-'+kind+'-v1')
  assert.equal(digest(Object.fromEntries(['schema_version','context','fields','defaults','policy'].map(k=>[k,form[k]]))),form.contract_id)
  assert.equal(form.policy.invalid_xml,'reject');assert.equal(form.policy.capacity_is_official_requirement,false);assert.equal(form.policy.committee_autofill_allowed,false)
  for(const field of form.fields){assert.ok(field.label);for(const child of field.fields??[])assert.ok(child.label)}
  if(kind==='evidence')assert.equal(form.defaults.evidenceList.length,1)
  const data=strict.createExampleForm(form);assert.match(JSON.stringify(data),/虚构/);assert.equal(strict.validateForm(form,data).valid,true)
  assert.equal(strict.validateForm(form,{...data,signature:'不代签'}).valid,false)
  for(const key of Object.keys(form.context)){
   assert.throws(()=>strict.assertFormContract(form,{...form.context,[key]:null}));rejectedContexts++
  }
  examples.push(strict.buildGenerateRequest(form,data))
 }
}
assert.equal(new Set(examples.map(x=>x.contract_id)).size,4);assert.equal(fetchCalls,0);assert.equal(rejectedContexts,60)
console.log(JSON.stringify({examples,fetch_calls:fetchCalls,rejected_contexts:rejectedContexts,sources:identities.map(x=>x.id)}))
