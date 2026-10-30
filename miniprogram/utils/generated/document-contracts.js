// Generated from packages/client-contracts/src/documents.ts. Do not edit.
// source-sha256: 8deac83b234677c8a7c53c3e99ad4207ca528ae2ccfc3685237b1bf0ba084ceb
"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.isRecord = void 0;
exports.isCatalogProvince = isCatalogProvince;
exports.isExperience = isExperience;
const isRecord = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);
exports.isRecord = isRecord;
function isCatalogProvince(v) {
    if (!(0, exports.isRecord)(v) || !['slug', 'name', 'source_url'].every(k => typeof v[k] === 'string') || !(0, exports.isRecord)(v.documents))
        return false;
    if (v.shortName !== undefined && typeof v.shortName !== 'string')
        return false;
    const documents = v.documents;
    if (!['application', 'evidence'].every(k => documents[k] === undefined || documents[k] === null || typeof documents[k] === 'string'))
        return false;
    if (v.forms !== undefined) {
        const forms = v.forms;
        if (!(0, exports.isRecord)(forms) || !Array.isArray(forms.applicationFields) || !forms.applicationFields.every(k => typeof k === 'string') || !Array.isArray(forms.evidenceFields) || !forms.evidenceFields.every(k => typeof k === 'string') || !(0, exports.isRecord)(forms.fieldDefinitions) || !Object.values(forms.fieldDefinitions).every(isFieldDefinition) || !(0, exports.isRecord)(forms.limits))
            return false;
        const limits = forms.limits;
        if (!['maxRequests', 'requestLength', 'factsLength', 'maxEvidence'].every(k => typeof limits[k] === 'number' && Number.isSafeInteger(limits[k]) && Number(limits[k]) > 0))
            return false;
    }
    return true;
}
function isFieldDefinition(v) { return (0, exports.isRecord)(v) && typeof v.label === 'string' && typeof v.type === 'string' && typeof v.maxLength === 'number' && Number.isSafeInteger(v.maxLength) && v.maxLength > 0 && (v.options === undefined || (Array.isArray(v.options) && v.options.every(s => typeof s === 'string'))); }
function isExperience(v) {
    if (!(0, exports.isRecord)(v) || !Array.isArray(v.steps) || !v.steps.every(exports.isRecord) || !Array.isArray(v.materials) || !Array.isArray(v.notes))
        return false;
    if (v.theme !== undefined && (!(0, exports.isRecord)(v.theme) || typeof v.theme.accent !== 'string'))
        return false;
    if (v.templates !== undefined && (!Array.isArray(v.templates) || !v.templates.every(t => (0, exports.isRecord)(t) && ['material_name', 'text', 'kind', 'url'].every(k => t[k] === undefined || typeof t[k] === 'string'))))
        return false;
    return ['service_kind', 'source_url', 'portal_url', 'captured_at'].every(k => v[k] === undefined || typeof v[k] === 'string');
}
