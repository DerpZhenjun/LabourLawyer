/** Offline stable API generation; never import the application startup module. */
import {execFileSync} from 'node:child_process'
import {createHash} from 'node:crypto'
import {createRequire} from 'node:module'
import {existsSync,mkdirSync,readFileSync,writeFileSync} from 'node:fs'
import path from 'node:path'

const root=path.resolve(import.meta.dirname,'..')
const require=createRequire(path.join(root,'frontend/package.json'))
const {default:openapiTS,astToString}=require('openapi-typescript')
const python=process.env.PYTHON || path.join(root,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python')
const schema=JSON.parse(execFileSync(python,['backend/export_api_contracts.py'],{cwd:root,env:{...process.env,PYTHONUTF8:'1',PYTHONIOENCODING:'utf-8'},encoding:'utf8',timeout:30000,windowsHide:true,maxBuffer:8*1024*1024}))
const normalized=JSON.stringify(schema,null,2)+'\n'
const digest=createHash('sha256').update(normalized).digest('hex')
const types=astToString(await openapiTS(schema,{alphabetize:true,defaultNonNullable:false})).replace(/\r\n/g,'\n')
const models=schema.components.schemas
const limits={questionMax:models.QuestionRequest.properties.question.maxLength,messageMax:models.ChatMessage.properties.content.maxLength,historyMax:models.QuestionRequest.properties.history.maxItems}
if(!Object.values(limits).every(v=>Number.isSafeInteger(v)&&v>0))throw Error('Missing finite backend AI limits')
const files={
 'packages/client-contracts/schema/stable-api.openapi.json':normalized,
 'packages/client-contracts/src/generated/stable-api.ts':`// Generated from registered FastAPI routes. Do not edit.\n// schema-sha256: ${digest}\n${types}`,
 'packages/client-contracts/src/generated/api-limits.ts':`// Generated from Pydantic request constraints. Do not edit.\n// schema-sha256: ${digest}\nexport const API_LIMITS = ${JSON.stringify(limits,null,2)} as const\n`,
}
for(const [relative,content] of Object.entries(files)){
 const file=path.join(root,relative)
 if(process.argv.includes('--check')){
  if(!existsSync(file)||readFileSync(file,'utf8').replace(/\r\n/g,'\n')!==content)throw Error('API contract drift: '+relative+'; run node scripts/build-api-contracts.mjs')
 }else{mkdirSync(path.dirname(file),{recursive:true});writeFileSync(file,content)}
}
console.log(`PASS stable OpenAPI ${process.argv.includes('--check')?'matches':'generated'}: ${Object.keys(schema.paths).length} paths; no startup, DB or model calls`)
