const test = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs/promises')
const path = require('node:path')
const { Readable, Writable, PassThrough } = require('node:stream')
const { createHandler } = require('./server.cjs')

class Response extends Writable {
  constructor() { super(); this.headers = {}; this.chunks = []; this.done = new Promise(resolve => this.on('finish', resolve)) }
  _write(chunk, encoding, callback) { this.chunks.push(Buffer.from(chunk)); callback() }
  writeHead(status, headers = {}) { this.statusCode = status; Object.assign(this.headers, headers); this.headersSent = true; return this }
  setHeader(name, value) { this.headers[name] = value }
  get text() { return Buffer.concat(this.chunks).toString() }
}
function request(url, options = {}) {
  const req = Readable.from(options.body ? [options.body] : [])
  Object.assign(req, { url, method: options.method || 'GET', headers: { host: '127.0.0.1:34567', ...options.headers } })
  return req
}
async function execute(handler, url, options) {
  const res = new Response(); handler(request(url, options), res); await res.done; return res
}

test('SPA assets serve, malformed paths cannot crash and sibling paths stay outside the allowlist', async () => {
  const runtime = path.resolve(__dirname, '../.runtime')
  await fs.mkdir(runtime, { recursive: true })
  const root = await fs.mkdtemp(path.join(runtime, 'desktop-unit-'))
  assert.equal(path.dirname(root), runtime)
  const web = path.join(root, 'web'); await fs.mkdir(web)
  await fs.writeFile(path.join(web, 'index.html'), 'synthetic SPA')
  await fs.mkdir(path.join(root, 'web-private')); await fs.writeFile(path.join(root, 'web-private', 'secret.txt'), 'never expose')
  try {
    const handler = createHandler({ webRoot: web })
    assert.equal((await execute(handler, '/province/anhui')).text, 'synthetic SPA')
    assert.equal((await execute(handler, '/%E0%A4%A')).statusCode, 400)
    const traversal = await execute(handler, '/..%2fweb-private%2fsecret.txt')
    assert.equal(traversal.statusCode, 403); assert.doesNotMatch(traversal.text, /never expose/)
  } finally { await fs.rm(root, { recursive: true, force: true }) }
})

test('same-origin API request streams unchanged to fixed loopback backend; external origins cannot proxy', async () => {
  let options; let body = ''; let calls = 0
  const handler = createHandler({ webRoot: __dirname, apiRequest: (settings, callback) => {
    calls++; options = settings
    const upstream = new Writable({ write(chunk, encoding, done) { body += chunk; done() } })
    upstream.setTimeout = () => upstream
    upstream.on('finish', () => {
      const incoming = new PassThrough(); incoming.statusCode = 200; incoming.headers = { 'content-type': 'text/plain' }
      callback(incoming); incoming.write('first'); setImmediate(() => incoming.end('second'))
    })
    return upstream
  } })
  const res = await execute(handler, '/api/ask', { method: 'POST', body: '{"question":"synthetic"}', headers: { origin: 'http://127.0.0.1:34567', 'content-type': 'application/json' } })
  assert.equal(options.hostname, '127.0.0.1'); assert.equal(options.port, 8000); assert.equal(options.path, '/api/ask')
  assert.equal(body, '{"question":"synthetic"}'); assert.equal(res.text, 'firstsecond')
  assert.equal((await execute(handler, '/api/ask', { method: 'POST', headers: { origin: 'https://outside.invalid' } })).statusCode, 403)
  assert.equal(calls, 1)
})

test('unavailable backend gives a usable dependency message rather than pretending services are bundled', async () => {
  const handler = createHandler({ webRoot: __dirname, apiRequest: () => {
    const upstream = new Writable({ write(chunk, encoding, done) { done() } }); upstream.setTimeout = () => upstream
    setImmediate(() => upstream.emit('error', new Error('synthetic refusal'))); return upstream
  } })
  const res = await execute(handler, '/api/regional-guides/report')
  assert.equal(res.statusCode, 503); assert.match(res.text, /127.0.0.1:8000/)
  assert.doesNotMatch(res.text, /synthetic refusal/)
})
