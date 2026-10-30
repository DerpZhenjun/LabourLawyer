/** Fixed J production parser/display/form assertions; stdin is JSON data only. */
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import * as strict from '../../../packages/regional-contracts/src/index.ts'
import * as display from '../../../frontend/src/data/regionalGuidePresentation.ts'
const wire=JSON.parse(readFileSync(0,'utf8'))
const identities=[
  ['350122','连江县','bca45154d74905b963af83c9'],['350123','罗源县','e6dccff3468cba55aa9b5c09'],
  ['350124','闽清县','4d74f378197bace2e63b05e9'],['350125','永泰县','3bfbebb0f7115a969c3d77be'],
  ['350181','福清市','9af3a0528483a9bb4fb67de5'],['350182','长乐区','e0b2adc9b9b0b10bc0eb9332'],
]
assert.equal(wire.regions.length,6)
assert.equal(display.readInventory(wire.inventory).items.length,6)
const examples=[],contracts=[]
globalThis.fetch=()=>{throw new Error('Reads/examples/cancel must not perform automatic fetch or POST')}
for(const [index,[code,district,source]] of identities.entries()) {
  const region={province:'fujian',city:'福州市',district},row=wire.regions[index]
  const guide=strict.assertRegionalGuide(row.lookup,region),view=display.readGuideDisplay(guide)
  assert.equal(guide.source_id,source);assert.equal(guide.region_code,code)
  assert.equal(guide.published,false);assert.equal(guide.can_generate,true)
  assert.equal(view.verification_status,'partial');assert.deepEqual(view.materials.map(m=>m.copies),[2,2,2])
  assert.equal(guide.committee_full_name,null);assert.equal(guide.channel.online_status,'auth_required')
  assert.equal(guide.channel.entry_url,null)
  assert.equal(view.materials[0].name,'仲裁申请书')
  assert.match(view.materials[0].instructions,/签字/)
  if(code==='350124')assert.match(guide.service_code,/202$/)
  if(code==='350182')assert.equal(guide.channel.observed_entry_url,'https://iam.e-govt.cn:8901/login')
  const kinds=code==='350125'?['application']:['application','evidence']
  assert.equal(row.forms.length,kinds.length)
  for(const [j,kind] of kinds.entries()) {
    const form=strict.assertFormContract(row.forms[j],{...region,region_code:code,source_id:source,version:guide.version,kind,mode:'blank',adapter:'fujian_six_own_blank_oct31j_v1'})
    assert.equal(form.context.schema_id,`fujian-j-${code}-${kind}-v1`)
    assert.equal(form.context.source_version,guide.source_version)
    assert.equal(form.policy.text_controls,'newline_only')
    if(kind==='evidence') {
      assert.equal(form.defaults.evidenceList.length,1)
      if(code==='350182') {
        assert.equal(form.context.template_id,'C0D98561149170947B4366BCA0299DD9')
        assert.equal(form.context.template_sha256,'511d213073af6e25b0f9f8ed2b914b7b31ee47bf6cef2fbb85a0422e3d6a4f56')
      }
    } else assert.deepEqual(form.fields.map(f=>f.key),['applicantName','agentName','respondentName','requests','factsReason'])
    const example=strict.createExampleForm(form);assert.equal(strict.validateForm(form,example).valid,true)
    assert.match(JSON.stringify(example),/虚构/)
    examples.push(strict.buildGenerateRequest(form,example));contracts.push(form.contract_id)
    assert.throws(()=>strict.assertFormContract(form,{...form.context,district:identities[(index+1)%6][1]}))
  }
}
assert.equal(new Set(contracts).size,11)
console.log(JSON.stringify({examples,cancel_posts:0}))
