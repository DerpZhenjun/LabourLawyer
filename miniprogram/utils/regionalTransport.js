// Generated from utils/regionalTransport.ts. Do not edit.
// source-sha256: 3096e6cb7ffa15c7e344b0e2a33fc67462eb5c09f9fa0f58206fb8c278e63d67
"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.createRegionalTransport = createRegionalTransport;
exports.header = header;
exports.isWordZip = isWordZip;
exports.decodeError = decodeError;
const shared = require("./generated/regional-contracts");
function createRegionalTransport(api, base) {
    const query = (region, extra) => {
        const scope = shared.regionQuery({ province: region.province, city: region.city || '', district: region.district || '' });
        const suffix = Object.keys(extra || {}).filter(k => extra[k] !== undefined).map(k => `${encodeURIComponent(k)}=${encodeURIComponent(String(extra[k]))}`).join('&');
        return scope + (suffix ? (scope ? '&' : '') + suffix : '');
    };
    const send = (route, options, callbacks) => api.request({ url: `${base().replace(/\/$/, '')}/api/regional-guides/${route}`, timeout: 15000, ...options, ...callbacks });
    return {
        areas: (region, callbacks) => send(`areas?${query(region)}`, {}, callbacks),
        lookup: (region, callbacks) => send(`lookup?${query(region)}`, {}, callbacks),
        formContract: (context, callbacks) => send(`form-contract?${query(context, { source_id: context.source_id, version: context.version, template_id: context.template_id, kind: context.kind })}`, {}, callbacks),
        generate: (payload, callbacks) => send('generate', { method: 'POST', data: payload, responseType: 'arraybuffer', timeout: 60000 }, callbacks),
        downloadTemplate: (context, callbacks) => send(`templates/${encodeURIComponent(context.template_id || '')}?${query(context, { source_id: context.source_id, version: context.version })}`, { responseType: 'arraybuffer', timeout: 60000 }, callbacks),
    };
}
function header(headers, name) {
    const key = Object.keys(headers || {}).find(k => k.toLowerCase() === name.toLowerCase());
    return key === undefined ? '' : String(headers?.[key]);
}
// Check a complete ZIP directory and the three mandatory Word package parts.
// This is structural verification, not a claim to verify decompressed XML or CRC.
function isWordZip(buffer) {
    try {
        if (!(buffer instanceof ArrayBuffer))
            return false;
        const bytes = new Uint8Array(buffer), v = new DataView(buffer);
        if (bytes.length < 22 || v.getUint32(0, true) !== 0x04034b50)
            return false;
        let end = -1;
        for (let i = bytes.length - 22; i >= Math.max(0, bytes.length - 65557); i--) {
            if (v.getUint32(i, true) === 0x06054b50 && i + 22 + v.getUint16(i + 20, true) === bytes.length) {
                end = i;
                break;
            }
        }
        if (end < 0 || v.getUint16(end + 4, true) || v.getUint16(end + 6, true))
            return false;
        const count = v.getUint16(end + 10, true), size = v.getUint32(end + 12, true), offset = v.getUint32(end + 16, true);
        if (!count || count !== v.getUint16(end + 8, true) || offset + size !== end)
            return false;
        const names = new Set();
        let cursor = offset;
        for (let i = 0; i < count; i++) {
            if (cursor + 46 > end || v.getUint32(cursor, true) !== 0x02014b50 || (v.getUint16(cursor + 8, true) & 1))
                return false;
            const n = v.getUint16(cursor + 28, true), e = v.getUint16(cursor + 30, true), c = v.getUint16(cursor + 32, true), local = v.getUint32(cursor + 42, true);
            if (cursor + 46 + n + e + c > end || local + 30 > offset || v.getUint32(local, true) !== 0x04034b50)
                return false;
            const ln = v.getUint16(local + 26, true), le = v.getUint16(local + 28, true), packed = v.getUint32(cursor + 20, true);
            if (ln !== n || local + 30 + ln + le + packed > offset)
                return false;
            let name = '';
            for (let j = 0; j < n; j++) {
                if (bytes[local + 30 + j] !== bytes[cursor + 46 + j])
                    return false;
                name += String.fromCharCode(bytes[cursor + 46 + j]);
            }
            if (names.has(name) || name.includes('..') || name[0] === '/')
                return false;
            names.add(name);
            cursor += 46 + n + e + c;
        }
        return cursor === end && ['[Content_Types].xml', '_rels/.rels', 'word/document.xml'].every(n => names.has(n));
    }
    catch (_) {
        return false;
    }
}
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
