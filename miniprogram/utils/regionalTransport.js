// Generated from utils/regionalTransport.ts. Do not edit.
// source-sha256: 49d83855baa4c57b531daa323a6cb7c6a0b58aa71fb897c75dd7cc4b0cdbf6e5
"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.isWordZip = void 0;
exports.createRegionalTransport = createRegionalTransport;
exports.header = header;
exports.decodeError = decodeError;
const shared = require("./generated/regional-contracts");
function createRegionalTransport(api, base) {
    const query = (region, extra) => {
        const scope = shared.regionQuery({ province: region.province, city: region.city || '', district: region.district || '', case_scope: region.case_scope });
        const suffix = Object.keys(extra || {}).filter(k => extra[k] !== undefined).map(k => `${encodeURIComponent(k)}=${encodeURIComponent(String(extra[k]))}`).join('&');
        return scope + (suffix ? (scope ? '&' : '') + suffix : '');
    };
    const send = (route, options, callbacks) => api.request({ url: `${base().replace(/\/$/, '')}/api/regional-guides/${route}`, timeout: 15000, ...options, ...callbacks });
    return {
        areas: (region, callbacks) => send(`areas?${query(region, { xlsx: true })}`, {}, callbacks),
        lookup: (region, callbacks) => send(`lookup?${query(region, { xlsx: true })}`, {}, callbacks),
        formContract: (context, callbacks) => send(`form-contract?${query(context, { source_id: context.source_id, version: context.version, template_id: context.template_id, kind: context.kind, xlsx: true })}`, {}, callbacks),
        generate: (payload, callbacks) => send('generate?xlsx=true', { method: 'POST', data: payload, responseType: 'arraybuffer', timeout: 60000 }, callbacks),
        downloadTemplate: (context, callbacks) => send(`templates/${encodeURIComponent(context.template_id || '')}?${query(context, { source_id: context.source_id, version: context.version })}`, { responseType: 'arraybuffer', timeout: 60000 }, callbacks),
    };
}
function header(headers, name) {
    const key = Object.keys(headers || {}).find(k => k.toLowerCase() === name.toLowerCase());
    return key === undefined ? '' : String(headers?.[key]);
}
const isWordZip = (buffer) => shared.isOfficeZip(buffer, 'docx');
exports.isWordZip = isWordZip;
function decodeError(buffer) {
    try {
        let encoded = '';
        new Uint8Array(buffer).forEach(b => { encoded += '%' + ('0' + b.toString(16)).slice(-2); });
        return shared.parseApiError(JSON.parse(decodeURIComponent(encoded)), '请求失败，请重新核对本区指南');
    }
    catch (_) {
        return '请求失败，请重新核对本区指南';
    }
}
