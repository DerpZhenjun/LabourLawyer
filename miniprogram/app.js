// Generated from app.ts. Do not edit.
// source-sha256: 99a05233506f85ee1aa00a4bb98331225e86db4f6a6d02bb77c9188c4e2e3511
"use strict";
App({
    globalData: {
        apiBase: 'http://127.0.0.1:8000',
        cases: [
            { id: 'PL-2026-018', title: '工资及加班费争议', client: '陈*', stage: '材料准备', deadline: '09-22', progress: 75, urgent: false },
            { id: 'PL-2026-017', title: '违法解除劳动合同', client: '林*', stage: '待提交', deadline: '09-19', progress: 88, urgent: true },
            { id: 'PL-2026-015', title: '工伤待遇争议', client: '周*', stage: '审理中', deadline: '10-08', progress: 94, urgent: false }
        ]
    },
    onLaunch() {
        const saved = wx.getStorageSync('labourlawyer_cases');
        if (Array.isArray(saved) && saved.length && saved.every((v) => v !== null && typeof v === 'object' && ['id', 'title', 'client', 'stage', 'deadline'].every(k => typeof Reflect.get(v, k) === 'string') && typeof Reflect.get(v, 'progress') === 'number'))
            this.globalData.cases = saved;
    }
});
