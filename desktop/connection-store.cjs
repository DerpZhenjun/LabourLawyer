// Only public service addresses. Identity, sessions, documents and file paths are not accepted.
const fs=require('node:fs'),path=require('node:path'),{randomUUID}=require('node:crypto')
function createConnectionStore(file,normalize){
 const validate=value=>{
  if(value===null)return null
  if(!value||typeof value!=='object'||Array.isArray(value)||Object.keys(value).sort().join(',')!=='api,digital'||typeof value.api!=='string'||typeof value.digital!=='string')throw Error('Invalid connection settings')
  return {api:normalize(value.api),digital:value.digital?normalize(value.digital):''}
 }
 const read=()=>{
  if(!fs.existsSync(file))return null
  const stat=fs.lstatSync(file);if(!stat.isFile()||stat.isSymbolicLink()||stat.size>4096)throw Error('Invalid connection file')
  return validate(JSON.parse(fs.readFileSync(file,'utf8')))
 }
 const write=value=>{
  const next=validate(value)
  if(next===null){if(fs.existsSync(file)){if(fs.lstatSync(file).isSymbolicLink())throw Error('Invalid connection file');fs.unlinkSync(file)}return}
  if(fs.existsSync(file)&&fs.lstatSync(file).isSymbolicLink())throw Error('Invalid connection file')
  fs.mkdirSync(path.dirname(file),{recursive:true})
  const temporary=file+'.'+randomUUID()+'.tmp'
  try{fs.writeFileSync(temporary,JSON.stringify(next)+'\n',{encoding:'utf8',mode:0o600,flag:'wx'});fs.renameSync(temporary,file)}
  finally{if(fs.existsSync(temporary))fs.unlinkSync(temporary)}
 }
 return {read,write}
}
function handleConnectionRequest(event,payload,trusted,store){
 event.returnValue={ok:false}
 try{
  if(!trusted(event)||!payload||typeof payload!=='object'||Array.isArray(payload))return
  if(payload.action==='read'&&Object.keys(payload).join(',')==='action')event.returnValue={ok:true,value:store.read()}
  else if(payload.action==='write'&&Object.keys(payload).sort().join(',')==='action,value'){store.write(payload.value);event.returnValue={ok:true,value:null}}
 }catch{/* Keep filesystem details outside the renderer. No credentials are stored here. */}
}
function trustedConnectionFrame(event,windows){
 try{return windows.get(event.sender.id)===new URL(event.senderFrame.url).origin&&event.senderFrame===event.sender.mainFrame&&windows.has(event.sender.id)}catch{return false}
}
module.exports={createConnectionStore,handleConnectionRequest,trustedConnectionFrame}
