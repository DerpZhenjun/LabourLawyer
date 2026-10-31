import assert from 'node:assert/strict'
import fs from 'node:fs'
import {createRequire} from 'node:module'
import {guideField,visitCountLabel,originalCopyLabel,materialCopiesLabel,guideSectionLabel,materialDetails,hasGenerationKind} from '../frontend/src/data/regionalGuidePresentation.js'
const yuhua=JSON.parse(fs.readFileSync('reports/nationwide-verification-20261029-c/hunan/yuhua/guide.json','utf8'))
assert.deepEqual(yuhua.materials.map(m=>materialCopiesLabel(m.copies)),['2 份','1 份','1 份','2 份'])
assert.equal(guideField(yuhua,'咨询方式'),'0731-85880234')
assert.equal(originalCopyLabel(yuhua.materials[0]),'原件')
assert.equal(materialDetails(yuhua.materials[0])['填写与份数说明'],yuhua.materials[0].instructions)
assert.equal(materialDetails(yuhua.materials[0])['提交方式'],'网上现场都可提交')
assert.equal(visitCountLabel({fields:{'到办事现场次数':{raw_value:'0次'}}}),'0次')
assert.equal(visitCountLabel({fields:{'到现场次数':{raw_value:0}}}),'0 次')
assert.equal(guideField({fields:{}},'咨询方式'),'待核实')
assert.equal(originalCopyLabel({material_type:'纸质'}),'原件/复印件待核实')
assert.deepEqual(materialDetails({details:{'原文':'原值'}}),{'原文':'原值'})
for(const [value,expected] of [[2,'2 份'],['2','2 份'],[' 02 ','2 份'],[2.5,'2.5 份'],['2e1','20 份']])assert.equal(materialCopiesLabel(value),expected)
for(const value of [undefined,null,'','   ',0,'0',-2,'-2',NaN,'NaN',Infinity,'Infinity',-Infinity,true,false,[],{},2n])assert.equal(materialCopiesLabel(value),'份数待核实')
const mBase='reports/overnight-gap-closure-20261030/localities/fujian-m-source-projection/chengxiang-350302/'
const mMaterials=JSON.parse(fs.readFileSync(mBase+'materials.json','utf8')).materials
assert.deepEqual(mMaterials.map(m=>materialCopiesLabel(m.copies_raw)),['原件份数2份','原件份数2份','复印件份数2份'])
for(const value of ['2 份',' 原件份数2份 ','原件份数0份（无需另交）','正本一份，副本按照当事人人数提交。','按被申请人人数提供副本'])assert.equal(materialCopiesLabel(value),value)
const mSections=JSON.parse(fs.readFileSync(mBase+'own-guide.json','utf8')).raw_sections
const originalSections=JSON.stringify(mSections)
assert.deepEqual(Object.keys(mSections).map(guideSectionLabel),['受理条件','窗口办理说明'])
assert.equal(JSON.stringify(mSections),originalSections,'Display labels must not alter official raw section keys or bodies')
for(const key of ['原始说明','unknown','conditions ','Conditions','toString','constructor',''])assert.equal(guideSectionLabel(key),key)
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
assert.match(view,/\{\{ materialCopiesLabel\(m\.copies\) \}\}/)
assert.doesNotMatch(view,/\{\{ m\.copies\?' 份':'' \}\}/)
assert.match(view,/<summary>\{\{ guideSectionLabel\(name\) \}\}<\/summary><p class="official-raw">\{\{ text \|\| '官网未提供，待核实' \}\}<\/p>/)
assert.match(view,/v-if="hasGenerationKind\(guide,'application'\)"[^>]+documentLink\('application'\)/)
assert.match(view,/v-if="hasGenerationKind\(guide,'evidence'\)"[^>]+documentLink\('evidence'\)/)
console.log('PASS own presence reasons and document CTA kind capabilities')
const {parse,compileScript,compileTemplate}=createRequire(new URL('../frontend/package.json',import.meta.url))('@vue/compiler-sfc')
const {descriptor,errors}=parse(view,{filename:'RegionalGuide.vue'})
assert.deepEqual(errors,[])
const compiledScript=compileScript(descriptor,{id:'regional-guide-display-fixture'})
const compiledTemplate=compileTemplate({source:descriptor.template.content,filename:'RegionalGuide.vue',id:'regional-guide-display-fixture',compilerOptions:{bindingMetadata:compiledScript.bindings}})
assert.deepEqual(compiledTemplate.errors,[])
assert(compiledTemplate.code.includes('materialCopiesLabel'))
assert(compiledTemplate.code.includes('guideSectionLabel'))
console.log('PASS actual RegionalGuide Vue script/template compile with display-only formatters; no site build or browser')
