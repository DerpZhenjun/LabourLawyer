const fs = require('node:fs')
const path = require('node:path')
const { spawnSync } = require('node:child_process')

const root = path.resolve(__dirname, '..')
const version = require('./package.json').version
if (!/^[0-9]+\.[0-9]+\.[0-9]+(?:-[a-zA-Z0-9.-]+)?$/.test(version)) throw new Error('Invalid release version')
const output = path.join(root, '.runtime/releases', version, 'desktop')
const notices = path.join(output, 'notices')
fs.mkdirSync(notices, { recursive: true })
const env = { ...process.env, ELECTRON_BUILDER_CACHE: path.join(output, 'cache/electron-builder'), ELECTRON_CACHE: path.join(output, 'cache/electron'), NPM_CONFIG_CACHE: path.join(root, '.runtime/launch-center/cache/npm'), TEMP: path.join(output, 'temp'), TMP: path.join(output, 'temp'), VITE_API_BASE_URL: '/', VITE_DIGITAL_LAWYER_URL: 'http://127.0.0.1:3000', CSC_IDENTITY_AUTO_DISCOVERY: 'false' }
fs.mkdirSync(env.TEMP, { recursive: true })
function run(script, args, cwd = root) {
  const result = spawnSync(process.execPath, [script, ...args], { cwd, env, stdio: 'inherit', windowsHide: true })
  if (result.status !== 0) throw new Error(`Build step failed: ${path.basename(script)} (${result.status})`)
}
run(path.join(root, 'frontend/node_modules/vite/bin/vite.js'), ['build', '--outDir', path.join(output, 'web'), '--emptyOutDir'], path.join(root, 'frontend'))

const projectLicense = fs.readFileSync(path.join(root, 'LICENSE'), 'utf8')
fs.writeFileSync(path.join(notices, 'LICENSE-LabourLawyer.txt'), projectLicense)
fs.copyFileSync(path.join(__dirname, 'README.md'), path.join(notices, 'README-Desktop.md'))
fs.writeFileSync(path.join(notices, 'INSTALL-LICENSE.txt'), 'LabourLawyer Windows 桌面客户端 '+require('./package.json').version+'\n\n本安装包仅含桌面界面，不含 Python 后端、官方模板原件库、个人案件库或AI模型。文书功能需另行运行本项目后端，默认 http://127.0.0.1:8000；也可通过连接设置使用已部署的 Ubuntu 服务。AI由后端连接Ubuntu模型。安装本包不会启动模型或后端。此包尚未代码签名。\n\n'+projectLicense)
const lock = JSON.parse(fs.readFileSync(path.join(root, 'frontend/package-lock.json'), 'utf8'))
const audit = []
let combined = 'Third-party notices for bundled frontend components\n\nElectron MIT LICENSE and Chromium/Node notices are included beside the executable (LICENSE.electron.txt / LICENSES.chromium.html).\nFont Awesome: Fonticons, Inc.; icons CC BY 4.0, fonts SIL OFL 1.1, code MIT. Full text follows.\n\n'
for (const [relative, metadata] of Object.entries(lock.packages)) {
  if (!relative.startsWith('node_modules/') || metadata.dev) continue
  const folder = path.join(root, 'frontend', relative)
  const packageFile = path.join(folder, 'package.json')
  if (!fs.existsSync(packageFile)) {
    if (metadata.optional) continue
    throw new Error(`Missing installed runtime dependency: ${relative}`)
  }
  const pkg = JSON.parse(fs.readFileSync(packageFile, 'utf8'))
  const files = fs.readdirSync(folder).filter(name => /^(licen[cs]e|copying|notice)([._-]|$)/i.test(name) && fs.statSync(path.join(folder, name)).isFile())
  if (!files.length && fs.existsSync(path.join(folder, 'README.md')) && /\(The MIT License\)/.test(fs.readFileSync(path.join(folder, 'README.md'), 'utf8'))) files.push('README.md')
  const vueNotice = pkg.name === '@vue/devtools-api' && pkg.version === '6.6.4'
  if (vueNotice) files.push('upstream-v6.6.4-LICENSE')
  audit.push({ name: pkg.name, version: pkg.version, license: pkg.license || metadata.license || 'UNDECLARED', notices: files })
  combined += `\n===== ${pkg.name} ${pkg.version} (${pkg.license || metadata.license || 'UNDECLARED'}) =====\n`
  for (const name of files) combined += `\n--- ${name} ---\n${fs.readFileSync(name === 'upstream-v6.6.4-LICENSE' ? path.join(__dirname, 'licenses/vue-devtools-v6.6.4-LICENSE.txt') : path.join(folder, name), 'utf8')}\n`
}
if (audit.some(item => item.license === 'UNDECLARED' || item.notices.length === 0)) throw new Error('Runtime dependency missing license information; inspect before packaging')
fs.writeFileSync(path.join(notices, 'THIRD-PARTY-NOTICES.txt'), combined)
fs.writeFileSync(path.join(output, 'license-audit.json'), JSON.stringify(audit, null, 2)+'\n')
if (!process.argv.includes('--web-only')) {
  const config = structuredClone(require('./package.json').build)
  config.directories.output = path.join(output, 'artifacts')
  config.extraResources = [{ from: path.join(output, 'web'), to: 'web' }, { from: notices, to: 'notices' }]
  config.nsis.license = path.join(notices, 'INSTALL-LICENSE.txt')
  const configPath = path.join(output, 'builder-config.json')
  fs.writeFileSync(configPath, JSON.stringify(config, null, 2)+'\n')
  run(path.join(__dirname, 'node_modules/electron-builder/cli.js'), ['--win', 'nsis', 'portable', '--x64', '--publish', 'never', '--config='+configPath, '--config.electronDist='+path.join(__dirname, 'node_modules/electron/dist')], __dirname)
}
