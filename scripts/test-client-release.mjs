import assert from 'node:assert/strict'
import {existsSync,mkdirSync,mkdtempSync,readFileSync,rmSync,writeFileSync} from 'node:fs'
import path from 'node:path'
import {tmpdir} from 'node:os'
const root=path.resolve(import.meta.dirname,'..')
assert(existsSync(path.join(root,'config/client-release.json')),'One product release manifest must drive client versions')
const {syncRelease}=await import('./sync-client-release.mjs')
const fixture=mkdtempSync(path.join(tmpdir(),'labourlawyer-release-'))
try{
 const initial=['config/client-release.json','frontend/package.json','frontend/package-lock.json','mobile/package.json','mobile/package-lock.json','desktop/package.json','desktop/package-lock.json','miniprogram/package.json','miniprogram/package-lock.json','mobile/android/app/build.gradle']
 for(const name of initial){mkdirSync(path.dirname(path.join(fixture,name)),{recursive:true});writeFileSync(path.join(fixture,name),readFileSync(path.join(root,name)))}
 assert.throws(()=>syncRelease({root:fixture,check:true}),/drift|missing/i)
 syncRelease({root:fixture,check:false})
 syncRelease({root:fixture,check:true})
 const before=readFileSync(path.join(fixture,'mobile/package.json'),'utf8')
 const release=JSON.parse(readFileSync(path.join(fixture,'config/client-release.json'),'utf8'));release.version='bad version';writeFileSync(path.join(fixture,'config/client-release.json'),JSON.stringify(release))
 assert.throws(()=>syncRelease({root:fixture,check:false}),/version/i)
 assert.equal(readFileSync(path.join(fixture,'mobile/package.json'),'utf8'),before,'Invalid metadata must fail before any write')
}finally{rmSync(fixture,{recursive:true,force:true})}
syncRelease({root,check:true})
console.log('PASS one release version across clients, read-only drift gate and invalid-metadata atomic refusal')
