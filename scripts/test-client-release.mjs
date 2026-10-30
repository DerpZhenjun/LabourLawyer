import assert from 'node:assert/strict'
import {existsSync,mkdirSync,mkdtempSync,readFileSync,rmSync,writeFileSync} from 'node:fs'
import path from 'node:path'
import {tmpdir} from 'node:os'
const root=path.resolve(import.meta.dirname,'..')
assert(existsSync(path.join(root,'config/client-release.json')),'One product release manifest must drive client versions')
const {syncRelease}=await import('./sync-client-release.mjs')
const startVersion=html=>{
 const tags=[...html.matchAll(/<p class="tag">Windows 桌面客户端 · v([^<]+)<\/p>/g)]
 assert.equal(tags.length,1,'Desktop start page must show exactly one product version')
 return tags[0][1]
}
const fixture=mkdtempSync(path.join(tmpdir(),'labourlawyer-release-'))
try{
 const initial=['config/client-release.json','frontend/package.json','frontend/package-lock.json','mobile/package.json','mobile/package-lock.json','desktop/package.json','desktop/package-lock.json','desktop/start.html','miniprogram/package.json','miniprogram/package-lock.json','mobile/android/app/build.gradle']
 for(const name of initial){mkdirSync(path.dirname(path.join(fixture,name)),{recursive:true});writeFileSync(path.join(fixture,name),readFileSync(path.join(root,name)))}
 assert.throws(()=>syncRelease({root:fixture,check:true}),/drift|missing/i)
 syncRelease({root:fixture,check:false})
 syncRelease({root:fixture,check:true})
 const manifest=JSON.parse(readFileSync(path.join(fixture,'config/client-release.json'),'utf8'))
 const startFile=path.join(fixture,'desktop/start.html'),start=readFileSync(startFile,'utf8').replace(/\r\n/g,'\n')
 assert.equal(startVersion(start),manifest.version,'Actual packaged desktop page must follow the shared release manifest')
 const stale=start.replace(' · v'+manifest.version+'</p>',' · v0.0.0-preview.0</p>')
 writeFileSync(startFile,stale)
 assert.throws(()=>syncRelease({root:fixture,check:true}),/desktop\/start\.html/)
 assert.equal(readFileSync(startFile,'utf8'),stale,'Check mode must not repair the packaged page silently')
 syncRelease({root:fixture,check:false})
 assert.equal(readFileSync(startFile,'utf8'),start,'Version synchronization must preserve all other desktop page copy')
 manifest.version='9.8.7-preview.2';writeFileSync(path.join(fixture,'config/client-release.json'),JSON.stringify(manifest))
 syncRelease({root:fixture,check:false});syncRelease({root:fixture,check:true})
 assert.equal(startVersion(readFileSync(startFile,'utf8')),manifest.version,'Future version bumps must update the actual packaged page')
 const before=readFileSync(path.join(fixture,'mobile/package.json'),'utf8')
 const release=JSON.parse(readFileSync(path.join(fixture,'config/client-release.json'),'utf8'));release.version='bad version';writeFileSync(path.join(fixture,'config/client-release.json'),JSON.stringify(release))
 assert.throws(()=>syncRelease({root:fixture,check:false}),/version/i)
 assert.equal(readFileSync(path.join(fixture,'mobile/package.json'),'utf8'),before,'Invalid metadata must fail before any write')
}finally{rmSync(fixture,{recursive:true,force:true})}
const release=syncRelease({root,check:true})
assert.equal(startVersion(readFileSync(path.join(root,'desktop/start.html'),'utf8')),release.version,'Repository desktop start page must match the released client version')
console.log('PASS one release version across clients and actual desktop HTML, read-only drift gate and invalid-metadata atomic refusal')
