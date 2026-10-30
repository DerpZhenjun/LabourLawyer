const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const cp = require('node:child_process')
const root = path.resolve(__dirname, '..')
const entries = ['app', ...fs.readdirSync(path.join(root, 'pages')).map(n => `pages/${n}/index`), 'utils/documents', 'utils/regionalTransport']
for (const entry of entries) {
  const file = path.join(root, entry + '.ts')
  assert(fs.existsSync(file), 'Missing typed business source: ' + entry)
  assert(!/\bany\b|@ts-(?:ignore|nocheck)/.test(fs.readFileSync(file, 'utf8')), 'Unchecked business code: ' + entry)
}
cp.execFileSync(process.execPath, [path.join(root, 'scripts/build-typescript.cjs'), '--check'], {stdio: 'inherit'})
const ts=require('typescript')
const probe=path.join(root,'types','__migration_probe.ts')
assert(!fs.existsSync(probe),'Probe path must be unused')
try {
  fs.writeFileSync(probe,`import type {PageSpec} from './runtime'
import type {FormContext} from '../../packages/regional-contracts/src/index'
import type {AskRequest} from '../../packages/client-contracts/src/index'
import type {FormLimits} from '../../packages/client-contracts/src/documents'
const page:PageSpec<{busy:boolean},{run():void}>={data:{busy:false},run(){this.setData({busy:'wrong'})}}
const context:Partial<FormContext>={version:'old'}
const ask:AskRequest={question:99,history:[]}
const limits:Partial<FormLimits>={maxEvidence:'unlimited'}
`)
  const config=ts.readConfigFile(path.join(root,'tsconfig.json'),ts.sys.readFile)
  const parsed=ts.parseJsonConfigFileContent(config.config,ts.sys,root)
  const program=ts.createProgram(parsed.fileNames,parsed.options)
  const errors=ts.getPreEmitDiagnostics(program)
  assert.equal(errors.length,4,'Four actual invalid page/wire types must be rejected')
  assert(errors.every(e=>e.file && path.resolve(e.file.fileName)===path.resolve(probe)&&e.code===2322))
} finally {fs.unlinkSync(probe)}
console.log('PASS all mini business sources are typed, strictly checked and generated JavaScript has no drift')
