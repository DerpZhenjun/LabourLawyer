import type { NextApiRequest, NextApiResponse } from "next";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== "POST") { res.setHeader("Allow", "POST"); return res.status(405).json({ message: "请使用 POST 请求。" }); }
  const messages = Array.isArray(req.body.messages) ? req.body.messages.filter((m: any) => ["user", "assistant"].includes(m?.role) && typeof m?.content === "string").slice(-12) : [];
  const last = messages[messages.length - 1];
  if (!last || last.role !== "user" || !last.content.trim()) return res.status(400).json({ message: "请输入问题。" });
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 600000);
  const cancel = () => controller.abort();
  res.on("close", cancel);
  let reader: ReadableStreamDefaultReader<Uint8Array> | undefined;
  try {
    const base = process.env.LABOURLAWYER_API_BASE || "http://127.0.0.1:8000";
    const upstream = await fetch(`${base.replace(/\/$/, "")}/api/ask`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: last.content, history: messages }), signal: controller.signal,
    });
    if (!upstream.ok || !upstream.body) return res.status(502).json({ message: "问答服务暂不可用，请检查项目后端。" });
    res.setHeader("Content-Type", "text/plain; charset=utf-8");
    res.setHeader("Cache-Control", "no-cache");
    res.setHeader("X-Accel-Buffering", "no");
    res.flushHeaders();
    reader = upstream.body.getReader();
    while (!controller.signal.aborted) {
      const { done, value } = await reader.read();
      if (done) break;
      if (!res.write(Buffer.from(value))) {
        await new Promise<void>(resolve => {
          const finished = () => { res.off("drain", finished); res.off("close", finished); resolve(); };
          res.once("drain", finished); res.once("close", finished);
        });
      }
    }
    res.end();
  } catch {
    if (!res.destroyed) {
      if (!res.headersSent) res.status(502).json({ message: "无法连接问答服务，请确认后端已启动。" });
      else res.end("\n连接中断，请稍后重试。");
    }
  } finally {
    clearTimeout(timer); res.off("close", cancel);
    if (reader) { await reader.cancel().catch(() => {}); reader.releaseLock(); }
  }
}