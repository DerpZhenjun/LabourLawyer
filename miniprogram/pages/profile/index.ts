import type { PageSpec } from '../../types/runtime';
const page: PageSpec<{
    version: string;
}, {
    clearData(): void;
}> = { data: { version: '1.0.0' }, clearData() { wx.showModal({ title: '清除本机数据', content: '将删除小程序中保存的案件草稿，此操作不可撤销。', success: res => { if (res.confirm) {
            wx.removeStorageSync('labourlawyer_cases');
            wx.showToast({ title: '已清除' });
        } } }); } };
Page(page);
