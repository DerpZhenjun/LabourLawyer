import assert from 'node:assert/strict'
import {existsSync,readFileSync} from 'node:fs'
import {execFileSync} from 'node:child_process'
import {createRequire} from 'node:module'
import path from 'node:path'
const root=path.resolve(import.meta.dirname,'..')
const output=path.join(root,'packages/client-contracts/src/generated/stable-api.ts')
assert(existsSync(output),'Stable types must be generated from the registered backend routes')
execFileSync(process.execPath,[path.join(root,'scripts/build-api-contracts.mjs'),'--check'],{stdio:'inherit'})
const require=createRequire(new URL('../frontend/package.json',import.meta.url)),ts=require('typescript')
const source=readFileSync(output,'utf8')
assert(source.includes('QuestionRequest')&&source.includes('ProvinceCatalogResponse'))
const limits=await import('../packages/client-contracts/src/generated/api-limits.ts')
assert.deepEqual(limits.API_LIMITS,{questionMax:8000,messageMax:8000,historyMax:12})
for(const cwd of ['frontend','miniprogram'])execFileSync(process.execPath,[path.join(root,'scripts/build-client-contracts.mjs'),'--check'],{cwd:path.join(root,cwd),stdio:'inherit'})
const probe=path.join(root,'packages/client-contracts/src/generated/__type_probe.ts')
const fs=await import('node:fs')
assert(!fs.existsSync(probe))
try{
 fs.writeFileSync(probe,`import type {components} from './stable-api'
const ask:components['schemas']['QuestionRequest']={question:8}
const limits:components['schemas']['FormLimits']={maxRequests:'many',requestLength:1,factsLength:1,maxEvidence:1}
`)
 const program=ts.createProgram([probe],{target:ts.ScriptTarget.ES2020,module:ts.ModuleKind.ESNext,moduleResolution:ts.ModuleResolutionKind.Bundler,strict:true,noEmit:true,skipLibCheck:true})
 const errors=ts.getPreEmitDiagnostics(program)
 assert.equal(errors.length,2)
 assert(errors.every(e=>e.code===2322&&path.resolve(e.file.fileName)===probe))
}finally{fs.unlinkSync(probe)}
console.log('PASS actual OpenAPI types, Python-derived limits and compiler counterexamples')
