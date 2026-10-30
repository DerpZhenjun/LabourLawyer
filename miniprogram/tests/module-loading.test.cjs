const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')
const root = path.resolve(__dirname, '..')
const cache = new Map()
function load(file) {
  assert(!file.endsWith('.json'), 'WeChat does not register JSON as a JavaScript module: ' + path.relative(root, file))
  if (!file.endsWith('.js')) file += '.js'
  if (cache.has(file)) return cache.get(file).exports
  const module = {exports: {}}; cache.set(file, module)
  vm.runInNewContext(fs.readFileSync(file, 'utf8'), {module, exports: module.exports, require: ref => load(path.resolve(path.dirname(file), ref)), Page() {}, App() {}, wx: {}, getApp: () => ({globalData: {}})}, {filename: file})
  return module.exports
}
for (const entry of ['app.js','utils/documents.js',...fs.readdirSync(path.join(root,'pages')).map(name=>'pages/'+name+'/index.js')]) load(path.join(root, entry))
for (const name of ['provinces', 'documentForms', 'provinceExperiences']) {
  assert.deepEqual(JSON.parse(JSON.stringify(load(path.join(root, 'data', name + '.js')))), JSON.parse(fs.readFileSync(path.join(root, 'data', name + '.json'), 'utf8')), name + ' CJS data must match its source exactly')
}
console.log('PASS simulator-compatible JS module loading and 3 exact source-data parity checks')
