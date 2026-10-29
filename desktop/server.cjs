const fs = require('node:fs')
const http = require('node:http')
const path = require('node:path')

const mime = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.svg': 'image/svg+xml', '.json': 'application/json', '.woff': 'font/woff', '.woff2': 'font/woff2', '.png': 'image/png', '.jpg': 'image/jpeg', '.ico': 'image/x-icon' }
function createHandler({ webRoot, apiRequest = http.request }) {
  const root = path.resolve(webRoot)
  return (req, res) => {
    const host = req.headers.host || ''
    if (!/^127\.0\.0\.1:\d+$/.test(host) || (req.headers.origin && req.headers.origin !== `http://${host}`)) {
      res.writeHead(403); return res.end('Forbidden origin')
    }
    let pathname
    try { pathname = decodeURIComponent(new URL(req.url, `http://${host}`).pathname) }
    catch { res.writeHead(400); return res.end('Invalid path') }
    if (pathname.startsWith('/api/') || pathname === '/health') {
      const headers = { ...req.headers, host: '127.0.0.1:8000' }
      delete headers.connection
      const upstream = apiRequest({ hostname: '127.0.0.1', port: 8000, path: req.url, method: req.method, headers }, incoming => {
        res.writeHead(incoming.statusCode, incoming.headers)
        incoming.on('error', () => res.destroy())
        incoming.pipe(res)
      })
      upstream.setTimeout(300000, () => upstream.destroy(new Error('Backend timeout')))
      upstream.on('error', () => {
        if (res.headersSent) return res.destroy()
        res.writeHead(503, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' })
        res.end(JSON.stringify({ detail: '请先运行本项目后端 http://127.0.0.1:8000；桌面安装包不包含后端或模型。' }))
      })
      req.on('aborted', () => upstream.destroy())
      res.on('close', () => { if (!res.writableEnded) upstream.destroy() })
      req.pipe(upstream)
      return
    }
    if (!['GET', 'HEAD'].includes(req.method)) { res.writeHead(405); return res.end('Method not allowed') }
    const requested = pathname === '/' ? 'index.html' : pathname.replace(/^\/+/, '')
    let filePath = path.resolve(root, requested)
    const relative = path.relative(root, filePath)
    if (relative.startsWith('..') || path.isAbsolute(relative)) { res.writeHead(403); return res.end('Forbidden') }
    if (pathname === '/__desktop/start') filePath = path.join(__dirname, 'start.html')
    else if (!path.extname(filePath)) filePath = path.join(root, 'index.html')
    fs.readFile(filePath, (error, data) => {
      if (error) { res.writeHead(404); return res.end('Not found') }
      res.writeHead(200, { 'Content-Type': mime[path.extname(filePath)] || 'application/octet-stream', 'X-Content-Type-Options': 'nosniff', 'Cache-Control': path.extname(filePath) === '.html' ? 'no-store' : 'public, max-age=31536000, immutable' })
      res.end(req.method === 'HEAD' ? undefined : data)
    })
  }
}

module.exports = { createHandler }
