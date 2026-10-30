import type { PageSpec, MiniEvent, AppState } from '../../types/runtime';
import type { ChatMessage } from '../../../packages/client-contracts/src/index';
import { buildAskRequest, apiURL } from '../../utils/generated/client-contracts';
type Data = {
    input: string;
    loading: boolean;
    messages: ChatMessage[];
    prompts: string[];
};
type Methods = {
    onInput(e: MiniEvent): void;
    usePrompt(e: MiniEvent): void;
    onUnload(): void;
    send(): void;
};
type State = {
    _disposed?: boolean;
    _request?: WechatMiniprogram.RequestTask;
};
const page: PageSpec<Data, Methods, State> = {
    data: { input: '', loading: false, messages: [{ role: 'ai', content: '你好，我可以帮你梳理请求事项、关键证据、仲裁时效和下一步行动。请先简单描述发生了什么。' }], prompts: ['公司口头辞退怎么办？', '仲裁需要哪些证据？', '赔偿金怎么计算？'] },
    onInput(e) { this.setData({ input: e.detail.value }); }, usePrompt(e) { this.setData({ input: String(e.currentTarget.dataset.text || '') }); },
    onUnload() { this._disposed = true; this._request?.abort(); },
    send() {
        const text = this.data.input.trim();
        if (!text || this.data.loading)
            return;
        let payload;
        try {
            payload = buildAskRequest(text, this.data.messages);
        }
        catch (error) {
            wx.showToast({ title: (error instanceof Error ? error.message : '') || '请检查问题和对话长度', icon: 'none' });
            return;
        }
        const messages: ChatMessage[] = [...this.data.messages, { role: 'user', content: text }];
        this.setData({ messages, input: '', loading: true });
        this._request = wx.request<Record<string, unknown> | string | ArrayBuffer>({ url: apiURL(getApp<AppState>().globalData.apiBase, '/api/ask'), method: 'POST', data: payload, timeout: 60000,
            success: res => !this._disposed && this.setData({ messages: [...messages, { role: 'ai', content: res.statusCode === 200 && typeof res.data === 'string' ? res.data : '当前无法连接远程助手，文书填写和生成仍可使用。' }] }),
            fail: () => !this._disposed && this.setData({ messages: [...messages, { role: 'ai', content: '当前无法连接模型服务。你仍可继续查看办理指南和准备文书。' }] }),
            complete: () => !this._disposed && this.setData({ loading: false })
        });
    }
};
Page(page);
