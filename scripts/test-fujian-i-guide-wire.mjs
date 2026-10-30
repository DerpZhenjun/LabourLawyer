/** Fixed I guide assertions; stdin is JSON data, never code or module paths. */
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import * as strict from '../packages/regional-contracts/src/index.ts'
import * as display from '../frontend/src/data/regionalGuidePresentation.ts'

const guides=JSON.parse(readFileSync(0,'utf8'))
assert(Array.isArray(guides))
assert.equal(guides.length,8)
const regions={
  '350103':{district:'台江区',source:'dcf9b71dee1c1cb61a3af637',copies:2},
  '350104':{district:'仓山区',source:'9ab36db8d0ff985d9617a944',copies:1},
}
for(const [index,value] of guides.entries()) {
  const own=regions[value.region_code]
  assert(own)
  const region={province:'fujian',city:'福州市',district:own.district}
  const guide=strict.assertRegionalGuide(value,region)
  const presented=display.readGuideDisplay(guide)
  assert.equal(guide.source_id,own.source)
  assert.equal(guide.verification_status,'partial')
  assert.equal(guide.can_generate,index>=2)
  assert.equal(guide.published,index>=6)
  assert.equal(presented.source_id,own.source)
  assert.equal(display.guideField(guide,'承诺办结时限'),'受理后5个工作日')
  assert.equal(display.guideField(guide,'法定办结时限'),'受理后5个工作日')
  assert.equal(display.guideField(guide,'是否收费'),'不收费')
  assert.equal(display.guideField(guide,'不存在的来源字段'),'待核实')
  assert.match(display.guideField(guide,'办理地点'),new RegExp(own.district))
  assert.deepEqual(presented.materials.map(row=>row.copies),[own.copies,own.copies,own.copies])
  assert.equal(guide.channel.online_status,'auth_required')
  for(const t of guide.templates.filter(t=>t.official_kind==='sample'||t.content_role==='scanning_instructions_only')) {
    assert.equal(t.can_generate,false)
    assert.deepEqual(t.document_types,[])
  }
  for(const change of [{sections:undefined},{version:true},{district:'鼓楼区'}])
    assert.throws(()=>strict.assertRegionalGuide({...guide,...change},region))
}
console.log('PASS I own source/offline/stage/final actual strict TS guide/display replay; no live/browser approval')
