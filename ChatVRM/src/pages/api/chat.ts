import type { NextApiRequest, NextApiResponse } from "next";
import {buildAskRequest} from "../../../../packages/client-contracts/generated/index.cjs";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== "POST") { res.setHeader("Allow", "POST"); return res.status(405).json({ message: "请使用 POST 请求。" }); }
  const body:unknown=req.body;
  const raw=body!==null&&typeof body==='object'&&'messages' in body?body.messages:[];
  let payload:ReturnType<typeof buildAskRequest>;
  try {
    if(!Array.isArray(raw))throw new Error('Invalid history');
    const last:unknown=raw[raw.length-1];
    if(last===null||typeof last!=='object'||!('role' in last)||last.role!=='user'||!('content' in last)||typeof last.content!=='string')throw new Error('Missing question');
    payload=buildAskRequest(last.content,raw);
  }catch{return res.status(400).json({message:'请输入有效的问题和对话记录。'});}
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 600000);
  const cancel = () => controller.abort();
  res.on("close", cancel);
  let reader: ReadableStreamDefaultReader<Uint8Array> | undefined;
  try {
    const base = process.env.LABOURLAWYER_API_BASE || "http://127.0.0.1:8000";
    const upstream = await fetch(`${base.replace(/\/$/, "")}/api/ask`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload), signal: controller.signal,
    });
    if (!upstream.ok || !upstream.body) return res.status(502).json({ message: "问答服务暂不可用，请检查项目后端。" });
    res.setHeader("Content-Type", "text/plain; charset=utf-8");
    // Next's compression middleware respects no-transform; do not buffer token chunks in gzip.
    res.setHeader("Cache-Control", "no-cache, no-transform");
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
