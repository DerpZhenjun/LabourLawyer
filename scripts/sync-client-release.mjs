/** Synchronize owned client metadata; check mode never writes. No SDK or network IO. */
import {existsSync,mkdirSync,readFileSync,writeFileSync} from 'node:fs'
import {dirname,resolve} from 'node:path'
import {fileURLToPath} from 'node:url'
const ROOT=fileURLToPath(new URL('../',import.meta.url))

export function syncRelease({root=ROOT,check=true}={}){
 const read=name=>readFileSync(resolve(root,name),'utf8').replace(/\r\n/g,'\n')
 const release=JSON.parse(read('config/client-release.json'))
 if(release.schemaVersion!==1||release.product!=='LabourLawyer'||!/^\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?$/.test(release.version)||!Number.isSafeInteger(release.androidVersionCode)||release.androidVersionCode<1||!['preview','stable'].includes(release.channel))throw Error('Invalid client release version or metadata')
 const files={}
 for(const client of ['frontend','mobile','desktop','miniprogram']){
  const name=client+'/package.json',pkg=JSON.parse(read(name));pkg.version=release.version;files[name]=JSON.stringify(pkg,null,2)+'\n'
  const lockName=client+'/package-lock.json',lock=JSON.parse(read(lockName));lock.version=release.version
  if(!lock.packages?.[''])throw Error('Missing root package lock entry: '+client)
  lock.packages[''].version=release.version;files[lockName]=JSON.stringify(lock,null,2)+'\n'
 }
 const gradle='mobile/android/app/build.gradle',source=read(gradle)
 if((source.match(/versionCode\s+\d+/g)||[]).length!==1||(source.match(/versionName\s+"[^"]+"/g)||[]).length!==1)throw Error('Missing or ambiguous Android release version')
 files[gradle]=source.replace(/versionCode\s+\d+/,`versionCode ${release.androidVersionCode}`).replace(/versionName\s+"[^"]+"/,`versionName "${release.version}"`)
 const desktopStart='desktop/start.html',start=read(desktopStart)
 const desktopVersion=/(<p class="tag">Windows 桌面客户端 · v)[^<]+(<\/p>)/g
 if([...start.matchAll(desktopVersion)].length!==1)throw Error('Missing or ambiguous desktop start page release version')
 files[desktopStart]=start.replace(desktopVersion,(_,prefix,suffix)=>prefix+release.version+suffix)
 const data={version:release.version,channel:release.channel}
 files['miniprogram/utils/generated/release-info.js']='// Generated from config/client-release.json. Do not edit.\nmodule.exports = '+JSON.stringify(data,null,2)+'\n'
 files['miniprogram/utils/generated/release-info.d.ts']='// Generated from config/client-release.json. Do not edit.\ndeclare const release: {readonly version:'+JSON.stringify(release.version)+';readonly channel:'+JSON.stringify(release.channel)+'}\nexport = release\n'
 for(const [name,content] of Object.entries(files)){
  const file=resolve(root,name)
  if(check){if(!existsSync(file)||read(name)!==content)throw Error('Client release metadata drift or missing output: '+name)}
 }
 if(!check)for(const [name,content] of Object.entries(files)){const file=resolve(root,name);mkdirSync(dirname(file),{recursive:true});writeFileSync(file,content)}
 return release
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const check=process.argv.includes('--check');const release=syncRelease({check});console.log(`PASS ${release.product} ${release.version}: client metadata ${check?'matches':'synchronized'}`)
}
