// Generated from packages/client-contracts/src/index.ts. Do not edit.
// source-sha256: ae8d98553d8d7bbae7c1601863092b604cefcac175024128fede639b752286c6
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// packages/client-contracts/src/index.ts
var index_exports = {};
__export(index_exports, {
  API_LIMITS: () => API_LIMITS,
  apiURL: () => apiURL,
  assertAIStatus: () => assertAIStatus,
  buildAskRequest: () => buildAskRequest,
  createAnswerDecoder: () => createAnswerDecoder,
  parseStoredChat: () => parseStoredChat,
  remoteReady: () => remoteReady
});
module.exports = __toCommonJS(index_exports);

// packages/client-contracts/src/generated/api-limits.ts
var API_LIMITS = {
  "questionMax": 8e3,
  "messageMax": 8e3,
  "historyMax": 12
};

// packages/client-contracts/src/index.ts
var record = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
var length = (s) => Array.from(s).length;
function apiURL(base, path) {
  if (!path.startsWith("/") || path.startsWith("//") || path.includes("..") || path.includes("\\") || /[\r\n]/.test(path)) throw new Error("\u63A5\u53E3\u8DEF\u5F84\u65E0\u6548\u3002");
  if (!/^https?:\/\/[^/?#\s@\\]+(?:\/[^?#\s\\]*)?$/.test(base)) throw new Error("\u670D\u52A1\u5730\u5740\u65E0\u6548\u3002");
  return base.replace(/\/$/, "") + path;
}
function assertAIStatus(raw) {
  if (!record(raw) || typeof raw.ready !== "boolean" || typeof raw.provider !== "string" || typeof raw.model !== "string" || typeof raw.local_model_started !== "boolean") throw new Error("\u52A9\u624B\u72B6\u6001\u683C\u5F0F\u4E0D\u6B63\u786E\uFF0C\u8BF7\u91CD\u8BD5\u3002");
  return { ready: raw.ready, provider: raw.provider, model: raw.model, local_model_started: raw.local_model_started, ...typeof raw.message === "string" ? { message: raw.message } : {}, ...typeof raw.status === "string" ? { status: raw.status } : {} };
}
var remoteReady = (s) => s.ready && s.provider === "Ubuntu Ollama" && s.model === "qwen3.8:27b" && !s.local_model_started;
function buildAskRequest(question, raw) {
  const text = question.trim();
  if (!text || length(text) > API_LIMITS.questionMax) throw new Error(`\u8BF7\u586B\u5199\u4E0D\u8D85\u8FC7${API_LIMITS.questionMax}\u5B57\u7B26\u7684\u95EE\u9898\u3002`);
  if (!Array.isArray(raw)) throw new Error("\u5BF9\u8BDD\u8BB0\u5F55\u683C\u5F0F\u4E0D\u6B63\u786E\u3002");
  const history = [];
  for (const item of raw) {
    if (!record(item) || !["ai", "assistant", "user"].includes(String(item.role)) || typeof item.content !== "string") throw new Error("\u5BF9\u8BDD\u8BB0\u5F55\u683C\u5F0F\u4E0D\u6B63\u786E\u3002");
    if (!item.content) continue;
    if (length(item.content) > API_LIMITS.messageMax) throw new Error(`\u5355\u6761\u5BF9\u8BDD\u8D85\u8FC7${API_LIMITS.messageMax}\u5B57\u7B26\uFF0C\u8BF7\u6E05\u7A7A\u5BF9\u8BDD\u540E\u91CD\u8BD5\u3002`);
    history.push({ role: item.role === "user" ? "user" : "assistant", content: item.content });
  }
  return { question: text, history: history.slice(-API_LIMITS.historyMax) };
}
function parseStoredChat(text) {
  if (!text) return null;
  try {
    const raw = JSON.parse(text);
    if (!Array.isArray(raw) || !raw.length) return null;
    const result = [];
    for (const item of raw) {
      if (!record(item) || !["ai", "user"].includes(String(item.role)) || typeof item.content !== "string") return null;
      result.push({ role: item.role === "user" ? "user" : "ai", content: item.content });
    }
    return result;
  } catch {
    return null;
  }
}
function createAnswerDecoder() {
  const decoder = new TextDecoder();
  return { push: (value) => decoder.decode(value, { stream: true }), finish: () => decoder.decode() };
}
