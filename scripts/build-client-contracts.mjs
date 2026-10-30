import {createRequire} from 'node:module'
import {readFileSync,writeFileSync,existsSync,mkdirSync} from 'node:fs'
import {fileURLToPath} from 'node:url'
import {createHash} from 'node:crypto'
const root=new URL('../',import.meta.url),require=createRequire(new URL('frontend/package.json',root)),ts=require('typescript')
const source=readFileSync(new URL('packages/client-contracts/src/index.ts',root),'utf8').replace(/\r\n/g,'\n')
const inputs=[source,readFileSync(new URL('packages/client-contracts/src/generated/api-limits.ts',root),'utf8'),readFileSync(new URL('packages/client-contracts/src/generated/stable-api.ts',root),'utf8')].map(s=>s.replace(/\r\n/g,'\n'))
const digest=createHash('sha256').update(inputs.join('\n')).digest('hex')
const bundled=require('esbuild').buildSync({absWorkingDir:fileURLToPath(root),entryPoints:[fileURLToPath(new URL('packages/client-contracts/src/index.ts',root))],bundle:true,write:false,format:'cjs',platform:'neutral',target:'es2020',legalComments:'none'})
const result={outputText:bundled.outputFiles[0].text}
const body=`// Generated from packages/client-contracts/src/index.ts. Do not edit.\n// source-sha256: ${digest}\n${result.outputText.replace(/\r\n/g,'\n')}`
const sourcePath=fileURLToPath(new URL('packages/client-contracts/src/index.ts',root))
const program=ts.createProgram([sourcePath],{target:ts.ScriptTarget.ES2020,module:ts.ModuleKind.ESNext,declaration:true,emitDeclarationOnly:true,strict:true,skipLibCheck:true,allowImportingTsExtensions:true})
const diagnostics=ts.getPreEmitDiagnostics(program)
if(diagnostics.length)throw Error(ts.formatDiagnosticsWithColorAndContext(diagnostics,{getCanonicalFileName:p=>p,getCurrentDirectory:()=>fileURLToPath(root),getNewLine:()=> '\n'}))
let declaration=''
const emitted=program.emit(undefined,(name,text)=>{if(name.endsWith('index.d.ts'))declaration=text.replace(/\r\n/g,'\n')})
declaration=declaration.replaceAll("'./generated/stable-api'","'../src/generated/stable-api'").replaceAll("'./generated/api-limits.ts'","'../src/generated/api-limits'")
if(emitted.emitSkipped||!declaration)throw Error('Unable to generate client contract declarations')
const files=[['miniprogram/utils/generated/client-contracts.js',body],['packages/client-contracts/generated/index.cjs',body],['packages/client-contracts/generated/index.d.cts','// Generated client contract declarations. Do not edit.\n'+declaration]]
for(const [name,content] of files){const output=new URL(name,root)
 if(process.argv.includes('--check')){if(!existsSync(output)||readFileSync(output,'utf8')!==content)throw Error('Stale client contract output: '+name)}
 else{mkdirSync(new URL('.',output),{recursive:true});writeFileSync(output,content)}
}
console.log(process.argv.includes('--check')?'PASS shared client runtimes and declarations match TypeScript':'Built shared client contracts for web, mini and digital proxy')

// Provincial catalog DTO runtime is also compiled from portable TypeScript.
const catalogSource=readFileSync(new URL('packages/client-contracts/src/documents.ts',root),'utf8').replace(/\r\n/g,'\n')
const catalogOutput=ts.transpileModule(catalogSource,{compilerOptions:{target:ts.ScriptTarget.ES2020,module:ts.ModuleKind.CommonJS,strict:true}}).outputText.replace(/\r\n/g,'\n')
const catalogBody='// Generated from packages/client-contracts/src/documents.ts. Do not edit.\n// source-sha256: '+createHash('sha256').update(catalogSource).digest('hex')+'\n'+catalogOutput
for(const [name,content] of [['miniprogram/utils/generated/document-contracts.js',catalogBody],['miniprogram/utils/generated/document-contracts.d.ts',"export * from '../../../packages/client-contracts/src/documents'\n"]]){
 const output=new URL(name,root)
 if(process.argv.includes('--check')){if(!existsSync(output)||readFileSync(output,'utf8').replace(/\r\n/g,'\n')!==content)throw Error('Stale catalog runtime: '+name)}else writeFileSync(output,content)
}
