/** Actual two-source N API JSON -> production TS only; stdin is data, never code. */
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {createHash} from 'node:crypto'
import * as strict from '../../../packages/regional-contracts/src/index.ts'
import * as display from '../../../frontend/src/data/regionalGuidePresentation.ts'
let fetchCalls=0
globalThis.fetch=()=>{fetchCalls++;throw new Error('Offline Putian replay cannot request')}
const wire=JSON.parse(readFileSync(0,'utf8'))
const identities=[
 {code:'350304',district:'荔城区',id:'c2f441391f073f71f55ce9de',service:'113503210037128046400201430200Y01',source:'d14f537bfd0137533112f380bf3e162f0207e23fe5aef75510db1a914a00cb91'},
 {code:'350305',district:'秀屿区',id:'758cc6043c5d57e5574a766e',service:'1135030448877165XX400201430200Y01',source:'9e3b53ede88fc12346504c94725d6a7987b8f263ac3caf3df51a1b1e2b11c96f'}
]
assert.equal(wire.cases.length,2)
const examples=[]
const canonical=value=>Array.isArray(value)?value.map(canonical):value!==null&&typeof value==='object'?Object.fromEntries(Object.keys(value).sort().map(key=>[key,canonical(value[key])])):value
for(const [i,expected] of identities.entries()) {
 const entry=wire.cases[i],region={province:'fujian',city:'莆田市',district:expected.district}
 const guide=strict.assertRegionalGuide(entry.guide,region),view=display.readGuideDisplay(guide)
 assert.equal(guide.source_id,expected.id);assert.equal(guide.region_code,expected.code)
 assert.equal(guide.service_code,expected.service);assert.equal(guide.source_version,expected.source);assert.equal(guide.committee_full_name,null);assert.equal(guide.official_version,null)
 assert.equal(guide.published,false);assert.equal(guide.channel.online_status,'auth_required');assert.equal(guide.channel.entry_url,null);assert.equal(guide.channel.submission_verified,false)
 assert.equal(view.materials.length,3);assert.deepEqual(view.materials.map(m=>m.copies),['原件份数2份','原件份数2份','复印件份数2份'])
 for(const [index,m] of view.materials.entries()){assert.equal(m.material_id,null);assert.equal(m.official_material_id,null);assert.equal(m.id,expected.id+':dom-material:'+(index+1))}
 assert.equal(display.guideField(view,'是否收费'),'不收费');assert.equal(display.guideField(view,'到办事现场次数'),'1 次')
 assert.equal(display.guideField(view,'承诺办结时限'),guide.fields['承诺时限'].raw_value)
 assert.throws(()=>strict.assertRegionalGuide(guide,{...region,district:identities[1-i].district}))
 for(const [index,kind] of ['application','evidence'].entries()){
  const form=strict.assertFormContract(entry.forms[index],{...region,region_code:expected.code,source_id:expected.id,version:guide.version,kind,adapter:'fujian_putian_licheng_xiuyu_own_blank_oct31n_v1',mode:'blank'})
  assert.equal(Object.keys(form.context).length,15);assert.equal(form.context.source_version,guide.source_version)
  assert.equal(form.context.schema_id,'fujian-n-'+expected.code+'-'+kind+'-v1')
  const body=Object.fromEntries(['schema_version','context','fields','defaults','policy'].map(key=>[key,form[key]]))
  assert.equal(createHash('sha256').update(JSON.stringify(canonical(body))).digest('hex'),form.contract_id)
  if(kind==='evidence'){assert.equal(form.defaults.evidenceList.length,1);assert.equal(form.fields[0].maxItems,9)}
  const data=strict.createExampleForm(form);assert.match(JSON.stringify(data),/虚构/);assert.equal(strict.validateForm(form,data).valid,true)
  assert.equal(strict.validateForm(form,{...data,signature:'禁止代签'}).valid,false)
  examples.push(strict.buildGenerateRequest(form,data))
  assert.throws(()=>strict.assertFormContract(form,{...form.context,source_id:identities[1-i].id}))
  assert.throws(()=>strict.assertFormContract(form,{...form.context,source_id:'28a4418211ce36fedd8069f6'}))
 }
 assert.equal(guide.templates.filter(t=>t.download_status==='metadata_only'&&!t.can_generate).length,4)
}
assert.equal(new Set(examples.map(x=>x.contract_id)).size,4);assert.equal(fetchCalls,0)
console.log(JSON.stringify({examples,fetch_calls:fetchCalls,sources:identities.map(i=>i.id)}))
