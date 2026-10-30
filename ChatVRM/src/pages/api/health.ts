import type { NextApiRequest, NextApiResponse } from "next";
import {assertAIStatus,remoteReady} from "../../../../packages/client-contracts/generated/index.cjs";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Cache-Control", "no-store");
  if (req.method !== "GET") return res.status(405).end();
  const base = process.env.LABOURLAWYER_API_BASE || "http://127.0.0.1:8000";
  let backend = false;
  let ai = { ready: false, status: "backend_unavailable", model: "qwen3.8:27b", message: "项目后端暂未连接，请检查后端是否已启动。" };
  try {
    const response = await fetch(`${base.replace(/\/$/, "")}/health`, { signal: AbortSignal.timeout(2500) });
    backend = response.ok && (await response.json()).service === "api";
    if (backend) {
      const status = await fetch(`${base.replace(/\/$/, "")}/api/ai/status`, { signal: AbortSignal.timeout(10000) });
      if (status.status === 404) {
        ai = { ...ai, status: "backend_update_required", message: "当前后端尚未加载远程问答接口，需要重启本项目后端。" };
      } else if (status.ok) {
        const result = assertAIStatus(await status.json());
        const correctModel = result.model === "qwen3.8:27b" && result.provider === "Ubuntu Ollama" && !result.local_model_started;
        ai = result.ready && !correctModel
          ? { ...ai, status: "model_mismatch", message: "远程模型配置不一致，请使用 Ubuntu 上的 qwen3.8:27b。" }
          : { ...ai, ...result, ready: remoteReady(result) };
      } else {
        ai = { ...ai, status: "unavailable", message: "远程问答状态检查失败，请稍后重试。" };
      }
    }
  } catch {
    if (backend) ai = { ...ai, status: "unavailable", message: "项目后端已启动，但 Ubuntu 远程问答状态检查未完成，请重试连接。" };
  }
  res.status(200).json({ service: "digital-human", backend, ai, voice: process.env.LABOURLAWYER_TTS_URL ? "gpt-sovits" : "browser" });
}
