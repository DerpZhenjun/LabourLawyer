import assert from 'node:assert/strict'
import {createRequire} from 'node:module'
import {existsSync, mkdirSync, readFileSync, writeFileSync} from 'node:fs'
import {fileURLToPath} from 'node:url'
import {spawnSync} from 'node:child_process'
import path from 'node:path'

const root=fileURLToPath(new URL('../',import.meta.url))
const ownFiles=['frontend/src/data/jiangsuOwnFields.ts','frontend/src/data/zhejiangOwnFields.ts',
  'frontend/src/composables/useJiangsuOwnDrafts.ts','frontend/src/composables/useZhejiangOwnDrafts.ts']
for(const name of ownFiles)assert(existsSync(path.join(root,name)),`Missing actual TypeScript module: ${name}`)
const require=createRequire(new URL('../frontend/package.json',import.meta.url)),ts=require('typescript')
const scratch=path.join(root,'.runtime','typescript-own-fields');mkdirSync(scratch,{recursive:true})
const imports=`import {createEmptyJiangsuOwn,jiangsuOwnPayload} from '../../frontend/src/data/jiangsuOwnFields.ts'
import type {JiangsuOwnApplication,JiangsuOwnEvidence,JiangsuOwnEvidenceItem} from '../../frontend/src/data/jiangsuOwnFields.ts'
import {createEmptyZhejiangOwn,zhejiangOwnPayload} from '../../frontend/src/data/zhejiangOwnFields.ts'
import type {ZhejiangOwnApplication,ZhejiangOwnEvidence,ZhejiangOwnEvidenceItem} from '../../frontend/src/data/zhejiangOwnFields.ts'
import {useJiangsuOwnDrafts} from '../../frontend/src/composables/useJiangsuOwnDrafts.ts'
import {useZhejiangOwnDrafts} from '../../frontend/src/composables/useZhejiangOwnDrafts.ts'
`
const positive=imports+`
const jsApplication: JiangsuOwnApplication={phone:'虚构电话',copyCount:3,evidenceCopyCount:2,requests:['虚构请求']}
const jsEvidence: JiangsuOwnEvidence={caseNumber:'虚构案号',evidenceList:[{source:'仅填虚构来源',originalType:'复印件'}]}
const jsItem: JiangsuOwnEvidenceItem={source:'虚构来源'}
const zjApplication: ZhejiangOwnApplication={householdType:'',phone:'虚构电话',copyCount:''}
const zjEvidence: ZhejiangOwnEvidence={copyCount:2,evidenceList:[{pageCount:'3'}]}
const zjItem: ZhejiangOwnEvidenceItem={purpose:'虚构用途'}
const jsName: string=createEmptyJiangsuOwn('application').applicantName
const zjRows: ZhejiangOwnEvidenceItem[]=createEmptyZhejiangOwn('evidence').evidenceList
const jsCopy: number|string|null|undefined=jiangsuOwnPayload(jsApplication,'application').copyCount
const zjRowsOut: ZhejiangOwnEvidenceItem[]|undefined=zhejiangOwnPayload(zjEvidence,'evidence').evidenceList
const selected={value:'application'}
const jsRaw=useJiangsuOwnDrafts(selected),zjRaw=useZhejiangOwnDrafts(selected)
jsRaw.value={unknownOldField:''};zjRaw.value=null
`
const negative=imports+`
const wrongJsHeader: JiangsuOwnEvidence={copyCount:2} // reject: js-evidence-copy-slot
const wrongJsItem: JiangsuOwnEvidenceItem={householdType:''} // reject: js-item-foreign-slot
const wrongJsText: JiangsuOwnApplication={phone:7} // reject: raw-numeric-text
const wrongJsRequests: JiangsuOwnApplication={requests:[7]} // reject: numeric-request
const wrongJsKind=createEmptyJiangsuOwn('identity') // reject: js-unsupported-kind
const wrongZJItem: ZhejiangOwnEvidenceItem={originalType:''} // reject: zj-item-foreign-slot
const wrongZJApp: ZhejiangOwnApplication={evidenceCopyCount:2} // reject: zj-foreign-copy-slot
const wrongZJKind=createEmptyZhejiangOwn('identity') // reject: zj-unsupported-kind
jiangsuOwnPayload({},'evidence').copyCount // reject: typed-js-evidence-output
zhejiangOwnPayload({},'evidence').originalType // reject: typed-zj-evidence-output
useJiangsuOwnDrafts({value:'application'}).value.applicantName // reject: js-raw-draft-remains-unknown
useZhejiangOwnDrafts({value:'application'}).value.applicantName // reject: zj-raw-draft-remains-unknown
`
const positiveFile=path.join(scratch,'positive.ts'),negativeFile=path.join(scratch,'negative.ts')
writeFileSync(positiveFile,positive);writeFileSync(negativeFile,negative)
const options={noEmit:true,strict:true,noUncheckedIndexedAccess:true,exactOptionalPropertyTypes:true,
  allowImportingTsExtensions:true,skipLibCheck:true,target:ts.ScriptTarget.ES2022,
  module:ts.ModuleKind.ESNext,moduleResolution:ts.ModuleResolutionKind.Bundler,
  lib:['lib.es2023.d.ts','lib.dom.d.ts'],verbatimModuleSyntax:true}
const diagnostics=files=>ts.getPreEmitDiagnostics(ts.createProgram(files,options)).filter(d=>d.category===ts.DiagnosticCategory.Error)
const display=list=>list.map(d=>`${d.file?path.relative(root,d.file.fileName):'compiler'}:${d.start??0} TS${d.code} ${ts.flattenDiagnosticMessageText(d.messageText,' ')}`).join('\n')
const good=diagnostics([...ownFiles.map(name=>path.join(root,name)),positiveFile])
assert.equal(good.length,0,display(good))
const bad=diagnostics([negativeFile]),expected=new Map()
negative.split('\n').forEach((line,index)=>{const tag=line.match(/reject: ([\w-]+)/)?.[1];if(tag)expected.set(index,tag)})
assert.equal(bad.filter(d=>!d.file||path.resolve(d.file.fileName)!==negativeFile).length,0,display(bad))
for(const diagnostic of bad)assert([2353,2322,2769,2339,2571,18046].includes(diagnostic.code),display([diagnostic]))
const observed=new Set(bad.map(d=>d.file.getLineAndCharacterOfPosition(d.start).line))
assert.deepEqual([...observed].sort((a,b)=>a-b),[...expected.keys()],display(bad))
for(const name of ownFiles){
  const source=ts.createSourceFile(name,readFileSync(path.join(root,name),'utf8'),ts.ScriptTarget.Latest,true)
  const visit=node=>{assert.notEqual(node.kind,ts.SyntaxKind.AnyKeyword,`${name} uses an unbounded type`);ts.forEachChild(node,visit)}
  visit(source);assert(!/@ts-(ignore|nocheck)/.test(source.text),`${name} suppresses checking`)
}
const componentFiles=['frontend/src/components/JiangsuOwnFields.vue','frontend/src/components/ZhejiangOwnFields.vue']
for(const name of componentFiles){
  const source=readFileSync(path.join(root,name),'utf8')
  assert.match(source,/<script setup lang="ts">/)
  assert(!/@ts-(ignore|nocheck)/.test(source))
  const script=source.match(/<script setup lang="ts">([\s\S]*?)<\/script>/)?.[1]
  assert(script)
  const tree=ts.createSourceFile(name+'.ts',script,ts.ScriptTarget.Latest,true)
  const visit=node=>{assert.notEqual(node.kind,ts.SyntaxKind.AnyKeyword,`${name} uses an unbounded type`);ts.forEachChild(node,visit)}
  visit(tree)
}
const config=path.join(scratch,'tsconfig.json')
writeFileSync(config,JSON.stringify({compilerOptions:{...options,target:'ES2022',module:'ESNext',moduleResolution:'Bundler',
  lib:['ES2023','DOM'],paths:{'@/*':[path.join(root,'frontend/src/*').replaceAll('\\','/')]}},
  vueCompilerOptions:{strictTemplates:true},
  files:[...ownFiles,...componentFiles].map(name=>path.join(root,name))},null,2))
const vueCheck=spawnSync(process.execPath,[require.resolve('vue-tsc/bin/vue-tsc.js'),'--project',config,'--noEmit'],{cwd:root,encoding:'utf8'})
assert.equal(vueCheck.status,0,(vueCheck.stdout+vueCheck.stderr).replaceAll(root,''))
console.log(`PASS own-field strict TypeScript: 4 modules + 2 SFCs, positive contracts, ${expected.size} rejected type counterexamples, raw drafts remain unknown`)
