import fs from 'node:fs'
import path from 'node:path'
import {provinces,makeApplicationExample,makeEvidenceExample} from '../frontend/src/data/provinces.js'
const root=path.resolve(import.meta.dirname,'..')
const result=provinces.filter(p=>p.hasApplication||p.hasEvidence).map(p=>({slug:p.slug,name:p.name,application:makeApplicationExample(p),evidence:makeEvidenceExample(p)}))
fs.mkdirSync(path.join(root,'.runtime/document-audit'),{recursive:true})
fs.writeFileSync(path.join(root,'.runtime/document-audit/frontend-examples.json'),JSON.stringify(result,null,2))
console.log(`Exported ${result.length} regions from actual frontend defaults`)
