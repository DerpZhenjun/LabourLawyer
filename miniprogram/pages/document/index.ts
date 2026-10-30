import {isRecord} from '../../utils/generated/document-contracts';
import type { PageSpec, MiniEvent } from '../../types/runtime';
import type { Province, DocumentKind, FormConfig, LegacyForm, FormLimits, DocumentFieldDefinition } from '../../../packages/client-contracts/src/documents';
type Data = {
    province: Province | null;
    kind: DocumentKind | '';
    title: string;
    fields: ({
        key: string;
    } & Partial<DocumentFieldDefinition>)[];
    itemFields: ({
        key: string;
    } & Partial<DocumentFieldDefinition>)[];
    form: LegacyForm & {requests:unknown[];evidenceList:Record<string,unknown>[]};
    busy: boolean;
    available: boolean;
    error: string;
    limits: Partial<FormLimits>;
};
type Methods = {
    onLoad(options: Record<string, string | undefined>): void;
    setup(province: Province, kind: DocumentKind, currentForm?: LegacyForm): void;
    input(event: MiniEvent): void;
    pick(event: MiniEvent): void;
    addRequest(): void;
    removeRequest(event: MiniEvent): void;
    addEvidence(): void;
    removeEvidence(event: MiniEvent): void;
    saveDraft(): void;
    onHide(): void;
    onUnload(): void;
    clear(): void;
    example(): void;
    copySource(): void;
    generate(): void;
    download(payload: Record<string, unknown>): void;
};
type State = {
    draftKey: string;
    config: FormConfig;
};
import * as docs from '../../utils/documents';
const page: PageSpec<Data, Methods, State> = {
    data: { province: null, kind: '', title: '', fields: [], itemFields: [], form: { requests: [], evidenceList: [] }, busy: false, available: false, error: '', limits: {} },
    onLoad(options) {
        const kind = options.kind;
        const province = docs.findProvince(options.slug);
        if (!province || (kind !== 'application' && kind !== 'evidence')) {
            this.setData({ error: '省份或文书类型无效，请返回首页选择' });
            return;
        }
        this.draftKey = `labourlawyer-${province.slug}-${kind}-v1`;
        this.setup(province, kind);
        docs.loadCatalog(items => {
            const live = docs.mergeCatalog(items).find(p => p.slug === province.slug);
            if (!live) {
                this.setData({ available: false, error: '服务端没有该省份的模板' });
                return;
            }
            this.setup({ ...province, ...live }, kind, this.data.form);
        }, () => this.setData({ error: '暂未连接后端，当前显示随项目保存的模板配置；生成前请启动服务' }));
    },
    setup(province, kind, currentForm) {
        this.config = docs.formConfig(province, kind);
        const available = !!province.documents[kind] && this.config.fields.length > 0;
        let saved:unknown = currentForm;
        if (!saved) {
            try {
                saved = wx.getStorageSync(this.draftKey);
            }
            catch { }
        }
        const form = { ...docs.blankForm(this.config, kind), ...(isRecord(saved) ? saved : {}) };
        if (!Array.isArray(form.requests))
            form.requests = [''];
        if (!Array.isArray(form.evidenceList) || !form.evidenceList.length || !form.evidenceList.every(isRecord))
            form.evidenceList = docs.blankForm(this.config, 'evidence').evidenceList;
        const keys = this.config.fields.filter(k => kind !== 'evidence' || !docs.evidenceKeys.includes(k));
        const title = kind === 'application' ? '劳动仲裁申请书' : '证据清单';
        this.setData({ province, kind, title, available, form:form as LegacyForm & {requests:unknown[];evidenceList:Record<string,unknown>[]}, fields: docs.fieldViews(keys, this.config.definitions), itemFields: docs.fieldViews(this.config.fields.filter(k => docs.evidenceKeys.includes(k)), this.config.definitions), limits: this.config.limits, error: available ? '' : '本省尚无已验证的对应官方 Word 模板' });
        wx.setNavigationBarTitle({ title: province.name + title });
    },
    input(event) {
        const { key, index } = event.currentTarget.dataset;
        const value = event.detail.value;
        let path;
        if (index !== undefined)
            path = key === 'requests' ? `form.requests[${index}]` : `form.evidenceList[${index}].${key}`;
        else
            path = `form.${key}`;
        this.setData({ [path]: value });
    },
    pick(event) {
        const { key, index } = event.currentTarget.dataset;
        const value = this.config.definitions[String(key)]?.options?.[Number(event.detail.value)];
        this.setData({ [index !== undefined ? `form.evidenceList[${index}].${key}` : `form.${key}`]: value });
    },
    addRequest() { if (this.data.form.requests.length < (this.data.limits.maxRequests ?? 0))
        this.setData({ 'form.requests': [...this.data.form.requests, ''] }); },
    removeRequest(event) { const rows = this.data.form.requests.filter((_, i) => i !== Number(event.currentTarget.dataset.index)); this.setData({ 'form.requests': rows.length ? rows : [''] }); },
    addEvidence() { if (this.data.form.evidenceList.length < (this.data.limits.maxEvidence ?? 0))
        this.setData({ 'form.evidenceList': [...this.data.form.evidenceList, docs.blankForm(this.config, 'evidence').evidenceList[0]!] }); },
    removeEvidence(event) { const rows = this.data.form.evidenceList.filter((_, i) => i !== Number(event.currentTarget.dataset.index)); this.setData({ 'form.evidenceList': rows.length ? rows : docs.blankForm(this.config, 'evidence').evidenceList }); },
    saveDraft() { if (this.draftKey && this.data.available)
        wx.setStorageSync(this.draftKey, this.data.form); },
    onHide() { this.saveDraft(); },
    onUnload() { this.saveDraft(); },
    clear() { wx.showModal({ title: '清空本省当前文书草稿？', content: '清空后可重新填写，不影响其他省份的草稿。', success: r => { if (r.confirm) {
            this.setData({ form: {requests:[''],evidenceList:[{}],...docs.blankForm(this.config, this.data.kind as DocumentKind)} });
            wx.removeStorageSync(this.draftKey);
        } } }); },
    example() {
        wx.showModal({ title: '加载虚构示例？', content: '会替换当前内容。示例用于试用，请在正式提交前全部改为真实信息。', success: r => {
                if (r.confirm)
                    this.setData({ form: {requests:[''],evidenceList:[{}], ...docs.blankForm(this.config, this.data.kind as DocumentKind), ...JSON.parse(JSON.stringify(this.data.province?.[this.data.kind === 'application' ? 'applicationExample' : 'evidenceExample'])) } });
            } });
    },
    copySource() { wx.setClipboardData({ data: this.data.province?.source_url || '' }); },
    generate() {
        if (this.data.busy || !this.data.available)
            return;
        let payload;
        try {
            payload = docs.payloadFor(this.data.form, this.config, this.data.kind as DocumentKind);
        }
        catch (error) {
            this.setData({ error: error instanceof Error ? error.message : '请核对填写内容' });
            return;
        }
        wx.showModal({ title: '生成官方格式 Word 文书', content: '请确认模板适用地区。未填写的信息保留空白，签名栏留给本人手签。', success: result => { if (result.confirm)
                this.download(payload); } });
    },
    download(payload) {
        this.saveDraft();
        this.setData({ busy: true, error: '' });
        wx.request<Record<string, unknown> | string | ArrayBuffer>({ url: `${docs.apiBase()}/api/province-documents/${this.data.province!.slug}/${this.data.kind}/generate`, method: 'POST', data: payload, header: { 'content-type': 'application/json' }, responseType: 'arraybuffer', timeout: 60000,
            success: res => {
                if (res.statusCode !== 200 || !docs.isDocx(res.data)) {
                    this.setData({ busy: false, error: docs.errorMessage(res.data) });
                    return;
                }
                const filePath = `${wx.env.USER_DATA_PATH}/${this.data.province!.slug}-${this.data.kind}-${Date.now()}.docx`;
                wx.getFileSystemManager().writeFile({ filePath, data: res.data,
                    success: () => wx.openDocument({ filePath, fileType: 'docx', showMenu: true, success: () => this.setData({ busy: false }), fail: () => this.setData({ busy: false, error: 'Word 已保存，当前设备无法预览；请在文件管理中打开' }) }),
                    fail: () => this.setData({ busy: false, error: '保存失败，请检查设备空间后重试' }),
                });
            },
            fail: error => this.setData({ busy: false, error: `生成请求失败：${error.errMsg || '请检查服务地址和网络'}` }),
        });
    },
};
Page(page);
