import logging
import os
from typing import List, Dict, AsyncGenerator

import litellm

# 配置简单的日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def generate_lawyer_chat(
    history: List[Dict[str, str]], 
    model: str | None = None,
    api_base: str | None = None,
    temperature: float | None = None,
    reasoning_effort: str | None = None,
) -> AsyncGenerator[str, None]:
    """
    支持多轮对话的流式生成
    :param history: 完整的对话历史 [{"role": "user", "content": "..."}, ...]
    """
    
    # 确保系统提示词始终在第一位
    model = model or os.getenv("LABOURLAWYER_LLM_MODEL", "ollama/qwen3.8:27b")
    api_base = api_base or os.getenv("OLLAMA_API_BASE", "http://10.66.66.1:11434")
    if model != 'ollama/qwen3.8:27b' or api_base != 'http://10.66.66.1:11434':
        raise ValueError('本次只使用 Ubuntu Ollama http://10.66.66.1:11434 / qwen3.8:27b')
    temperature = temperature if temperature is not None else float(os.getenv("LABOURLAWYER_LLM_TEMPERATURE", "0.5"))
    reasoning_effort = reasoning_effort or os.getenv("LABOURLAWYER_LLM_REASONING", "none")
    max_tokens = int(os.getenv("LABOURLAWYER_LLM_MAX_TOKENS", "1200"))

    system_prompt = {
        "role": "system", 
        "content": (
            "你是面向普通劳动者的中国劳动争议法律信息助手。"
            "请使用通俗、克制的中文，先概括结论，再列出可执行步骤、建议准备的证据和需要注意的仲裁时效。"
            "不确定的事实必须明确说明，不得编造法条、办理期限、地方政策或裁判结果；没有可靠依据时不要给出精确天数。"
            "涉及重要决定时提醒用户向当地仲裁委员会、12333或执业律师核实。"
            "回答不应声称已经形成律师委托关系。"
        )
    }
    
    # 如果历史记录里没有系统提示词，手动加上
    if not history or history[0].get("role") != "system":
        messages = [system_prompt] + history
    else:
        messages = history

    logger.info(f"🚀 发送请求给模型: {model}, 消息数: {len(messages)}")

    try:
        response = await litellm.acompletion(
            model=model,
            messages=messages,
            api_base=api_base,
            stream=True,
            temperature=temperature,
            reasoning_effort=reasoning_effort,
            max_tokens=max_tokens,
            api_key="ollama",
            timeout=600  # 设置 600秒 超时，防止生成过长卡死
        )

        async for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                # DeepSeek R1 会输出 <think> 标签。
                # 如果你想在后端处理掉思考过程，可以在这里加正则过滤。
                # 但通常建议保留，让前端决定是否折叠显示。
                yield content

    except litellm.Timeout:
        logger.error("模型响应超时")
        yield "⚠️ 回答超时，请简化问题或稍后再试。"
    except Exception as e:
        logger.error(f"调用异常: {e}")
        yield "⚠️ 系统内部错误，请联系管理员。"
