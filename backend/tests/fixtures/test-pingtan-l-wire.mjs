/** Actual Pingtan API JSON -> shared production TypeScript; never fetch. */
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import * as strict from '../../../packages/regional-contracts/src/index.ts'
import * as display from '../../../frontend/src/data/regionalGuidePresentation.ts'
globalThis.fetch=()=>{throw new Error('Offline Pingtan contract replay cannot request')}
const wire=JSON.parse(readFileSync(0,'utf8'))
const region={province:'fujian',city:'平潭综合实验区',district:'平潭综合实验区'}
const guide=strict.assertRegionalGuide(wire.guide,region),view=display.readGuideDisplay(guide)
assert.equal(guide.source_id,'511e7f64c9481b5a0b6ff4a1');assert.equal(guide.region_code,'350128')
assert.equal(guide.service_code,'1135012806039606XH300201430200201')
assert.equal(guide.authority,'平潭综合实验区社会事业局');assert.equal(guide.committee_full_name,null)
assert.equal(guide.published,false);assert.equal(guide.channel.online_status,'unverified')
assert.equal(guide.channel.entry_url,null);assert.equal(guide.channel.submission_verified,false)
assert.equal(view.materials.length,3);assert.deepEqual(view.materials.map(m=>m.copies),[2,2,2])
assert.deepEqual(view.materials.map(m=>display.originalCopyLabel(m)),['原件','原件','复印件'])
assert.equal(display.guideField(view,'承诺办结时限'),guide.fields['承诺时限'].raw_value)
assert.throws(()=>strict.assertRegionalGuide(guide,{...region,city:'福州市',district:'平潭县'}))
const examples=[]
for(const [i,kind] of ['application','evidence'].entries()) {
 const form=strict.assertFormContract(wire.forms[i],{...region,region_code:'350128',source_id:guide.source_id,version:guide.version,kind,adapter:'fujian_pingtan_own_blank_oct31l_v1',mode:'blank'})
 assert.equal(form.context.source_version,guide.source_version)
 assert.equal(form.context.schema_id,`fujian-l-350128-${kind}-v1`)
 if(kind==='evidence'){assert.equal(form.defaults.evidenceList.length,1);assert.equal(form.fields[0].maxItems,9)}
 const data=strict.createExampleForm(form)
 assert.match(JSON.stringify(data),/虚构/);assert.equal(strict.validateForm(form,data).valid,true)
 examples.push(strict.buildGenerateRequest(form,data))
 assert.throws(()=>strict.assertFormContract(form,{...form.context,source_id:'09dcedf106cd2fd411a09546'}))
}
assert.equal(new Set(examples.map(x=>x.contract_id)).size,2)
assert.equal(guide.templates.filter(t=>t.download_status==='metadata_only'&&!t.can_generate).length,4)
console.log(JSON.stringify({examples,network:0,cancel_posts:0,source_id:guide.source_id}))
