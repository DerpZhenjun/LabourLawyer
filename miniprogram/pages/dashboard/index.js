// Generated from pages/dashboard/index.ts. Do not edit.
// source-sha256: 9a25ca8b8908a66f5b0b49f55a7f8c96d3eb9a7140feac0a72afd67ed1fcebd3
"use strict";
const docs = require("../../utils/documents");
const featuredSlugs = ['zhejiang', 'guangdong', 'jiangsu', 'liaoning', 'fujian'];
function cards(provinces) {
    return provinces.map(p => ({ ...p, mark: p.shortName.slice(0, 1), ready: !!p.documents.application || !!p.documents.evidence, meta: [p.documents.application ? '申请书' : '', p.documents.evidence ? '证据清单' : ''].filter(Boolean).join(' · ') || '官方办理指南' }));
}
const page = {
    data: { featured: [], others: [] },
    onLoad() { this.update(docs.provinces); docs.loadCatalog(items => this.update(docs.mergeCatalog(items))); },
    update(provinces) { const all = cards(provinces); this.setData({ featured: all.filter(p => featuredSlugs.includes(p.slug)), others: all.filter(p => !featuredSlugs.includes(p.slug)) }); },
    openProvince(event) { wx.navigateTo({ url: `/pages/province/index?slug=${event.currentTarget.dataset.slug}` }); },
};
Page(page);
