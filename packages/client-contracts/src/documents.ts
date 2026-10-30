/** Portable wire DTOs for the existing provincial document catalog. */
export type DocumentKind = 'application' | 'evidence';
export interface DocumentFieldDefinition {
    label: string;
    type: string;
    maxLength: number;
    options?: string[];
    rows?: number;
    placeholder?: string;
}
export interface FormLimits {
    maxRequests: number;
    requestLength: number;
    factsLength: number;
    maxEvidence: number;
}
export interface FormConfig {
    fields: string[];
    limits: FormLimits;
    definitions: Record<string, DocumentFieldDefinition>;
}
export interface FormSchema {
    applicationExtraFields: Record<string, string[][]>;
    evidenceExtraFields: Record<string, string[][]>;
    applicationSupportedFields: Record<string, string[]>;
    evidenceSupportedFields: Record<string, string[]>;
    limits: Record<string, FormLimits> & {
        default: FormLimits;
    };
    fields: Record<string, DocumentFieldDefinition>;
}
export interface CatalogProvince {
    slug: string;
    name: string;
    shortName?: string;
    source_url: string;
    documents: Partial<Record<DocumentKind, string | null>>;
    forms?: {
        applicationFields: string[];
        evidenceFields: string[];
        limits: FormLimits;
        fieldDefinitions: Record<string, DocumentFieldDefinition>;
    };
    process?: {
        title: string;
        text: string;
    }[];
    materials?: string[];
    applicationExample?: Record<string, unknown>;
    evidenceExample?: Record<string, unknown>;
    [key: string]: unknown;
}
export interface Province extends CatalogProvince {
    shortName: string;
}
export type LegacyForm = Record<string, unknown> & {
    requests?: unknown[];
    evidenceList?: Record<string, unknown>[];
};
export const isRecord = (v: unknown): v is Record<string, unknown> => v !== null && typeof v === 'object' && !Array.isArray(v);
export function isCatalogProvince(v: unknown): v is CatalogProvince {
    if (!isRecord(v) || !['slug', 'name', 'source_url'].every(k => typeof v[k] === 'string') || !isRecord(v.documents))
        return false;
    if (v.shortName !== undefined && typeof v.shortName !== 'string')
        return false;
    const documents = v.documents;
    if (!['application', 'evidence'].every(k => documents[k] === undefined || documents[k] === null || typeof documents[k] === 'string'))
        return false;
    if (v.forms !== undefined) {
        const forms = v.forms;
        if (!isRecord(forms) || !Array.isArray(forms.applicationFields) || !forms.applicationFields.every(k => typeof k === 'string') || !Array.isArray(forms.evidenceFields) || !forms.evidenceFields.every(k => typeof k === 'string') || !isRecord(forms.fieldDefinitions) || !Object.values(forms.fieldDefinitions).every(isFieldDefinition) || !isRecord(forms.limits))
            return false;
        const limits = forms.limits;
        if (!['maxRequests', 'requestLength', 'factsLength', 'maxEvidence'].every(k => typeof limits[k] === 'number' && Number.isSafeInteger(limits[k]) && Number(limits[k]) > 0))
            return false;
    }
    return true;
}
function isFieldDefinition(v: unknown): v is DocumentFieldDefinition { return isRecord(v) && typeof v.label === 'string' && typeof v.type === 'string' && typeof v.maxLength === 'number' && Number.isSafeInteger(v.maxLength) && v.maxLength > 0 && (v.options === undefined || (Array.isArray(v.options) && v.options.every(s => typeof s === 'string'))); }
export interface ExperienceWire {
    steps: Record<string, unknown>[];
    materials: unknown[];
    notes: unknown[];
    theme?: {
        accent: string;
        [key: string]: unknown;
    };
    templates?: {
        material_name?: string;
        text?: string;
        kind?: string;
        url?: string;
    }[];
    service_kind?: string;
    source_url?: string;
    portal_url?: string;
    captured_at?: string;
    [key: string]: unknown;
}
export function isExperience(v: unknown): v is ExperienceWire {
    if (!isRecord(v) || !Array.isArray(v.steps) || !v.steps.every(isRecord) || !Array.isArray(v.materials) || !Array.isArray(v.notes))
        return false;
    if (v.theme !== undefined && (!isRecord(v.theme) || typeof v.theme.accent !== 'string'))
        return false;
    if (v.templates !== undefined && (!Array.isArray(v.templates) || !v.templates.every(t => isRecord(t) && ['material_name', 'text', 'kind', 'url'].every(k => t[k] === undefined || typeof t[k] === 'string'))))
        return false;
    return ['service_kind', 'source_url', 'portal_url', 'captured_at'].every(k => v[k] === undefined || typeof v[k] === 'string');
}
