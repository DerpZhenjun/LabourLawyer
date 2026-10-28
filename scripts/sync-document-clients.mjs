// Regenerate both client snapshots from the production template registry.
import fs from 'node:fs'
import path from 'node:path'
import vm from 'node:vm'
import { execFileSync } from 'node:child_process'

const root = path.resolve(import.meta.dirname, '..')
const python = process.env.PYTHON || path.join(root, '.venv/Scripts/python.exe')
const catalog = JSON.parse(execFileSync(python, ['-c', "import sys,json;sys.path.insert(0,'backend');from province_documents import PROVINCE_DOCUMENTS;print(json.dumps(list(PROVINCE_DOCUMENTS.values()),ensure_ascii=True))"], { cwd: root, encoding: 'utf8' }))
for (const province of catalog) {
  if (!province.region) throw new Error(`Missing region grouping: ${province.slug}`)
  province.hasApplication = !!province.documents.application
  province.hasEvidence = !!province.documents.evidence
}
const formSchema = JSON.parse(fs.readFileSync(path.join(root, 'config/document_forms.json'), 'utf8'))
const context = { officialCatalog: catalog, formSchema, result: null }
vm.createContext(context)
const source = fs.readFileSync(path.join(root, 'frontend/src/data/provinces.js'), 'utf8').replace(/^import .*$/gm, '').replaceAll('export const ', 'const ')
vm.runInContext(source + '\nresult=provinces.map(p=>({...p,applicationExample:makeApplicationExample(p),evidenceExample:makeEvidenceExample(p)}))', context)
const files = {
  'frontend/src/data/provinceCatalog.json': catalog.map(p => ({ ...p, hasApplication: !!p.documents.application, hasEvidence: !!p.documents.evidence })),
  'miniprogram/data/documentForms.json': formSchema,
  'miniprogram/data/provinces.json': context.result,
}
for (const [name, value] of Object.entries(files)) {
  const filename = path.join(root, name)
  const text = JSON.stringify(value, null, 2) + '\n'
  if (process.argv.includes('--check')) {
    if (!fs.existsSync(filename) || fs.readFileSync(filename, 'utf8') !== text) throw new Error(`Client snapshot is out of date: ${name}`)
  } else {
    fs.mkdirSync(path.dirname(filename), { recursive: true })
    fs.writeFileSync(filename, text)
  }
}
console.log(`Synchronized ${catalog.length} regions; ${catalog.filter(p=>p.documents.application).length} applications; ${catalog.filter(p=>p.documents.evidence).length} evidence lists`)
