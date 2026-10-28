import type { NextApiRequest, NextApiResponse } from "next";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Cache-Control", "no-store");
  if (req.method !== "GET") return res.status(405).end();
  const base = process.env.LABOURLAWYER_API_BASE || "http://127.0.0.1:8000";
  let backend = false;
  try {
    const response = await fetch(`${base.replace(/\/$/, "")}/health`, { signal: AbortSignal.timeout(2500) });
    backend = response.ok && (await response.json()).service === "api";
  } catch { /* The avatar can load while the backend reconnects. */ }
  res.status(200).json({ service: "digital-human", backend, voice: process.env.LABOURLAWYER_TTS_URL ? "gpt-sovits" : "browser" });
}
