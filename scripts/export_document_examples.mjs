import fs from 'node:fs'
import vm from 'node:vm'
import path from 'node:path'
const root=path.resolve(import.meta.dirname,'..')
const context={officialCatalog:JSON.parse(fs.readFileSync(path.join(root,'frontend/src/data/provinceCatalog.json'),'utf8')),formSchema:JSON.parse(fs.readFileSync(path.join(root,'config/document_forms.json'),'utf8')),result:null}
vm.createContext(context)
const source=fs.readFileSync(path.join(root,'frontend/src/data/provinces.js'),'utf8').replace(/^import .*$/gm,'').replaceAll('export const ','const ')
vm.runInContext(source+'\nresult=provinces.filter(p=>p.hasApplication||p.hasEvidence).map(p=>({slug:p.slug,name:p.name,application:makeApplicationExample(p),evidence:makeEvidenceExample(p)}))',context)
fs.mkdirSync(path.join(root,'.runtime/document-audit'),{recursive:true})
fs.writeFileSync(path.join(root,'.runtime/document-audit/frontend-examples.json'),JSON.stringify(context.result,null,2))
console.log(`Exported ${context.result.length} regions from actual frontend defaults`)
