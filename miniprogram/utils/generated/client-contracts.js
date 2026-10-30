// Generated from packages/client-contracts/src/index.ts. Do not edit.
// source-sha256: b4e687559c9fc9eb31c04d9727b65682f7a3fb552f69f18fbec744e34147459b
"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.remoteReady = void 0;
exports.apiURL = apiURL;
exports.assertAIStatus = assertAIStatus;
exports.buildAskRequest = buildAskRequest;
exports.parseStoredChat = parseStoredChat;
exports.createAnswerDecoder = createAnswerDecoder;
const record = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);
const length = (s) => Array.from(s).length;
function apiURL(base, path) {
    if (!path.startsWith('/') || path.startsWith('//') || path.includes('..') || path.includes('\\') || /[\r\n]/.test(path))
        throw new Error('接口路径无效。');
    // WeChat's script runtime does not provide the browser URL constructor.
    if (!/^https?:\/\/[^/?#\s@\\]+(?:\/[^?#\s\\]*)?$/.test(base))
        throw new Error('服务地址无效。');
    return base.replace(/\/$/, '') + path;
}
function assertAIStatus(raw) {
    if (!record(raw) || typeof raw.ready !== 'boolean' || typeof raw.provider !== 'string' || typeof raw.model !== 'string' || typeof raw.local_model_started !== 'boolean')
        throw new Error('助手状态格式不正确，请重试。');
    return { ready: raw.ready, provider: raw.provider, model: raw.model, local_model_started: raw.local_model_started, ...(typeof raw.message === 'string' ? { message: raw.message } : {}), ...(typeof raw.status === 'string' ? { status: raw.status } : {}) };
}
const remoteReady = (s) => s.ready && s.provider === 'Ubuntu Ollama' && s.model === 'qwen3.8:27b' && !s.local_model_started;
exports.remoteReady = remoteReady;
function buildAskRequest(question, raw) {
    const text = question.trim();
    if (!text || length(text) > 8000)
        throw new Error('请填写不超过8000字符的问题。');
    if (!Array.isArray(raw))
        throw new Error('对话记录格式不正确。');
    const history = [];
    for (const item of raw) {
        if (!record(item) || !['ai', 'assistant', 'user'].includes(String(item.role)) || typeof item.content !== 'string')
            throw new Error('对话记录格式不正确。');
        if (!item.content)
            continue;
        if (length(item.content) > 8000)
            throw new Error('单条对话超过8000字符，请清空对话后重试。');
        history.push({ role: item.role === 'user' ? 'user' : 'assistant', content: item.content });
    }
    return { question: text, history: history.slice(-12) };
}
function parseStoredChat(text) {
    if (!text)
        return null;
    try {
        const raw = JSON.parse(text);
        if (!Array.isArray(raw) || !raw.length)
            return null;
        const result = [];
        for (const item of raw) {
            if (!record(item) || !['ai', 'user'].includes(String(item.role)) || typeof item.content !== 'string')
                return null;
            result.push({ role: item.role === 'user' ? 'user' : 'ai', content: item.content });
        }
        return result;
    }
    catch {
        return null;
    }
}
function createAnswerDecoder() { const decoder = new TextDecoder(); return { push: (value) => decoder.decode(value, { stream: true }), finish: () => decoder.decode() }; }
