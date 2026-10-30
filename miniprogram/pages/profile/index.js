// Generated from pages/profile/index.ts. Do not edit.
// source-sha256: ec1c4282c98319ab0d461eb6c0839cb03e71eb20d92e6f42361bd0a1554e80f3
"use strict";
const release = require("../../utils/generated/release-info");
const page = { data: { version: release.version }, clearData() {
        wx.showModal({ title: '清除本机数据', content: '将删除小程序中保存的案件草稿，此操作不可撤销。', success: res => {
                if (res.confirm) {
                    wx.removeStorageSync('labourlawyer_cases');
                    wx.showToast({ title: '已清除' });
                }
            } });
    } };
Page(page);
