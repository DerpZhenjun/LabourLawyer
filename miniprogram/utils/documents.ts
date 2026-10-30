import type { Province, CatalogProvince, DocumentKind, FormConfig, LegacyForm, DocumentFieldDefinition } from '../../packages/client-contracts/src/documents';
import type { AppState } from '../types/runtime';
import { isRecord, isCatalogProvince } from './generated/document-contracts';
import provinces = require('../data/provinces');
import schema = require('../data/documentForms');
const evidenceKeys = ['name', 'pageCount', 'source', 'purpose', 'kind', 'originalType', 'hasOriginal', 'pageRange', 'itemCount', 'notes'];
const derived = ['contractPeriod', 'proof', 'applicantAddressWithPostalCode', 'respondentAddressWithPostalCode'];
function findProvince(slug: string | undefined) { return provinces.find(p => p.slug === slug); }
function formConfig(province: Province, kind: DocumentKind): FormConfig {
    const live = province.forms;
    return {
        fields: live ? live[kind === 'application' ? 'applicationFields' : 'evidenceFields'] : schema[kind === 'application' ? 'applicationSupportedFields' : 'evidenceSupportedFields'][province.slug] || [],
        limits: live ? live.limits : schema.limits[province.slug] || schema.limits.default,
        definitions: live ? live.fieldDefinitions : schema.fields,
    };
}
function fieldViews(keys: string[], definitions: Record<string, DocumentFieldDefinition>) {
    return keys.filter(key => !derived.includes(key) && key !== 'requests' && key !== 'factsReason')
        .map(key => ({ key, ...definitions[key]! })).filter(field => field.label);
}
function blankForm(config:FormConfig,kind:'application'):LegacyForm&{requests:string[]};
function blankForm(config:FormConfig,kind:'evidence'):LegacyForm&{evidenceList:Record<string,unknown>[]};
function blankForm(config:FormConfig,kind:DocumentKind):LegacyForm;
function blankForm(config: FormConfig, kind: DocumentKind): LegacyForm {
    const form: LegacyForm = Object.fromEntries(config.fields.filter(k => !derived.includes(k)).map(k => [k, k === 'copyCount' ? 1 : '']));
    if (kind === 'application')
        form.requests = [''];
    else
        form.evidenceList = [Object.fromEntries(evidenceKeys.filter(k => config.fields.includes(k)).map(k => [k, '']))];
    return form;
}
function payloadFor(form: LegacyForm, config: FormConfig, kind: DocumentKind) {
    const payload: Record<string, unknown> = {};
    for (const key of config.fields) {
        if (derived.includes(key) || evidenceKeys.includes(key) || key === 'requests')
            continue;
        if (form[key] !== undefined)
            payload[key] = key === 'copyCount' ? Number(form[key]) : String(form[key]).trim();
    }
    if (kind === 'application') {
        payload.requests = (form.requests || []).map(s => String(s).trim()).filter(Boolean);
        if ((payload.requests as string[]).length > config.limits.maxRequests)
            throw new Error(`最多填写 ${config.limits.maxRequests} 项请求`);
        if ((payload.requests as string[]).some(s => s.length > config.limits.requestLength))
            throw new Error(`单项请求最多 ${config.limits.requestLength} 字`);
        if (String(payload.factsReason || '').length > config.limits.factsLength)
            throw new Error(`事实与理由最多 ${config.limits.factsLength} 字`);
    }
    else {
        const rows = (form.evidenceList || []).map(row => Object.fromEntries(evidenceKeys.filter(k => config.fields.includes(k)).map(k => [k, String(row[k] || '').trim()])));
        if (rows.length > config.limits.maxEvidence)
            throw new Error(`最多填写 ${config.limits.maxEvidence} 项证据`);
        rows.forEach((row, i) => { if (!row.name && Object.values(row).some(Boolean))
            throw new Error(`请补充第 ${i + 1} 项证据名称`); });
        payload.evidenceList = rows.filter(row => row.name);
    }
    return payload;
}
function isDocx(buffer: unknown): buffer is ArrayBuffer {
    if (!(buffer instanceof ArrayBuffer))
        return false;
    const bytes = new Uint8Array(buffer);
    return bytes.length >= 4 && bytes[0] === 0x50 && bytes[1] === 0x4b && bytes[2] === 3 && bytes[3] === 4;
}
function errorMessage(buffer: unknown) {
    try {
        const encoded = Array.from(new Uint8Array(buffer as ArrayBuffer)).map(b => '%' + b.toString(16).padStart(2, '0')).join('');
        const raw: unknown = JSON.parse(decodeURIComponent(encoded));
        const detail = isRecord(raw) ? raw.detail : undefined;
        return typeof detail === 'string' ? detail : '填写内容不符合模板要求，请检查字段和长度';
    }
    catch {
        return '没有收到有效 Word 文书，请检查后端服务';
    }
}
function apiBase() { return getApp<AppState>().globalData.apiBase.replace(/\/$/, ''); }
function loadCatalog(success: (items: CatalogProvince[]) => void, fail?: () => void) {
    wx.request<Record<string, unknown> | string | ArrayBuffer>({ url: apiBase() + '/api/province-documents', timeout: 15000,
        success: res => res.statusCode === 200 && isRecord(res.data) && Array.isArray(res.data.items) && res.data.items.every(isCatalogProvince) ? success(res.data.items) : fail && fail(),
        fail: () => fail && fail(),
    });
}
function mergeCatalog(items: CatalogProvince[]): Province[] {
    return items.flatMap(item => { const base = findProvince(item.slug); return base ? [{ ...base, ...item, shortName: item.shortName || base.shortName }] : []; });
}
export { mergeCatalog, provinces, schema, evidenceKeys, findProvince, formConfig, fieldViews, blankForm, payloadFor, isDocx, errorMessage, apiBase, loadCatalog };
