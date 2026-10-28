import type { NextApiRequest, NextApiResponse } from "next";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== "POST") return res.status(405).end();
  const endpoint = process.env.LABOURLAWYER_TTS_URL;
  const reference = process.env.LABOURLAWYER_TTS_REF_AUDIO;
  const text = typeof req.body.text === "string" ? req.body.text.trim().slice(0, 8000) : "";
  if (!text) return res.status(400).json({ message: "缺少朗读内容。" });
  if (!endpoint || !reference) return res.status(503).json({ message: "未配置 GPT-SoVITS，使用浏览器朗读。" });
  try {
    const url = new URL(endpoint);
    url.searchParams.set("text", text); url.searchParams.set("text_lang", "zh"); url.searchParams.set("prompt_lang", "zh");
    url.searchParams.set("ref_audio_path", reference);
    url.searchParams.set("prompt_text", process.env.LABOURLAWYER_TTS_PROMPT || "");
    const response = await fetch(url, { signal: AbortSignal.timeout(20000) });
    if (!response.ok) throw new Error("TTS unavailable");
    res.setHeader("Content-Type", response.headers.get("content-type") || "audio/wav");
    res.send(Buffer.from(await response.arrayBuffer()));
  } catch { res.status(502).json({ message: "语音合成不可用，使用浏览器朗读。" }); }
}