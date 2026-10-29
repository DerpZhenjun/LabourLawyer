const provinces = require('../data/provinces')
const schema = require('../data/documentForms')
const evidenceKeys = ['name', 'pageCount', 'source', 'purpose', 'kind', 'originalType', 'hasOriginal', 'pageRange', 'itemCount', 'notes']
const derived = ['contractPeriod', 'proof', 'applicantAddressWithPostalCode', 'respondentAddressWithPostalCode']

function findProvince(slug) { return provinces.find(p => p.slug === slug) }
function formConfig(province, kind) {
  const live = province.forms
  return {
    fields: live ? live[kind + 'Fields'] : schema[kind + 'SupportedFields'][province.slug] || [],
    limits: live ? live.limits : schema.limits[province.slug] || schema.limits.default,
    definitions: live ? live.fieldDefinitions : schema.fields,
  }
}
function fieldViews(keys, definitions) {
  return keys.filter(key => !derived.includes(key) && key !== 'requests' && key !== 'factsReason')
    .map(key => ({ key, ...definitions[key] })).filter(field => field.label)
}
function blankForm(config, kind) {
  const form = Object.fromEntries(config.fields.filter(k => !derived.includes(k)).map(k => [k, k === 'copyCount' ? 1 : '']))
  if (kind === 'application') form.requests = ['']
  else form.evidenceList = [Object.fromEntries(evidenceKeys.filter(k => config.fields.includes(k)).map(k => [k, '']))]
  return form
}
function payloadFor(form, config, kind) {
  const payload = {}
  for (const key of config.fields) {
    if (derived.includes(key) || evidenceKeys.includes(key) || key === 'requests') continue
    if (form[key] !== undefined) payload[key] = key === 'copyCount' ? Number(form[key]) : String(form[key]).trim()
  }
  if (kind === 'application') {
    payload.requests = (form.requests || []).map(s => String(s).trim()).filter(Boolean)
    if (payload.requests.length > config.limits.maxRequests) throw new Error(`最多填写 ${config.limits.maxRequests} 项请求`)
    if (payload.requests.some(s => s.length > config.limits.requestLength)) throw new Error(`单项请求最多 ${config.limits.requestLength} 字`)
    if ((payload.factsReason || '').length > config.limits.factsLength) throw new Error(`事实与理由最多 ${config.limits.factsLength} 字`)
  } else {
    const rows = (form.evidenceList || []).map(row => Object.fromEntries(evidenceKeys.filter(k => config.fields.includes(k)).map(k => [k, String(row[k] || '').trim()])))
    if (rows.length > config.limits.maxEvidence) throw new Error(`最多填写 ${config.limits.maxEvidence} 项证据`)
    rows.forEach((row, i) => { if (!row.name && Object.values(row).some(Boolean)) throw new Error(`请补充第 ${i + 1} 项证据名称`) })
    payload.evidenceList = rows.filter(row => row.name)
  }
  return payload
}
function isDocx(buffer) {
  if (!(buffer instanceof ArrayBuffer)) return false
  const bytes = new Uint8Array(buffer)
  return bytes.length >= 4 && bytes[0] === 0x50 && bytes[1] === 0x4b && bytes[2] === 3 && bytes[3] === 4
}
function errorMessage(buffer) {
  try {
    const encoded = Array.from(new Uint8Array(buffer)).map(b => '%' + b.toString(16).padStart(2, '0')).join('')
    const detail = JSON.parse(decodeURIComponent(encoded)).detail
    return typeof detail === 'string' ? detail : '填写内容不符合模板要求，请检查字段和长度'
  } catch { return '没有收到有效 Word 文书，请检查后端服务' }
}
function apiBase() { return getApp().globalData.apiBase.replace(/\/$/, '') }
function loadCatalog(success, fail) {
  wx.request({ url: apiBase() + '/api/province-documents', timeout: 15000,
    success: res => res.statusCode === 200 && Array.isArray(res.data.items) ? success(res.data.items) : fail && fail(),
    fail: () => fail && fail(),
  })
}
module.exports = { provinces, schema, evidenceKeys, findProvince, formConfig, fieldViews, blankForm, payloadFor, isDocx, errorMessage, apiBase, loadCatalog }
