// Generated from pages/regional/index.ts. Do not edit.
// source-sha256: e01a820860a84bc30102e238e63aeac49667e8c92573c166b47aa7aaa8861850
"use strict";
const shared = require("../../utils/generated/regional-contracts");
const files = require("../../utils/regionalTransport");
const provinces = require("../../data/provinces");
const copy = (value) => {
    if (value === null || typeof value !== 'object')
        return value;
    const out = Array.isArray(value) ? new Array(value.length) : {};
    Reflect.ownKeys(value).forEach(key => {
        if (key !== 'length')
            Object.defineProperty(out, key, { value: copy(Reflect.get(value, key)), enumerable: true, configurable: true, writable: true });
    });
    return out;
};
const at = (value, path) => path.reduce((v, k) => v !== null && typeof v === 'object' ? Reflect.get(v, k) : undefined, value);
const identity = (c) => JSON.stringify([c.schema_version, c.contract_id, c.context.province, c.context.city, c.context.district, c.context.source_id, c.context.version, c.context.template_id, c.context.kind]);
const display = (value) => typeof value === 'string' ? value : value == null ? '' : typeof value === 'object' ? JSON.stringify(value) : String(value);
const guideText = (value) => {
    if (Array.isArray(value))
        return value.map(guideText).join('\n');
    if (shared.isPlainRecord(value)) {
        if (typeof value.capture_text === 'string')
            return guideText(value.capture_text);
        if (value.raw_value !== undefined)
            return guideText(value.raw_value);
        return Object.keys(value).filter(k => value[k] !== null && value[k] !== '' && !['source_file', 'source_url'].includes(k)).map(k => `${k}：${guideText(value[k])}`).join('\n');
    }
    return display(value).replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, '').replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, '').replace(/<\/(?:p|div|li)>|<br\s*\/?\s*>/gi, '\n').replace(/<[^>]*>/g, '').replace(/&nbsp;/g, ' ').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&amp;/g, '&');
};
const page = {
    data: { provinces: provinces.map(p => p.name), provinceIndex: 0, cities: [], districts: [], cityIndex: -1, districtIndex: -1, guide: null, contract: null, fields: [], sections: [], channelText: '', warnings: [], materials: [], blanks: [], kinds: [], kindIndex: 0, controls: [], errors: [], formValid: false, available: false, busy: false, notice: '请选择办理区县，核对本区自己的指南和表格。', error: '', result: '', storageNotice: '', draftBlocked: false },
    onLoad(options) {
        this._epoch = 0;
        this._jobs = new Set();
        this._sequence = 0;
        this.transport = files.createRegionalTransport(wx, () => getApp().globalData.apiBase);
        const index = Math.max(0, provinces.findIndex(p => p.slug === options.province));
        this.setData({ provinceIndex: index });
        this._region = { province: provinces[index].slug };
        this.loadCities();
    },
    onUnload() { this.saveDraft(); this.invalidate(); },
    onHide() { this.saveDraft(); },
    invalidate() {
        this._epoch++;
        this._jobs.forEach(job => {
            job.done = true;
            if (job.task && job.task.abort)
                job.task.abort();
        });
        this._jobs.clear();
        this._guide = null;
        this._contract = null;
        this._form = null;
        this.draftKey = '';
        this._storedFingerprint = null;
        this.setData({ guide: null, contract: null, fields: [], sections: [], channelText: '', warnings: [], materials: [], blanks: [], controls: [], kinds: [], kindIndex: 0, available: false, formValid: false, busy: false, errors: [], error: '', result: '', draftBlocked: false, storageNotice: '' });
    },
    current(epoch, contract) { return this._epoch === epoch && (!contract || this._contract === contract); },
    request(method, payload, success) {
        const epoch = this._epoch, job = { done: false };
        this._jobs.add(job);
        const finish = (callback) => (value) => {
            if (job.done)
                return;
            job.done = true;
            this._jobs.delete(job);
            if (this.current(epoch))
                callback(value);
        };
        job.task = this.transport[method](payload, {
            success: finish(res => {
                if (res.statusCode !== 200) {
                    if (res.statusCode === 409) {
                        this._contract = null;
                        this.setData({ contract: null, available: false, draftBlocked: true, notice: '指南或表格版本已变更，请重新选择地区并核对。' });
                    }
                    this.setData({ busy: false, error: res.data instanceof ArrayBuffer ? files.decodeError(res.data) : shared.parseApiError(res.data, '请求失败，请重新核对') });
                    return;
                }
                try {
                    success(res);
                }
                catch (_) {
                    this.setData({ busy: false, error: '返回的地区、来源、版本或表格不匹配，请重新核对。' });
                }
            }),
            fail: finish(() => this.setData({ busy: false, error: '网络请求未完成，请重试并核对办理地区。' })),
        });
    },
    onProvinceChange(e) {
        this.saveDraft();
        this.invalidate();
        const i = Number(e.detail.value);
        if (!provinces[i])
            return;
        this._region = { province: provinces[i].slug };
        this.setData({ provinceIndex: i, cities: [], districts: [], cityIndex: -1, districtIndex: -1 });
        this.loadCities();
    },
    loadCities() {
        this.request('areas', this._region, res => {
            if (!shared.isPlainRecord(res.data) || !Array.isArray(res.data.items))
                throw new Error('areas');
            this._cities = [...new Set(res.data.items.filter((r) => shared.isPlainRecord(r) && r.province === this._region.province && typeof r.city === 'string').map(r => r.city))];
            this.setData({ cities: this._cities, notice: this._cities.length ? '请选择市和办理区县。' : '本省区县目录待核验。' });
        });
    },
    onCityChange(e) {
        const city = (this._cities || [])[Number(e.detail.value)];
        if (!city)
            return;
        this.saveDraft();
        this.invalidate();
        this._region = { province: this._region.province, city };
        this.setData({ cityIndex: Number(e.detail.value), districtIndex: -1, districts: [] });
        this.request('areas', this._region, res => {
            if (!shared.isPlainRecord(res.data) || !Array.isArray(res.data.items))
                throw new Error('areas');
            this._districts = res.data.items.filter((r) => shared.isPlainRecord(r) && r.province === this._region.province && r.city === city && typeof r.district === 'string' && !!r.district);
            this.setData({ districts: this._districts.map(r => r.district), notice: this._districts.length ? '请选择办理区县。' : '本市区县目录待核验。' });
        });
    },
    onDistrictChange(e) {
        const row = (this._districts || [])[Number(e.detail.value)];
        if (!row)
            return;
        this.saveDraft();
        this.invalidate();
        this._region = { province: row.province, city: row.city, district: row.district };
        this.setData({ districtIndex: Number(e.detail.value), notice: '正在核对本区指南…' });
        this.request('lookup', this._region, res => {
            const g = shared.assertRegionalGuide(res.data, { province: this._region.province, city: this._region.city || '', district: this._region.district || '' });
            this._guide = g;
            if (!g.source_id || g.verification_status === 'unverified') {
                this.setData({ guide: g, notice: '该地区办事指南尚未核验，暂不能填写生成。' });
                return;
            }
            this._kinds = [];
            g.templates.forEach(t => {
                if (t.can_generate === true && Array.isArray(t.document_types))
                    t.document_types.forEach(kind => {
                        if (kind === 'application' || kind === 'evidence')
                            this._kinds.push({ t, kind });
                    });
            });
            const fields = Object.keys(g.fields || {}).map(key => ({ label: key, value: display(shared.isPlainRecord(g.fields[key]) && g.fields[key].raw_value !== undefined ? g.fields[key].raw_value : g.fields[key]) }));
            const blanks = g.templates.map((t, index) => ({ ...t, index })).filter(t => t.official_kind === 'blank' && t.download_status === 'downloaded' && t.file && /^[a-f0-9]{64}$/i.test(typeof t.sha256 === 'string' ? t.sha256 : ''));
            const sections = Object.keys(g.sections).map(label => ({ label, value: guideText(g.sections[label]) }));
            const channelText = guideText(g.channel.raw_value) + (g.channel.online_status === 'auth_required' ? '\n网上入口需要登录或验证码；本页不会代办提交。' : '');
            this.setData({ guide: g, fields, sections, channelText, materials: g.materials, warnings: Array.isArray(g.warnings) ? g.warnings : [], blanks, kinds: this._kinds.map(k => `${k.kind === 'application' ? '申请书' : '证据清单'} · ${k.t.original_name || k.t.id}`), notice: this._kinds.length ? '请核对本区指南、材料和表格来源。' : '本区表格填写尚待核验，可查看已核验的原件。' });
            if (this._kinds.length)
                this.loadContract(0);
        });
    },
    onKindChange(e) { this.saveDraft(); this.loadContract(Number(e.detail.value)); },
    loadContract(index) {
        const option = (this._kinds || [])[index], g = this._guide;
        if (!g || !option)
            return;
        // Invalidate pending work even when a user returns to the same kind.
        this._epoch++;
        this._jobs.forEach(job => {
            job.done = true;
            if (job.task && job.task.abort)
                job.task.abort();
        });
        this._jobs.clear();
        this._contract = null;
        this._form = null;
        this.draftKey = '';
        this._storedFingerprint = null;
        this.setData({ contract: null, available: false, controls: [], errors: [], formValid: false, kindIndex: index, busy: false, result: '', error: '', storageNotice: '', draftBlocked: false });
        const expected = { ...this._region, source_id: g.source_id, version: g.version, template_id: option.t.id, kind: option.kind };
        if (g.region_code)
            expected.region_code = g.region_code;
        if (option.t.adapter)
            expected.adapter = option.t.adapter;
        this.request('formContract', expected, res => {
            const c = shared.assertFormContract(res.data, expected);
            this._contract = c;
            this._form = shared.createEmptyForm(c);
            this.draftKey = 'regional-draft:' + identity(c);
            try {
                const draft = wx.getStorageSync(this.draftKey);
                if (draft) {
                    if (!shared.isPlainRecord(draft)) {
                        this.setData({ draftBlocked: true, notice: '草稿结构不匹配，请清空后重新核对。' });
                        this.setData({ contract: c, available: true });
                        this.refresh();
                        return;
                    }
                    if (Object.keys(draft).some(key => !['schema_version', 'contract_id', 'context', 'form'].includes(key)) || draft.schema_version !== c.schema_version || draft.contract_id !== c.contract_id || JSON.stringify(draft.context) !== JSON.stringify(c.context) || !draft.form || typeof draft.form !== 'object')
                        this.setData({ draftBlocked: true, notice: '草稿版本、来源或结构不匹配，请清空后重新核对。' });
                    else {
                        this._form = copy(draft.form);
                        this._storedFingerprint = JSON.stringify(this._form);
                    }
                }
            }
            catch (_) {
                this.setData({ storageNotice: '草稿读取失败，仍可填写；请自行保留重要内容。' });
            }
            this.setData({ contract: c, available: true });
            this.refresh();
        });
    },
    refresh() {
        const c = this._contract;
        if (!c)
            return;
        const validation = shared.validateForm(c, this._form), controls = [];
        const walk = (fields, base) => fields.forEach(f => {
            const path = base.concat(f.key), value = at(this._form, path), encoded = JSON.stringify(path);
            if (f.type === 'object_list' || f.type === 'text_list') {
                const list = Array.isArray(value) ? value : [];
                controls.push({ viewType: 'list', path: encoded, label: f.label, count: list.length, maxItems: f.maxItems, canAdd: Array.isArray(value) && (!f.maxItems || list.length < f.maxItems) });
                list.forEach((item, index) => {
                    if (f.type === 'object_list') {
                        controls.push({ viewType: 'row', path: encoded, label: `${f.label} ${index + 1}`, index, canRemove: list.length > 1 });
                        walk(f.fields || [], path.concat(index));
                    }
                    else
                        controls.push({ viewType: 'list-item', path: JSON.stringify(path.concat(index)), parentPath: encoded, label: `${f.label} ${index + 1}`, value: display(item), count: Array.from(display(item)).length, maxLength: f.maxLength, index, canRemove: list.length > 1 });
                });
            }
            else
                controls.push({ viewType: 'scalar', path: encoded, label: f.label, value: display(value), count: Array.from(display(value)).length, maxLength: f.maxLength, format: f.format, choices: f.choices || [], integer: f.integer, min: f.min, max: f.max });
        });
        walk(c.fields, []);
        controls.forEach((control, index) => { control.id = 'regional-field-' + index; });
        this.setData({ controls, errors: validation.errors, formValid: validation.valid && !this.data.draftBlocked });
    },
    path(e) {
        try {
            const p = JSON.parse(String(e.currentTarget.dataset.path));
            return Array.isArray(p) && p.every(k => typeof k === 'string' || Number.isInteger(k)) ? p : null;
        }
        catch (_) {
            return null;
        }
    },
    spec(path) {
        if (!this._contract)
            return null;
        let fields = this._contract.fields, spec;
        for (let i = 0; i < path.length; i++) {
            if (typeof path[i] === 'number')
                continue;
            spec = fields.find(f => f.key === path[i]);
            if (!spec)
                return null;
            if (spec.type === 'object_list')
                fields = spec.fields || [];
        }
        return spec || null;
    },
    onInput(e) {
        if (!this._contract || this.data.draftBlocked)
            return;
        const path = this.path(e);
        if (!path || !path.length || !this.spec(path))
            return;
        const parent = at(this._form, path.slice(0, -1));
        if (!parent || typeof parent !== 'object')
            return;
        Object.defineProperty(parent, path[path.length - 1], { value: e.detail.value, enumerable: true, configurable: true, writable: true });
        this.refresh();
    },
    onChoice(e) {
        const path = this.path(e), spec = path && this.spec(path), value = spec && spec.choices && spec.choices[Number(e.detail.value)];
        if (typeof value === 'string')
            this.onInput({ ...e, detail: { value } });
    },
    addItem(e) {
        if (!this._contract || this.data.draftBlocked)
            return;
        const path = this.path(e), spec = path && this.spec(path), list = path && at(this._form, path);
        if (!spec || !Array.isArray(list) || (spec.type !== 'text_list' && spec.type !== 'object_list') || (spec.maxItems && list.length >= spec.maxItems))
            return;
        const empty = shared.createEmptyForm(this._contract), defaultPath = path.map(k => typeof k === 'number' ? 0 : k), defaults = at(empty, defaultPath);
        if (!Array.isArray(defaults) || !defaults.length)
            return;
        list.push(copy(defaults[0]));
        this.refresh();
    },
    removeItem(e) {
        if (!this._contract || this.data.draftBlocked)
            return;
        const path = this.path(e), list = path && at(this._form, path), index = Number(e.currentTarget.dataset.index);
        if (!Array.isArray(list) || list.length <= 1 || !Number.isInteger(index) || index < 0 || index >= list.length)
            return;
        list.splice(index, 1);
        this.refresh();
    },
    saveDraft() {
        if (!this._contract || !this._form || !this.draftKey || this.data.draftBlocked)
            return;
        try {
            // JSON storage must never erase sparse slots or extra array properties.
            const serializable = (value) => {
                if (!value || typeof value !== 'object')
                    return typeof value !== 'undefined' && typeof value !== 'function' && typeof value !== 'symbol';
                if (Array.isArray(value) && (Object.keys(value).length !== value.length || !Array.from({ length: value.length }, (_, i) => Object.prototype.hasOwnProperty.call(value, i)).every(Boolean)))
                    return false;
                return Reflect.ownKeys(value).filter(k => k !== 'length').every(k => typeof k === 'string' && serializable(Reflect.get(value, k)));
            };
            if (!serializable(this._form))
                throw new Error('lossy storage');
            const fingerprint = JSON.stringify(this._form);
            if (fingerprint === this._storedFingerprint)
                return;
            wx.setStorageSync(this.draftKey, { schema_version: this._contract.schema_version, contract_id: this._contract.contract_id, context: copy(this._contract.context), form: copy(this._form) });
            this._storedFingerprint = fingerprint;
        }
        catch (_) {
            this.setData({ storageNotice: '草稿保存失败，仍可生成；请自行保留重要内容。' });
        }
    },
    confirm(content, action) {
        const epoch = this._epoch, c = this._contract;
        let settled = false;
        wx.showModal({ title: '核对办理地区与资料', content, success: res => {
                if (settled)
                    return;
                settled = true;
                if (res.confirm && this.current(epoch, c))
                    action();
            } });
    },
    clear() {
        if (!this._contract)
            return;
        this.confirm('清空本区这份表格的草稿？其他区县草稿不受影响。', () => {
            this._form = shared.createEmptyForm(this._contract);
            this._storedFingerprint = null;
            this.setData({ draftBlocked: false, result: '', error: '', notice: '已清空，请重新核对本区资料。' });
            try {
                wx.removeStorageSync(this.draftKey);
            }
            catch (_) {
                this.setData({ storageNotice: '旧草稿清理失败，请勿依赖自动保存。' });
            }
            this.refresh();
        });
    },
    example() {
        if (!this._contract)
            return;
        this.confirm('用虚构示例替换当前内容？示例不能直接提交，日期、份数和意愿仍需本人核对。', () => { this._form = shared.createExampleForm(this._contract); this.setData({ draftBlocked: false, result: '', error: '' }); this.refresh(); });
    },
    generate() {
        if (!this._contract || this.data.busy || this.data.draftBlocked)
            return;
        this.refresh();
        if (!this.data.formValid)
            return;
        let payload;
        try {
            payload = shared.buildGenerateRequest(this._contract, this._form);
        }
        catch (_) {
            this.setData({ error: '请修正表格校验提示后再生成。' });
            return;
        }
        const c = this._contract;
        this.confirm(`${c.context.city}${c.context.district}：请核对来源和内容。文件须自行核对，打印后由本人手写签名。`, () => {
            if (this.data.busy)
                return;
            this.saveDraft();
            this.setData({ busy: true, error: '', result: '' });
            this.request('generate', payload, res => this.acceptFile(res, c.context, null, 'docx', c.contract_id));
        });
    },
    downloadBlank(e) {
        const t = this._guide && this._guide.templates[Number(e.currentTarget.dataset.index)], g = this._guide;
        if (!g || !t || t.official_kind !== 'blank' || t.download_status !== 'downloaded' || !t.file || !/^[a-f0-9]{64}$/i.test(typeof t.sha256 === 'string' ? t.sha256 : '') || this.data.busy)
            return;
        const context = { ...this._region, source_id: g.source_id, version: g.version, template_id: t.id, region_code: g.region_code, kind: 'blank' };
        const type = String(t.file_type || (t.original_name || '').split('.').pop()).toLowerCase();
        if (!['docx', 'doc', 'pdf'].includes(type)) {
            this.setData({ error: '该原件格式暂不支持预览，请查看官方来源。' });
            return;
        }
        this.confirm(`下载${g.city}${g.district}自己的公开空白表格，请核对官方来源。`, () => {
            if (this.data.busy)
                return;
            this.setData({ busy: true, error: '', result: '' });
            this.request('downloadTemplate', context, res => this.acceptFile(res, context, typeof t.sha256 === 'string' ? t.sha256 : null, type));
        });
    },
    acceptFile(res, context, sha, type, contractId) {
        if (type !== 'docx' && type !== 'doc' && type !== 'pdf')
            throw new Error('preview type');
        const source = files.header(res.header, 'X-Guide-Source-ID'), version = files.header(res.header, 'X-Guide-Version');
        if (source !== context.source_id || version !== String(context.version) || (contractId && files.header(res.header, 'X-Form-Contract-ID') !== contractId) || (sha && files.header(res.header, 'X-Template-SHA256').toLowerCase() !== sha.toLowerCase()))
            throw new Error('source headers');
        if (!(res.data instanceof ArrayBuffer))
            throw new Error('binary response');
        const binary = res.data;
        const b = new Uint8Array(binary);
        const valid = type === 'docx' ? files.isWordZip(binary) : type === 'pdf' ? b.length > 5 && String.fromCharCode(...b.slice(0, 5)) === '%PDF-' : b.length > 8 && [208, 207, 17, 224, 161, 177, 26, 225].every((v, i) => b[i] === v);
        if (!valid) {
            this.setData({ busy: false, error: '返回文件格式不完整，未保存。请重试。' });
            return;
        }
        const epoch = this._epoch, c = this._contract, path = `${wx.env.USER_DATA_PATH}/regional-${String(context.region_code || 'local').replace(/[^a-zA-Z0-9_-]/g, '')}-${++this._sequence}.${type}`;
        let written = false, opened = false;
        wx.getFileSystemManager().writeFile({ filePath: path, data: binary, success: () => {
                if (written)
                    return;
                written = true;
                if (!this.current(epoch, c))
                    return;
                wx.openDocument({ filePath: path, fileType: type, showMenu: true, success: () => {
                        if (opened)
                            return;
                        opened = true;
                        if (this.current(epoch, c))
                            this.setData({ busy: false, result: `${context.city}${context.district}文件已打开，请本人核对并手写签名。` });
                    }, fail: () => {
                        if (opened)
                            return;
                        opened = true;
                        if (this.current(epoch, c))
                            this.setData({ busy: false, error: '文件已保存，预览未完成，请重试。' });
                    } });
            }, fail: () => {
                if (written)
                    return;
                written = true;
                if (this.current(epoch, c))
                    this.setData({ busy: false, error: '文件保存失败，请检查设备空间后重试。' });
            } });
    },
    copySource() {
        if (this._guide && /^https?:\/\//.test(this._guide.source_url || ''))
            wx.setClipboardData({ data: this._guide.source_url || '' });
    },
};
Page(page);
