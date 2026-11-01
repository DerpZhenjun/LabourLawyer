/** P's actual ASGI JSON -> unchanged production validators/display; data stdin only. */
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {createHash} from 'node:crypto'
import * as strict from '../../../packages/regional-contracts/src/index.ts'
import * as display from '../../../frontend/src/data/regionalGuidePresentation.ts'
let fetchCalls=0
globalThis.fetch=()=>{fetchCalls++;throw new Error('P offline replay must not request')}
const wire=JSON.parse(readFileSync(0,'utf8'))
const identities=[
 {code:'350503',city:'泉州市',district:'丰泽区',id:'89a6739d1a513a7c5a77717a',service:'113505030038213221400201430200201',source:'0806ccef8ab4037d1f9a1f3bba41ea805c19c26ba247e920310db45757838a86',boundary:'https://fjzc.fjzhkj.cn:7881/'},
 {code:'350504',city:'泉州市',district:'洛江区',id:'4a34ce0e167250f122410ffc',service:'113505040038235128400201430200Y01',source:'d4faf4fbd11248451329370d55722f665bd09c9bd0144953c768360dc0517313',boundary:'https://iam.e-govt.cn:8901/login'}
]
const canonical=v=>Array.isArray(v)?v.map(canonical):v!==null&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v
const hash=v=>createHash('sha256').update(JSON.stringify(canonical(v))).digest('hex')
assert.equal(wire.cases.length,2)
const examples=[]
for(const [i,expected] of identities.entries()){
 const entry=wire.cases[i],region={province:'fujian',city:expected.city,district:expected.district}
 const guide=strict.assertRegionalGuide(entry.guide,region),view=display.readGuideDisplay(guide)
 assert.equal(guide.source_id,expected.id);assert.equal(guide.source_version,expected.source);assert.equal(guide.region_code,expected.code);assert.equal(guide.service_code,expected.service)
 assert.equal(guide.verification_status,'partial');assert.equal(guide.raw_verification_status,'observed_unverified');assert.equal(guide.published,false)
 assert.equal(guide.committee_full_name,null);assert.equal(guide.committee_name,null);assert.equal(guide.official_version,null)
 assert.equal(guide.online_boundary.origin_path,expected.boundary);assert.equal(view.channel.online_status,'auth_required');assert.equal(view.channel.entry_url,'');assert.equal(guide.channel.submission_verified,false)
 assert.equal(view.materials.length,3);assert.deepEqual(view.materials.map(m=>m.copies),['原件份数2份','原件份数2份','复印件份数2份'])
 for(const [j,m] of view.materials.entries()){
  assert.equal(m.id,expected.id+':dom-material:'+(j+1));assert.equal(m.material_id,null);assert.equal(m.official_material_id,null);assert.equal(m.legal_default_copies,null);assert.deepEqual(m.official_badges,[])
  assert.equal(m.required,m.raw_fields['材料必要性']);assert.equal(m.format,m.raw_fields['材料形式'])
  if(j<2)assert.match(display.materialDetails(m)['填写与份数说明'],/签字捺印/)
 }
 assert.equal(display.guideField(view,'办理形式'),guide.fields['办理形式'].raw_value)
 assert.equal(display.guideField(view,'承诺时限'),guide.fields['承诺时限'].raw_value)
 assert.deepEqual(view.sections,guide.sections)
 for(const field of Object.values(guide.fields)){assert.equal(field.normalized_value,null);assert.equal(field.verification_status,'observed_unverified');assert.equal(field.source_id,expected.id)}
 assert.throws(()=>strict.assertRegionalGuide(guide,{...region,district:identities[1-i].district}))
 for(const [index,kind] of ['application','evidence'].entries()){
  const form=strict.assertFormContract(entry.forms[index],{...region,region_code:expected.code,source_id:expected.id,version:guide.version,kind,adapter:'fujian_fengze_luojiang_own_blank_oct31p_v1',mode:'blank'})
  assert.equal(Object.keys(form.context).length,15);assert.equal(form.context.source_version,expected.source)
  assert.equal(form.context.schema_id,'private-quanzhou-p-own-'+expected.code+'-'+kind+'-v1')
  const body=Object.fromEntries(['schema_version','context','fields','defaults','policy'].map(k=>[k,form[k]]));assert.equal(hash(body),form.contract_id)
  assert.equal(form.policy.invalid_xml,'reject');assert.equal(form.policy.capacity_is_official_requirement,false)
  for(const f of form.fields){assert.equal(typeof f.label,'string');assert.ok(f.label);for(const item of f.fields??[])assert.ok(item.label)}
  if(kind==='evidence'){assert.equal(form.defaults.evidenceList.length,1);assert.equal(form.fields[0].maxItems,9);assert.equal(strict.validateForm(form,{evidenceList:[{name:'虚构',originalType:'副本'}]}).valid,false)}
  const data=strict.createExampleForm(form);assert.match(JSON.stringify(data),/虚构/);assert.equal(strict.validateForm(form,data).valid,true)
  assert.equal(strict.validateForm(form,{...data,signature:'不能代签'}).valid,false)
  const bad=structuredClone(form);delete bad.policy.invalid_xml;assert.throws(()=>strict.assertFormContract(bad,form.context))
  const unlabelled=structuredClone(form);delete unlabelled.fields[0].label;assert.throws(()=>strict.assertFormContract(unlabelled,form.context))
  assert.throws(()=>strict.assertFormContract(form,{...form.context,source_id:identities[1-i].id}))
  assert.throws(()=>strict.assertFormContract(form,{...form.context,source_id:'28a4418211ce36fedd8069f6'}))
  examples.push(strict.buildGenerateRequest(form,data))
 }
 assert.equal(guide.templates.filter(t=>t.download_status==='metadata_only'&&!t.can_generate).length,4)
 assert.equal(guide.templates.filter(t=>t.download_status==='downloaded'&&t.can_generate).length,2)
}
assert.equal(new Set(examples.map(x=>x.contract_id)).size,4);assert.equal(fetchCalls,0)
console.log(JSON.stringify({examples,fetch_calls:fetchCalls,sources:identities.map(i=>i.id)}))
