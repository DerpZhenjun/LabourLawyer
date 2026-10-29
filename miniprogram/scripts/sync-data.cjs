const fs = require('node:fs')
const path = require('node:path')
const root = path.resolve(__dirname, '..')
const check = process.argv.includes('--check')
for (const name of ['provinces', 'documentForms', 'provinceExperiences']) {
  const source = JSON.parse(fs.readFileSync(path.join(root, 'data', name + '.json'), 'utf8'))
  const output = '// Generated from ' + name + '.json by scripts/sync-data.cjs. Do not edit.\nmodule.exports = ' + JSON.stringify(source, null, 2) + '\n'
  const destination = path.join(root, 'data', name + '.js')
  if (check) {
    if (!fs.existsSync(destination) || fs.readFileSync(destination, 'utf8') !== output) throw new Error('Stale generated data: ' + name + '.js; run node miniprogram/scripts/sync-data.cjs')
  } else fs.writeFileSync(destination, output)
}
console.log(check ? 'PASS generated mini data is synchronized' : 'Generated 3 WeChat-compatible data modules')
