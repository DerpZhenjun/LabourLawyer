import {createRequire} from 'node:module'
import {readFileSync,writeFileSync,mkdirSync,existsSync} from 'node:fs'
import {createHash} from 'node:crypto'
const root=new URL('../',import.meta.url),require=createRequire(new URL('frontend/package.json',root))
const ts=require('typescript'),source=readFileSync(new URL('packages/regional-contracts/src/index.ts',root),'utf8')
const sha=createHash('sha256').update(source).digest('hex')
const output=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2020,module:ts.ModuleKind.CommonJS,strict:true,removeComments:false}})
const body=`// Generated from packages/regional-contracts/src/index.ts. Do not edit.\n// source-sha256: ${sha}\n${output.outputText.replace(/\r\n/g,'\n')}`
const target=new URL('miniprogram/utils/generated/regional-contracts.js',root)
if(process.argv.includes('--check')){
  if(!existsSync(target)||readFileSync(target,'utf8')!==body)throw new Error('Shared mini-program contract runtime is stale. Run npm --prefix frontend run contracts:build.')
  console.log('PASS generated mini-program runtime matches the exact shared TypeScript source')
}else{mkdirSync(new URL('.',target),{recursive:true});writeFileSync(target,body);console.log('Built shared contract runtime for mini-program')}
