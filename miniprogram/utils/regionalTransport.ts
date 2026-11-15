import * as shared from './generated/regional-contracts';
import type { FormContext, RegionalGenerateRequest } from '../../packages/regional-contracts/src/index';
export type RequestInput = Omit<Partial<FormContext>, 'kind'> & {
    province: string;
    kind?: string;
    data?: unknown;
    contract_id?: string;
};
export type Callbacks = {
    success: (res: WechatMiniprogram.RequestSuccessCallbackResult<Record<string, unknown> | string | ArrayBuffer>) => void;
    fail: (error: WechatMiniprogram.GeneralCallbackResult) => void;
};
export type Transport = ReturnType<typeof createRegionalTransport>;
function createRegionalTransport(api: Pick<WechatMiniprogram.Wx, 'request'>, base: () => string) {
    const query = (region: RequestInput, extra?: Record<string, unknown>) => {
        const scope = shared.regionQuery({ province: region.province, city: region.city || '', district: region.district || '', case_scope: region.case_scope });
        const suffix = Object.keys(extra || {}).filter(k => extra![k] !== undefined).map(k => `${encodeURIComponent(k)}=${encodeURIComponent(String(extra![k]))}`).join('&');
        return scope + (suffix ? (scope ? '&' : '') + suffix : '');
    };
    const send = (route: string, options: Partial<WechatMiniprogram.RequestOption<Record<string, unknown> | string | ArrayBuffer>>, callbacks: Callbacks) => api.request<Record<string, unknown> | string | ArrayBuffer>({ url: `${base().replace(/\/$/, '')}/api/regional-guides/${route}`, timeout: 15000, ...options, ...callbacks });
    return {
        areas: (region: RequestInput, callbacks: Callbacks) => send(`areas?${query(region,{xlsx:true})}`, {}, callbacks),
        lookup: (region: RequestInput, callbacks: Callbacks) => send(`lookup?${query(region,{xlsx:true})}`, {}, callbacks),
        formContract: (context: RequestInput, callbacks: Callbacks) => send(`form-contract?${query(context, { source_id: context.source_id, version: context.version, template_id: context.template_id, kind: context.kind, xlsx: true })}`, {}, callbacks),
        generate: (payload: RequestInput, callbacks: Callbacks) => send('generate?xlsx=true', { method: 'POST', data: payload, responseType: 'arraybuffer', timeout: 60000 }, callbacks),
        downloadTemplate: (context: RequestInput, callbacks: Callbacks) => send(`templates/${encodeURIComponent(context.template_id || '')}?${query(context, { source_id: context.source_id, version: context.version })}`, { responseType: 'arraybuffer', timeout: 60000 }, callbacks),
    };
}
function header(headers: Record<string, unknown> | undefined, name: string) {
    const key = Object.keys(headers || {}).find(k => k.toLowerCase() === name.toLowerCase());
    return key === undefined ? '' : String(headers?.[key]);
}
const isWordZip = (buffer: unknown): buffer is ArrayBuffer => shared.isOfficeZip(buffer, 'docx');
function decodeError(buffer: ArrayBuffer) {
    try {
        let encoded = '';
        new Uint8Array(buffer).forEach(b => { encoded += '%' + ('0' + b.toString(16)).slice(-2); });
        return shared.parseApiError(JSON.parse(decodeURIComponent(encoded)), '请求失败，请重新核对本区指南');
    }
    catch (_) {
        return '请求失败，请重新核对本区指南';
    }
}
export { createRegionalTransport, header, isWordZip, decodeError };
