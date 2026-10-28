"""Stream answers from the configured Ubuntu Ollama; never start a model process."""
import json,os
import httpx
from .remote import resolve_remote

SYSTEM_PROMPT=(
    '你是面向普通劳动者的中国劳动争议法律信息助手。'
    '请使用通俗、克制的中文，先概括问题，再给出可执行步骤和建议准备的材料。'
    '不得编造法条、办理期限、地方政策或裁判结果；没有可靠依据时不要给出精确天数。'
    '不要将某个地区的办理要求套用全国。缺少地区或事实时说明需要核实的内容。'
    '重要决定请向当地仲裁机构、12333或执业律师核实，不声称已经形成律师委托关系。'
    '不要输出思考过程，不索取完整身份证号或其他非必要个人资料。'
)

async def generate_lawyer_chat(history,model=None,api_base=None,temperature=None,reasoning_effort=None):
    config=resolve_remote(model,api_base)
    messages=[{'role':'system','content':SYSTEM_PROMPT}]
    # API callers cannot replace the trusted system message. Bound past context;
    # the newest question remains intact rather than silently being cut short.
    recent=[];size=0
    for message in reversed(history[-12:]):
        if message.get('role') not in {'user','assistant'}:continue
        content=message.get('content','')
        if not isinstance(content,str) or not content.strip():continue
        if size+len(content)>6500:
            if not recent:raise ValueError('问题较长，请分段描述后再发送。')
            break
        recent.append({'role':message['role'],'content':content});size+=len(content)
    messages+=list(reversed(recent))
    payload={'model':config.model.removeprefix('ollama/'),'messages':messages,'stream':True,'think':False,
             'keep_alive':'5m','options':{'temperature':temperature if temperature is not None else 0.35,
             'num_ctx':8192,'num_predict':min(int(os.getenv('LABOURLAWYER_LLM_MAX_TOKENS','768')),2048)}}
    received=False;completed=False
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(300,connect=8),trust_env=False) as client:
            async with client.stream('POST',config.endpoint+'/api/chat',json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():continue
                    item=json.loads(line)
                    if item.get('error'):raise RuntimeError('Ubuntu 远程模型暂时无法回答，请稍后重试。')
                    content=item.get('message',{}).get('content')
                    if content:received=True;yield content
                    if item.get('done') is True:completed=True;break
    except (httpx.HTTPError,ValueError) as exc:
        raise RuntimeError('无法连接 Ubuntu 远程模型，请检查远程 AI 连接；文书生成仍可使用。') from exc
    if not received:raise RuntimeError('Ubuntu 远程模型没有返回内容，请稍后重试。')
    if not completed:raise RuntimeError('Ubuntu 远程回答中断，当前内容可能不完整，请重试。')
