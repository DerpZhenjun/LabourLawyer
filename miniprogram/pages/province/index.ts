import type { PageSpec, MiniEvent } from '../../types/runtime';
import type { Province } from '../../../packages/client-contracts/src/documents';
import type { ExperienceWire as Experience } from '../../../packages/client-contracts/src/documents';
import { isRecord, isExperience } from '../../utils/generated/document-contracts';
interface Guide {
    guide_url: string;
    region_name?: string;
    authority?: string;
    service_name?: string;
    steps?: unknown[];
    [key: string]: unknown;
}
type Link = {
    name: string;
    kind?: string;
    url: string;
};
type Data = {
    province: Partial<Province>;
    experience: Experience;
    theme: Partial<NonNullable<Experience['theme']>>;
    templateLinks: Link[];
    process: NonNullable<Province['process']>;
    materials: string[];
    guides: Guide[];
    guideLabels: string[];
    selectedGuide: Guide | null;
    guideError: string;
    serviceLabel?: string;
    guideDate?: string;
};
type Methods = {
    onLoad(options: Record<string, string | undefined>): void;
    updateProvince(province: Province): void;
    updateExperience(experience: Experience | undefined): void;
    copyPreferred(): void;
    copyTemplate(event: MiniEvent): void;
    selectGuide(event: MiniEvent): void;
    openRegional(): void;
    openDocument(event: MiniEvent): void;
    copyGuide(): void;
    copyPortal(): void;
};
import * as docs from '../../utils/documents';
import experienceData = require('../../data/provinceExperiences');
const experiences = experienceData.provinces;
const page: PageSpec<Data, Methods, {
    slug: string;
}> = {
    data: { province: {}, experience: { steps: [], materials: [], notes: [] }, theme: {}, templateLinks: [], process: [], materials: [], guides: [], guideLabels: [], selectedGuide: null, guideError: '' },
    onLoad(options) {
        this.slug = options.slug || '';
        const province = docs.findProvince(options.slug);
        if (!province) {
            this.setData({ guideError: '省份无效，请返回首页' });
            return;
        }
        this.updateProvince(province);
        this.updateExperience(experiences[this.slug]);
        wx.request<Record<string, unknown> | string | ArrayBuffer>({ url: `${docs.apiBase()}/api/portal-reports/experiences/${this.slug}`, timeout: 15000,
            success: res => { if (res.statusCode === 200 && isRecord(res.data) && res.data.slug === this.slug) {
                const merged = { ...experiences[this.slug], ...res.data };
                if (isExperience(merged))
                    this.updateExperience(merged);
            } },
        });
        docs.loadCatalog(items => { const live = docs.mergeCatalog(items).find(p => p.slug === this.slug); if (live)
            this.updateProvince({ ...province, ...live }); });
        wx.request<Record<string, unknown> | string | ArrayBuffer>({ url: `${docs.apiBase()}/api/portal-reports/workflows/${this.slug}`, timeout: 15000,
            success: res => {
                if (res.statusCode !== 200) {
                    this.setData({ guideError: '本次暂无地区流程记录，请查询官方办理页面' });
                    return;
                }
                const guides = (isRecord(res.data) && Array.isArray(res.data.guides) ? res.data.guides : []).filter((g: unknown): g is Guide => isRecord(g) && typeof g.guide_url === 'string' && (g.steps === undefined || Array.isArray(g.steps)) && /^https?:\/\//.test(g.guide_url));
                this.setData({ guides, guideLabels: guides.map(g => `${g.region_name || '未标明地区'} · ${g.authority || g.service_name || '官方指南'}`), selectedGuide: guides.find(g => g.steps && g.steps.length) || guides[0] || null, guideError: guides.length ? '' : '本次暂无地区流程记录' });
            }, fail: () => this.setData({ guideError: '地区流程加载失败，请启动后端并检查网络' }),
        });
    },
    updateProvince(province) {
        const base = { ...province, hasApplication: !!province.documents.application, hasEvidence: !!province.documents.evidence };
        this.setData({ province: base, process: base.process || [], materials: base.materials || [] });
        wx.setNavigationBarTitle({ title: `${province.shortName}劳动仲裁` });
    },
    updateExperience(experience) {
        if (!experience)
            return;
        const theme = experience.theme || experiences[this.slug]?.theme || { accent: '#1b6b63' };
        const templates = (experience.templates || []).map(t => ({ name: t.material_name || t.text || '查看文书模板', kind: t.kind, url: t.url || experience.source_url || experience.portal_url || '' })).filter(t => /^https?:\/\//.test(t.url || ''));
        this.setData({ experience, theme, templateLinks: templates, serviceLabel: experience.service_kind === 'mediation' ? '劳动争议调解（不是仲裁申请）' : experience.service_kind === 'arbitration' ? '劳动人事争议仲裁申请' : '请在官方入口查询', guideDate: (experience.captured_at || '').slice(0, 10) || '尚未确认' });
        wx.setNavigationBarColor({ frontColor: '#ffffff', backgroundColor: theme.accent });
    },
    copyPreferred() { const p = this.data.experience; wx.setClipboardData({ data: p.source_url || p.portal_url || '' }); },
    copyTemplate(event) { wx.setClipboardData({ data: this.data.templateLinks[Number(event.currentTarget.dataset.index)]?.url || '' }); },
    selectGuide(event) { this.setData({ selectedGuide: this.data.guides[Number(event.detail.value)] || null }); },
    openRegional() { wx.navigateTo({ url: `/pages/regional/index?province=${encodeURIComponent(this.slug)}` }); },
    openDocument(event) { wx.navigateTo({ url: `/pages/document/index?slug=${this.slug}&kind=${event.currentTarget.dataset.kind}` }); },
    copyGuide() { if (this.data.selectedGuide)
        wx.setClipboardData({ data: this.data.selectedGuide.guide_url }); },
    copyPortal() { wx.setClipboardData({ data: this.data.province.source_url || '' }); },
};
Page(page);
