import assert from 'node:assert/strict'
import {readFileSync,readdirSync,mkdirSync,writeFileSync} from 'node:fs'
import {createRequire} from 'node:module'
import path from 'node:path'
import {fileURLToPath} from 'node:url'
const root=fileURLToPath(new URL('../',import.meta.url)),require=createRequire(new URL('../frontend/package.json',import.meta.url)),ts=require('typescript')
function walk(dir){return readdirSync(dir,{withFileTypes:true}).flatMap(e=>e.isDirectory()?walk(path.join(dir,e.name)):[path.join(dir,e.name)])}
const pages=walk(path.join(root,'frontend/src')).filter(f=>f.endsWith('.vue'))
for(const file of pages){const text=readFileSync(file,'utf8');for(const script of text.matchAll(/<script\b([^>]*)>/g))assert(/\blang=["']ts["']/.test(script[1]),`Vue script not yet TypeScript: ${path.relative(root,file)}`)}
const dir=path.join(root,'.runtime','typed-release-tests');mkdirSync(dir,{recursive:true})
const fixture=path.join(dir,'negative.ts')
writeFileSync(fixture,`import type {AIStatus,AskRequest} from '../../packages/client-contracts/src/index.ts'
const wrongStatus:AIStatus={ready:'yes',provider:'x',model:'x',local_model_started:false}
const wrongRequest:AskRequest={question:9,history:[{role:'system',content:'x'}]}
const opaque:unknown={ready:true}
const unsafeStatus:AIStatus=opaque
`)
const program=ts.createProgram([fixture],{strict:true,noEmit:true,skipLibCheck:true,target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext,moduleResolution:ts.ModuleResolutionKind.Bundler,allowImportingTsExtensions:true})
const diagnostics=ts.getPreEmitDiagnostics(program),errors=diagnostics.filter(d=>d.file&&path.resolve(d.file.fileName)===path.resolve(fixture)&&d.category===ts.DiagnosticCategory.Error)
assert.equal(errors.length,4,ts.formatDiagnosticsWithColorAndContext(diagnostics,{getCanonicalFileName:f=>f,getCurrentDirectory:()=>root,getNewLine:()=> '\n'}))
console.log(`PASS ${pages.length} Vue files use TypeScript scripts; 4 unsafe cross-client API assignments rejected by real compiler`)
