const { app, BrowserWindow, shell } = require('electron')
const http = require('node:http')
const path = require('node:path')
const { createHandler } = require('./server.cjs')

const isDev = !app.isPackaged
let staticServer

function startStaticServer() {
  const webRoot = path.resolve(process.resourcesPath, 'web')
  return new Promise((resolve, reject) => {
    staticServer = http.createServer(createHandler({ webRoot }))
    staticServer.once('error', reject)
    staticServer.listen(0, '127.0.0.1', () => resolve(`http://127.0.0.1:${staticServer.address().port}`))
  })
}

async function createWindow() {
  const win = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 1080,
    minHeight: 700,
    show: false,
    backgroundColor: '#f3f6f9',
    title: 'LabourLawyer · 劳动仲裁文书助手（需本地后端）',
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  })

  win.once('ready-to-show', () => win.show())
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:/.test(url)) shell.openExternal(url)
    return { action: 'deny' }
  })
  if (isDev) {
    const devUrl = process.env.LABOURLAWYER_DEV_URL || 'http://127.0.0.1:5173'
    win.webContents.on('will-navigate', (event, url) => { if (new URL(url).origin !== new URL(devUrl).origin) event.preventDefault() })
    await win.loadURL(devUrl)
  } else {
    const appUrl = staticServer ? `http://127.0.0.1:${staticServer.address().port}` : await startStaticServer()
    win.webContents.on('will-navigate', (event, url) => { if (new URL(url).origin !== appUrl) event.preventDefault() })
    await win.loadURL(appUrl + '/__desktop/start')
  }
}

app.whenReady().then(() => {
  createWindow()
  app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow() })
})
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit() })
app.on('before-quit', () => staticServer?.close())
