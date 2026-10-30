/** Fixed J source/offline/stage wire replay; stdin JSON cannot supply code. */
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import * as strict from '../packages/regional-contracts/src/index.ts'
import * as display from '../frontend/src/data/regionalGuidePresentation.ts'
const guides=JSON.parse(readFileSync(0,'utf8'))
assert.equal(guides.length,18)
const regions={
  '350122':['连江县','bca45154d74905b963af83c9'], '350123':['罗源县','e6dccff3468cba55aa9b5c09'],
  '350124':['闽清县','4d74f378197bace2e63b05e9'], '350125':['永泰县','3bfbebb0f7115a969c3d77be'],
  '350181':['福清市','9af3a0528483a9bb4fb67de5'], '350182':['长乐区','e0b2adc9b9b0b10bc0eb9332'],
}
for(const [index,value] of guides.entries()) {
  const [district,source]=regions[value.region_code],region={province:'fujian',city:'福州市',district}
  const g=strict.assertRegionalGuide(value,region),view=display.readGuideDisplay(g)
  assert.equal(g.source_id,source);assert.equal(g.verification_status,'partial')
  assert.equal(g.can_generate,index>=6);assert.equal(g.published,false)
  assert.deepEqual(view.materials.map(m=>m.copies),[2,2,2])
  assert.equal(g.materials[0].name,'仲裁申请书');assert.match(g.materials[0].instructions,/签字/)
  assert.match(g.materials[0].format,/纸质/);assert.equal(g.materials[0].required,'必要')
  assert.equal(g.channel.online_status,'auth_required');assert.equal(g.channel.entry_url,null)
  assert.equal(display.guideField(g,'不存在的来源字段'),'待核实')
  for(const t of g.templates.filter(t=>t.official_kind==='sample'||t.official_kind==='reference')) {
    assert.equal(t.can_generate,false);assert.deepEqual(t.document_types,[])
  }
  if(g.region_code==='350125')assert.deepEqual(g.templates.filter(t=>t.can_generate).flatMap(t=>t.document_types),index>=6?['application']:[])
  if(g.region_code==='350124')assert.match(g.service_code,/202$/)
  for(const change of [{sections:undefined},{version:true},{district:'台江区'}])assert.throws(()=>strict.assertRegionalGuide({...g,...change},region))
}
console.log('PASS J actual strict source/offline/stage parser/display; publication false')
