const { contextBridge, ipcRenderer } = require('electron')
function connectionRequest(payload){
  const result=ipcRenderer.sendSync('labourlawyer:connection',payload)
  if(!result||result.ok!==true)throw Error('连接设置读取或保存失败。')
  return result.value
}

contextBridge.exposeInMainWorld('labourLawyerDesktop', Object.freeze({
  platform: process.platform,
  desktop: true,
  version: '1.2.0-preview.4',
  bundledBackend: false,
  bundledModel: false,
  connection: Object.freeze({
    read:()=>connectionRequest({action:'read'}),
    write:value=>connectionRequest({action:'write',value}),
  }),
}))
