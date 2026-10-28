import { Message } from "../messages/messages";
import { interruptSpeakCharacter } from "../messages/speakCharacter";

export async function getChatResponseStream(messages: Message[], _apiKey: string, signal?: AbortSignal) {
  interruptSpeakCharacter();
  const response = await fetch("/api/chat/", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ messages }), signal,
  });
  if (!response.ok || !response.body) throw new Error("问答服务暂不可用，请检查项目后端。");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  return new ReadableStream<string>({
    async pull(controller) {
      try {
        const { done, value } = await reader.read();
        if (done) { const tail = decoder.decode(); if (tail) controller.enqueue(tail); controller.close(); reader.releaseLock(); }
        else { const text = decoder.decode(value, { stream: true }); if (text) controller.enqueue(text); }
      } catch (error) { controller.error(error); reader.releaseLock(); }
    },
    async cancel() { await reader.cancel(); reader.releaseLock(); },
  });
}
export async function getChatResponse(messages: Message[], apiKey: string) {
  const stream = await getChatResponseStream(messages, apiKey), reader = stream.getReader();
  let message = "";
  try { while (true) { const chunk = await reader.read(); if (chunk.done) break; message += chunk.value; } }
  finally { reader.releaseLock(); }
  return { message };
}
