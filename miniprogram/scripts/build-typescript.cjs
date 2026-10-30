const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto')
const ts=require('typescript')
const root=path.resolve(__dirname,'..'),config=ts.readConfigFile(path.join(root,'tsconfig.json'),ts.sys.readFile)
if(config.error)throw Error(ts.flattenDiagnosticMessageText(config.error.messageText,'\n'))
const parsed=ts.parseJsonConfigFileContent(config.config,ts.sys,root)
const program=ts.createProgram(parsed.fileNames,parsed.options)
const errors=[...parsed.errors,...ts.getPreEmitDiagnostics(program)]
if(errors.length){console.error(ts.formatDiagnosticsWithColorAndContext(errors,{getCanonicalFileName:f=>f,getCurrentDirectory:()=>root,getNewLine:()=> '\n'}));process.exit(1)}
const entries=['app',...fs.readdirSync(path.join(root,'pages')).map(n=>'pages/'+n+'/index'),'utils/documents','utils/regionalTransport']
for(const entry of entries){
 const source=fs.readFileSync(path.join(root,entry+'.ts'),'utf8').replace(/\r\n/g,'\n')
 let body=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2020,module:ts.ModuleKind.CommonJS,strict:true,esModuleInterop:false}}).outputText.replace(/\r\n/g,'\n')
 if(entry==='app'||entry.startsWith('pages/'))body=body.replace(/^Object.defineProperty\(exports, "__esModule", \{ value: true \}\);\n/m,'')
 body='// Generated from '+entry+'.ts. Do not edit.\n// source-sha256: '+crypto.createHash('sha256').update(source).digest('hex')+'\n'+body
 const output=path.join(root,entry+'.js')
 if(process.argv.includes('--check')){if(!fs.existsSync(output)||fs.readFileSync(output,'utf8').replace(/\r\n/g,'\n')!==body)throw Error('Stale mini runtime: '+entry)}else fs.writeFileSync(output,body)
}
console.log('PASS strict mini TypeScript and '+entries.length+' generated runtimes'+(process.argv.includes('--check')?' match':' built'))
