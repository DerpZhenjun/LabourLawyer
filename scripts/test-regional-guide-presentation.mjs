import assert from 'node:assert/strict'
import fs from 'node:fs'
import {guideField,visitCountLabel,originalCopyLabel,materialDetails,hasGenerationKind} from '../frontend/src/data/regionalGuidePresentation.js'
const yuhua=JSON.parse(fs.readFileSync('reports/nationwide-verification-20261029-c/hunan/yuhua/guide.json','utf8'))
assert.equal(guideField(yuhua,'咨询方式'),'0731-85880234')
assert.equal(originalCopyLabel(yuhua.materials[0]),'原件')
assert.equal(materialDetails(yuhua.materials[0])['填写与份数说明'],yuhua.materials[0].instructions)
assert.equal(materialDetails(yuhua.materials[0])['提交方式'],'网上现场都可提交')
assert.equal(visitCountLabel({fields:{'到办事现场次数':{raw_value:'0次'}}}),'0次')
assert.equal(visitCountLabel({fields:{'到现场次数':{raw_value:0}}}),'0 次')
assert.equal(guideField({fields:{}},'咨询方式'),'待核实')
assert.equal(originalCopyLabel({material_type:'纸质'}),'原件/复印件待核实')
assert.deepEqual(materialDetails({details:{'原文':'原值'}}),{'原文':'原值'})
console.log('PASS real own guide aliases, local material instructions, zero visits and no inferred missing information')

for(const [file,heading] of [['hunan/yuhua','必需现场办理原因'],['hunan/wangcheng','必需现场办理原因'],['jiangsu/xinbei','必须到现场办理说明'],['jiangsu/wujin','必须到现场办理说明']]){
  const g=JSON.parse(fs.readFileSync(`reports/nationwide-verification-20261029-c/${file}/guide.json`,'utf8'))
  assert.equal(guideField(g,'必须到现场原因'),g.fields[heading].raw_value)
}
assert.equal(hasGenerationKind({templates:[{can_generate:true,document_types:['application']}]},'application'),true)
assert.equal(hasGenerationKind({templates:[{can_generate:true,document_types:['application']}]},'evidence'),false)
assert.equal(hasGenerationKind({templates:[{can_generate:false,document_types:['evidence']}]},'evidence'),false)
assert.equal(hasGenerationKind({templates:[{can_generate:true,document_types:['evidence']}]},'evidence'),true)
const view=fs.readFileSync('frontend/src/views/RegionalGuide.vue','utf8')
assert.match(view,/v-if="hasGenerationKind\(guide,'application'\)"[^>]+documentLink\('application'\)/)
assert.match(view,/v-if="hasGenerationKind\(guide,'evidence'\)"[^>]+documentLink\('evidence'\)/)
console.log('PASS own presence reasons and document CTA kind capabilities')
