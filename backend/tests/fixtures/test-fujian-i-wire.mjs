/** Fixed production TS parser/display regression. Stdin is JSON data only. */
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import * as strict from '../../../packages/regional-contracts/src/index.ts'
import * as display from '../../../frontend/src/data/regionalGuidePresentation.ts'
const wire=JSON.parse(readFileSync(0,'utf8'))
const identities=[['350103','台江区','dcf9b71dee1c1cb61a3af637',2],['350104','仓山区','9ab36db8d0ff985d9617a944',1]]
assert.equal(wire.regions.length,2)
assert.equal(display.readInventory(wire.inventory).items.length,2)
const examples=[],contracts=[]
globalThis.fetch=()=>{throw new Error('No automatic POST or fetch in form read/example/cancel')}
for(const [index,[code,district,source,copies]] of identities.entries()) {
  const region={province:'fujian',city:'福州市',district},row=wire.regions[index]
  const guide=strict.assertRegionalGuide(row.lookup,region),view=display.readGuideDisplay(guide)
  assert.equal(guide.source_id,source);assert.equal(guide.region_code,code)
  assert.equal(guide.published,false);assert.equal(guide.can_generate,true)
  assert.equal(view.verification_status,'partial');assert.deepEqual(view.materials.map(m=>m.copies),[copies,copies,copies])
  assert.equal(guide.committee_full_name,null);assert.equal(guide.channel.online_status,'auth_required')
  assert.equal(display.guideField(guide,'承诺办结时限'),'受理后5个工作日')
  for(const [j,kind] of ['application','evidence'].entries()) {
    const form=strict.assertFormContract(row.forms[j],{...region,region_code:code,source_id:source,version:guide.version,kind,mode:'blank',adapter:'fujian_taijiang_cangshan_own_blank_oct31i_v1'})
    assert.equal(form.context.schema_id,`fujian-i-${code}-${kind}-v1`)
    assert.equal(form.policy.text_controls,'newline_only')
    if(kind==='evidence')assert.equal(form.defaults.evidenceList.length,1)
    else assert.deepEqual(form.fields.map(f=>f.key),['applicantName','agentName','respondentName','requests','factsReason'])
    const example=strict.createExampleForm(form);assert.equal(strict.validateForm(form,example).valid,true)
    assert.match(JSON.stringify(example),/虚构/)
    examples.push(strict.buildGenerateRequest(form,example));contracts.push(form.contract_id)
    assert.throws(()=>strict.assertFormContract(form,{...form.context,district:identities[1-index][1]}))
  }
}
assert.equal(new Set(contracts).size,4)
console.log(JSON.stringify({examples,cancel_posts:0}))
