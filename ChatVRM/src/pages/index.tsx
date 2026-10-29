import { useCallback, useContext, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import VrmViewer from "@/components/vrmViewer";
import { ViewerContext } from "@/features/vrmViewer/viewerContext";
import { Message, textsToScreenplay } from "@/features/messages/messages";
import { speakCharacter, interruptSpeakCharacter } from "@/features/messages/speakCharacter";
import { DEFAULT_PARAM } from "@/features/constants/koeiroParam";
import { getChatResponseStream } from "@/features/chat/openAiChat";
import { Meta } from "@/components/meta";

const prompts = ["公司拖欠工资怎么办？", "仲裁需要哪些证据？", "收到辞退通知怎么办？"];
export default function Home() {
  const { viewer } = useContext(ViewerContext);
  const [chatLog, setChatLog] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [voice, setVoice] = useState(false);
  const [avatar, setAvatar] = useState("loading");
  const [error, setError] = useState("");
  const [backend, setBackend] = useState<boolean | null>(null);
  const [connectionMessage, setConnectionMessage] = useState("正在检查 Ubuntu Qwen3.8 连接…");
  const [checkingConnection, setCheckingConnection] = useState(false);
  const healthRequest = useRef<AbortController>();
  const [avatarAttempt, setAvatarAttempt] = useState(0);
  const [voiceMode, setVoiceMode] = useState("browser");
  const [voiceSupported, setVoiceSupported] = useState(false);
  const [micSupported, setMicSupported] = useState(false);
  const [recording, setRecording] = useState(false);
  const recognition = useRef<SpeechRecognition>();
  const [embedded, setEmbedded] = useState(false);
  const end = useRef<HTMLDivElement>(null);
  const voiceRef = useRef(false);
  const processing = useRef(false);
  const request = useRef<AbortController>();
  const checkConnection = useCallback(async () => {
    healthRequest.current?.abort();
    const controller = new AbortController(); healthRequest.current = controller;
    setCheckingConnection(true);
    const timer = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch("/api/health/", { signal: controller.signal, cache: "no-store" });
      if (!response.ok) throw new Error();
      const state = await response.json();
      if (healthRequest.current !== controller) return;
      const ready = state.backend === true && state.ai?.ready === true;
      setBackend(ready); setVoiceMode(state.voice);
      setConnectionMessage(ready ? "Ubuntu · qwen3.8:27b，已连接" : state.ai?.message || "Ubuntu 远程问答暂未连接，文书生成仍可使用。");
    } catch {
      if (healthRequest.current === controller) { setBackend(false); setConnectionMessage("连接检查未完成，请检查项目后端和 Ubuntu SSH 连接后重试。"); }
    } finally {
      clearTimeout(timer);
      if (healthRequest.current === controller) setCheckingConnection(false);
    }
  }, []);
  useEffect(() => {
    setEmbedded(new URLSearchParams(window.location.search).get("embed") === "1");
    setVoiceSupported("speechSynthesis" in window);
    setMicSupported(Boolean(window.SpeechRecognition || window.webkitSpeechRecognition));
    try {
      const saved = JSON.parse(localStorage.getItem("labourlawyer.digital.chat") || "[]");
      if (Array.isArray(saved)) setChatLog(saved.filter(m => ["user", "assistant"].includes(m?.role) && typeof m.content === "string").slice(-20));
    } catch { /* Ignore damaged local drafts. */ }
    checkConnection(); const poll = setInterval(checkConnection, 20000);
    return () => { clearInterval(poll); healthRequest.current?.abort(); healthRequest.current = undefined; request.current?.abort(); recognition.current?.abort(); interruptSpeakCharacter(); };
  }, [checkConnection]);
  useEffect(() => { try { localStorage.setItem("labourlawyer.digital.chat", JSON.stringify(chatLog.slice(-20))); } catch {} end.current?.scrollIntoView({ block: "end" }); }, [chatLog, busy]);
  useEffect(() => {
    const close = (event: KeyboardEvent) => {
      if (!embedded || event.key !== "Escape" || !document.referrer || window.parent === window) return;
      window.parent.postMessage({ type: "labourlawyer:digital-close" }, new URL(document.referrer).origin);
    };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [embedded]);
  const avatarReady = useCallback(() => setAvatar("ready"), []);
  const avatarFailed = useCallback(() => setAvatar("error"), []);
  const send = async (text = input) => {
    text = text.trim(); if (!text || processing.current || backend !== true) return;
    processing.current = true; setBusy(true); setInput(""); setError("");
    const history: Message[] = [...chatLog.slice(-11), { role: "user", content: text }];
    setChatLog([...history, { role: "assistant", content: "" }]);
    request.current = new AbortController();
    let reader: ReadableStreamDefaultReader<string> | undefined, answer = "";
    try {
      const stream = await getChatResponseStream(history, "", request.current.signal);
      reader = stream.getReader();
      while (true) { const part = await reader.read(); if (part.done) break; answer += part.value; setChatLog([...history, { role: "assistant", content: answer }]); }
      if (!answer.trim()) throw new Error("模型没有返回内容，请重试。");
      setBackend(true);
      if (voiceRef.current) { const screenplay = textsToScreenplay([answer], DEFAULT_PARAM)[0]; if (screenplay) speakCharacter(screenplay, viewer, ""); }
    } catch (e) {
      if (!request.current.signal.aborted) { setError(e instanceof Error ? e.message : "连接中断，请重试。"); setChatLog([...history, { role: "assistant", content: answer || "暂时无法获取回答，请检查项目后端和 Ubuntu 远程连接。" }]); }
    } finally { reader?.releaseLock(); processing.current = false; setBusy(false); }
  };
  const toggleMic = () => {
    if (recording) { recognition.current?.abort(); setRecording(false); return; }
    const Recognizer = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognizer || processing.current) return;
    const r = new Recognizer(); recognition.current = r;
    r.lang = "zh-CN"; r.interimResults = true; r.continuous = false;
    r.onresult = e => { const text = e.results[0][0].transcript; setInput(text); if (e.results[0].isFinal) send(text); };
    r.onend = () => setRecording(false);
    r.onerror = () => { setRecording(false); setError("语音输入未成功，请检查麦克风权限或直接输入文字。"); };
    try { r.start(); setRecording(true); setError(""); } catch { setError("无法启动麦克风，请直接输入文字。"); }
  };
  return <main className={`digital-app ${embedded ? "embedded" : ""}`}>
    <Meta />
    <header className="counsel-topbar"><div><img src="/brand/counsel-mark.svg" width={38} height={38} alt="" /><span><small>LABOUR LAWYER</small><strong>阿律 · 法律数字人</strong></span></div><span className={`service-badge ${backend === false ? "offline" : ""}`}><i />{backend === null ? "检查服务" : backend ? "远程问答已连接" : "远程问答未连接"}</span></header>
    <div className="counsel-workspace">
      <section className="avatar-stage" aria-label="数字人形象" data-avatar-state={avatar}>
        <div className="stage-rings" aria-hidden="true" />
        <div className="avatar-portrait"><VrmViewer key={avatarAttempt} onReady={avatarReady} onError={avatarFailed} /></div>
        {avatar !== "ready" && <div className="avatar-notice" role="status">{avatar === "loading" ? "正在加载数字人形象…" : "形象加载失败，仍可使用文字咨询。"}</div>}
        {avatar === "error" && <button className="avatar-retry" onClick={() => { setAvatar("loading"); setAvatarAttempt(n => n + 1); }}>重新加载形象</button>}
        <div className="stage-label"><span>你的劳动法律助手</span><h1>你好，我是阿律</h1><p>先说说你遇到的问题，<br />我们一起梳理下一步。</p></div>
      </section>
      <section className="consultation-panel" aria-label="法律咨询对话">
        <div className="conversation-heading"><div><small>YOUR CONSULTATION</small><h2>劳动争议咨询</h2></div><div className="conversation-actions"><button disabled={!voiceSupported && voiceMode !== "gpt-sovits"} className={voice ? "active" : ""} onClick={() => { voiceRef.current = !voice; setVoice(!voice); if (voice) interruptSpeakCharacter(); }} aria-label={voice ? "关闭语音朗读" : "开启语音朗读"} title={voiceMode === "gpt-sovits" ? "语音合成朗读" : "浏览器语音朗读"}>{voice ? "♫" : "♪"}<span>{voice ? "朗读开" : "朗读关"}</span></button><button disabled={busy || !chatLog.length} onClick={() => { interruptSpeakCharacter(); setChatLog([]); setError(""); }} aria-label="清空对话" title="清空对话">↺</button></div></div>
        <div className={`connection-notice ${backend ? "connected" : ""}`} role="status"><span>{connectionMessage}</span>{backend !== true && <button type="button" onClick={checkConnection} disabled={checkingConnection}>{checkingConnection ? "检查中…" : "重新检查连接"}</button>}</div>
        <div className="conversation-log" role="log" aria-label="咨询记录" aria-live="polite">
          {!chatLog.length && <div className="welcome-card"><p>你遇到了什么问题？也可以从下面的问题开始聊。</p><div className="prompt-list">{prompts.map(text => <button key={text} disabled={backend !== true} onClick={() => send(text)}>{text}<span>↗</span></button>)}</div></div>}
          {chatLog.map((m, i) => <article key={i} className={`counsel-message ${m.role}`}><small>{m.role === "user" ? "你" : "阿律"}</small><div>{m.content ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content.replace(/<think>[\s\S]*?(<\/think>|$)/gi, "")}</ReactMarkdown> : <span className="reply-loading">正在梳理你的问题<span>…</span></span>}</div></article>)}
          <div ref={end} />
        </div>
        {error && <p className="consultation-error" role="alert">{error}</p>}
        <form className="counsel-composer" onSubmit={e => { e.preventDefault(); send(); }}><label htmlFor="counsel-question" className="sr-only">描述你的劳动争议问题</label><textarea id="counsel-question" value={input} maxLength={8000} onChange={e => setInput(e.target.value)} placeholder="例如：公司拖欠了两个月工资，我该准备什么证据？" rows={2} disabled={busy} onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); send(); } }} /><div><span>{recording ? "正在听，请描述你的问题" : busy ? "正在生成回答" : "Enter 发送 · Shift + Enter 换行"}</span><div className="composer-buttons"><button type="button" className={`mic-button ${recording ? "recording" : ""}`} aria-label={recording ? "停止语音输入" : "开始语音输入"} title={micSupported ? "语音输入" : "当前浏览器不支持语音输入"} disabled={!micSupported || busy} onClick={toggleMic}>{recording ? "停止" : "语音"}</button><button type="submit" disabled={busy || backend !== true || !input.trim()}>{busy ? "思考中…" : "发送问题 ↗"}</button></div></div></form>
        <p className="counsel-disclaimer">提供法律信息辅助，不代表律师委托或办案结果。</p>
      </section>
    </div>
  </main>;
}
