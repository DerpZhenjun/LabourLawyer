const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')
const docs = require('../miniprogram/utils/documents')
const root = path.resolve(__dirname, '..')
const payloads = []
for (const province of docs.provinces) {
  assert(province.region, `Province must remain visible in a home page region group: ${province.slug}`)
  for (const kind of ['application', 'evidence']) {
    if (!province.documents[kind]) continue
    const config = docs.formConfig(province, kind)
    const payload = docs.payloadFor(province[kind + 'Example'], config, kind)
    assert(!('submitterName' in payload), 'Handwritten evidence signatures must not be sent as typed names')
    assert(config.fields.length > 0)
    const views = docs.fieldViews(config.fields, config.definitions)
    const omitted = config.fields.filter(k => !['contractPeriod','proof','applicantAddressWithPostalCode','respondentAddressWithPostalCode','requests','factsReason'].includes(k) && !views.some(v => v.key === k))
    assert.deepEqual(omitted, [], `${province.slug} ${kind} has a missing input label`)
    payloads.push({ slug: province.slug, kind, payload })
  }
}
assert.equal(payloads.length, 34)
assert.equal(docs.provinces.filter(p => p.hasApplication).length, 21)
assert.equal(docs.provinces.filter(p => p.hasEvidence).length, 13)
assert.throws(() => docs.payloadFor({ requests: ['一','二','三'] }, docs.formConfig(docs.findProvince('hainan'),'application'), 'application'), /最多/)
assert.throws(() => docs.payloadFor({ evidenceList: [{ purpose: '证明关系' }] }, docs.formConfig(docs.findProvince('jiangsu'),'evidence'), 'evidence'), /证据名称/)
assert(!docs.isDocx(new TextEncoder().encode('{"error":true}').buffer))
assert(docs.isDocx(new Uint8Array([80,75,3,4]).buffer))
assert.equal(docs.errorMessage(new TextEncoder().encode('{"detail":"缺少模板"}').buffer), '缺少模板')

// Run the real Page script with mocked WeChat platform IO. Test HTTP payload,
// ZIP validation, file writing, native document opening and distinct drafts.
let page, lastRequest, written, opened, catalogRequest, failPreview = false
const storage = {}
const wx = {
  env: { USER_DATA_PATH: '/device/files' },
  getStorageSync: k => storage[k], setStorageSync: (k,v) => { storage[k] = structuredClone(v) }, removeStorageSync: k => { delete storage[k] },
  setNavigationBarTitle() {}, showModal: options => options.success({ confirm: true }),
  request: options => {
    lastRequest = options
    if (options.method !== 'POST') { catalogRequest = options; return }
    options.success({ statusCode: 200, data: new Uint8Array([80,75,3,4]).buffer })
  },
  getFileSystemManager: () => ({ writeFile: options => { written = options; options.success() } }),
  openDocument: options => { opened = options; if (failPreview) options.fail(); else options.success() },
}
global.wx = wx
global.getApp = () => ({ globalData: { apiBase: 'http://127.0.0.1:8000' } })
vm.runInNewContext(fs.readFileSync(path.join(root,'miniprogram/pages/document/index.js'),'utf8'), { require: name => require(path.resolve(root,'miniprogram/pages/document',name)), wx, Page: value => { page = value }, Array, Object, JSON, String, Number, Date })
page.setData = values => { Object.assign(page.data, values) }
page.onLoad({ slug: 'jiangsu', kind: 'application' })
// A late catalog response must preserve information typed while it loaded.
page.data.form.applicantName = '加载期间填写'
catalogRequest.success({ statusCode: 200, data: { items: [{ ...docs.findProvince('jiangsu'), forms: { applicationFields: docs.schema.applicationSupportedFields.jiangsu, evidenceFields: docs.schema.evidenceSupportedFields.jiangsu, limits: docs.schema.limits.default, fieldDefinitions: docs.schema.fields } }] } })
assert.equal(page.data.form.applicantName, '加载期间填写')
page.data.form = docs.findProvince('jiangsu').applicationExample
page.generate()
assert.match(lastRequest.url, /jiangsu\/application\/generate$/)
assert.equal(lastRequest.responseType, 'arraybuffer')
assert.equal(lastRequest.timeout, 60000)
assert(written.filePath.endsWith('.docx'))
assert.equal(opened.fileType, 'docx')
assert.equal(opened.showMenu, true)
assert.equal(page.data.busy, false)
failPreview = true
page.generate()
assert.equal(page.data.busy, false)
assert.match(page.data.error, /无法预览/)
failPreview = false
page.onUnload()
assert(storage['labourlawyer-jiangsu-application-v1'])
page.onLoad({ slug: 'tianjin', kind: 'evidence' })
assert.equal(page.draftKey, 'labourlawyer-tianjin-evidence-v1')
assert.equal(page.data.form.evidenceList[0].name, '')
page.onLoad({ slug: 'hebei', kind: 'application' })
assert.equal(page.data.available, false)

const output = path.join(root,'.runtime/document-audit/mini-payloads.json')
fs.mkdirSync(path.dirname(output), { recursive: true })
fs.writeFileSync(output, JSON.stringify(payloads, null, 2))
console.log(`PASS: 34 actual client payloads; provincial capacity; partial evidence; binary Word download; native preview failure; catalog refresh race; separate drafts; unsupported templates`)
