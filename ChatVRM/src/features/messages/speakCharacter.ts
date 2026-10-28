import { Viewer } from "../vrmViewer/viewer";
import { Screenplay, Talk } from "./messages";
let currentSpeakToken = 0;
let queue: Promise<unknown> = Promise.resolve();
export const interruptSpeakCharacter = () => {
  currentSpeakToken++;
  queue = Promise.resolve();
  if (typeof window !== "undefined") window.speechSynthesis?.cancel();
};
const clean = (text: string) => text.replace(/<think>[\s\S]*?(<\/think>|$)/gi, "").replace(/<[^>]+>/g, "").replace(/\[(.*?)\]\(.*?\)/g, "$1").replace(/[\*#>`\-]/g, "").trim();
const browserSpeak = (text: string, token: number) => new Promise<void>(resolve => {
  if (!("speechSynthesis" in window) || token !== currentSpeakToken) return resolve();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "zh-CN";
  const chinese = window.speechSynthesis.getVoices().find(v => v.lang.startsWith("zh"));
  if (chinese) utterance.voice = chinese;
  utterance.onend = () => resolve(); utterance.onerror = () => resolve();
  window.speechSynthesis.speak(utterance);
});
export const speakCharacter = (screenplay: Screenplay, viewer: Viewer, _apiKey: string, onStart?: () => void, onComplete?: () => void) => {
  const token = currentSpeakToken, text = clean(screenplay.talk.message);
  queue = queue.catch(() => {}).then(async () => {
    if (!text || token !== currentSpeakToken) return;
    onStart?.();
    try {
      const status = await fetch("/api/health/").then(r => r.json()).catch(() => null);
      if (status?.voice === "gpt-sovits" && viewer.model) {
        try { const audio = await fetchAudio({ ...screenplay.talk, message: text }, ""); if (token === currentSpeakToken) await viewer.model.speak(audio, screenplay); return; } catch { /* Browser voice is available when local TTS fails. */ }
      }
      await browserSpeak(text, token);
    } finally { onComplete?.(); }
  });
};
export const fetchAudio = async (talk: Talk, _apiKey: string): Promise<ArrayBuffer> => {
  const response = await fetch("/api/tts/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: clean(talk.message) }), signal: AbortSignal.timeout(25000) });
  if (!response.ok) throw new Error("语音合成服务不可用");
  return response.arrayBuffer();
};
