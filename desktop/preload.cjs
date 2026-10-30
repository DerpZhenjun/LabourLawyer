const { contextBridge } = require('electron')

contextBridge.exposeInMainWorld('labourLawyerDesktop', Object.freeze({
  platform: process.platform,
  desktop: true,
  version: '1.2.0-preview.3',
  bundledBackend: false,
  bundledModel: false,
}))
