import assert from 'node:assert/strict'
import {createRequire} from 'node:module'
import {readFileSync} from 'node:fs'
import vm from 'node:vm'
const require=createRequire(new URL('../frontend/package.json',import.meta.url)),ts=require('typescript')
const shared=await import('../packages/client-contracts/src/index.ts')
const code=readFileSync(new URL('../frontend/src/api/http.ts',import.meta.url),'utf8').replaceAll('import.meta.env','({VITE_API_BASE_URL:"/"})')
const js=ts.transpileModule(code,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText
const module={exports:{}}
vm.runInNewContext(js,{module,exports:module.exports,location:{origin:'http://127.0.0.1:45678'},require:ref=>ref.includes('client-contracts')?shared:ref.includes('connection')?{savedConnection:()=>null}:{parseApiError:()=> 'error'}})
assert.equal(module.exports.apiURL('/health'),'http://127.0.0.1:45678/health','Desktop same-origin API configuration must resolve through its own proxy')
assert.throws(()=>module.exports.apiURL('//untrusted.invalid'))
assert.throws(()=>module.exports.apiURL('/api/../secret'))
console.log('PASS desktop same-origin API base retains shared URL safety checks')
