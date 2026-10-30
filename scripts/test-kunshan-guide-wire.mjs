/** Fixed regressions against the production parser and presentation.
 * Stdin is JSON data only; it never supplies executable code or module paths.
 */
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import * as strict from '../packages/regional-contracts/src/index.ts'
import * as display from '../frontend/src/data/regionalGuidePresentation.ts'

const data=JSON.parse(readFileSync(0,'utf8'))
if(data.mode==='wire') {
  const guide=strict.assertRegionalGuide(data.lookup,data.region)
  assert.deepEqual(display.readInventory(data.inventory).items.map(r=>r.region_code),['320583'])
  assert.equal(display.readGuideDisplay(guide).verification_status,'verified')
  for(const form of data.forms)strict.assertFormContract(form,form.context)
  assert.deepEqual(data.forms.map(f=>f.fields.length),[28,4])
  console.log('PASS Kunshan own lookup, inventory, display and both form contracts')
} else if(data.mode==='display') {
  const guide=display.readGuideDisplay(data.guide)
  for(const name of ['办理形式','办理地点','办理时间','咨询方式'])
    assert.equal(display.guideField(guide,name),data.fields[name],name+' must retain its own actual fact')
  assert.equal(display.visitCountLabel(guide),'3 次')
  assert.deepEqual(guide.materials.map(m=>m.copies),data.copies)
  assert.deepEqual(guide.materials.map(m=>display.originalCopyLabel(m)),data.originals)
  assert.deepEqual(guide.materials.map(m=>m.required),data.required)
  assert.deepEqual(guide.materials.map(m=>m.format),data.formats)
  console.log('PASS Kunshan own fields, visit count and all four material requirements')
} else {
  assert.fail('Only the fixed wire or display regression is supported')
}
