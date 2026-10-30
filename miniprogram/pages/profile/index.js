// Generated from pages/profile/index.ts. Do not edit.
// source-sha256: d114779aba0654ee5fe80adb67c2e41daf5d9b9b597195cbc15cc63c1a8cb29f
"use strict";
const page = { data: { version: '1.0.0' }, clearData() {
        wx.showModal({ title: '清除本机数据', content: '将删除小程序中保存的案件草稿，此操作不可撤销。', success: res => {
                if (res.confirm) {
                    wx.removeStorageSync('labourlawyer_cases');
                    wx.showToast({ title: '已清除' });
                }
            } });
    } };
Page(page);
