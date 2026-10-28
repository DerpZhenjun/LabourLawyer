"""Shared, remote-only AI service for the website, mini program and avatar."""
import threading
from contextlib import aclosing
from typing import Literal
import httpx
from fastapi import APIRouter,HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel,Field
from llm_service.QA import generate_lawyer_chat
from llm_service.remote import resolve_remote

router=APIRouter(tags=['远程法律助手'])
_slot=threading.BoundedSemaphore(1)

class ClosingAnswer:
    def __init__(self,iterator,release):self.iterator=iterator;self.release=release
    def __aiter__(self):return self
    async def __anext__(self):
        try:return await self.iterator.__anext__()
        except BaseException:
            await self.aclose();raise
    async def aclose(self):
        try:await self.iterator.aclose()
        finally:self.release()

class AnswerResponse(StreamingResponse):
    async def __call__(self,scope,receive,send):
        try:await super().__call__(scope,receive,send)
        finally:await self.body_iterator.aclose()

class ChatMessage(BaseModel):
    role:Literal['user','assistant']
    content:str=Field(min_length=1,max_length=8000)

class QuestionRequest(BaseModel):
    question:str=Field(min_length=1,max_length=8000)
    history:list[ChatMessage]=Field(default_factory=list,max_length=12)

@router.get('/api/ai/status')
async def ai_status():
    public={'ready':False,'provider':'Ubuntu Ollama','model':'qwen3.8:27b','local_model_started':False}
    try:config=resolve_remote()
    except ValueError as exc:return {**public,'status':'not_connected','message':str(exc)}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(4,connect=2),trust_env=False) as client:
            r=await client.get(config.endpoint+'/api/tags');r.raise_for_status()
            model=next((m for m in r.json().get('models',[]) if m.get('name')=='qwen3.8:27b'),None)
        if not model:return {**public,'status':'model_missing','message':'Ubuntu 上尚未找到已配置的模型。'}
        details=model.get('details',{})
        if not str(details.get('parameter_size','')).startswith('27') or details.get('quantization_level')!='Q4_K_M':
            return {**public,'status':'model_mismatch','message':'远程模型与已核验的配置不一致。'}
        return {**public,'ready':True,'status':'ready','transport':config.transport,'message':'Ubuntu 远程服务已连接。'}
    except (httpx.HTTPError,ValueError,TypeError):
        return {**public,'status':'unavailable','message':'远程服务暂未连接，文书填写和生成仍可使用。'}

@router.post('/api/ask')
async def ask(req:QuestionRequest):
    try:resolve_remote()
    except ValueError as exc:raise HTTPException(503,str(exc)) from None
    if not _slot.acquire(blocking=False):raise HTTPException(429,'当前正在回答另一个问题，请稍后重试。')
    history=[m.model_dump() for m in req.history]
    if not history or history[-1]!={'role':'user','content':req.question}:history.append({'role':'user','content':req.question})
    released=False
    def release():
        nonlocal released
        if not released:released=True;_slot.release()
    async def stream():
        try:
            async with aclosing(generate_lawyer_chat(history=history)) as answer:
                async for part in answer:
                    if part:yield part
        except (RuntimeError,ValueError) as exc:yield '\n⚠️ '+str(exc)
        except Exception:yield '\n⚠️ 远程回答中断，请稍后重试。文书生成仍可使用。'
        finally:release()
    return AnswerResponse(ClosingAnswer(stream(),release),media_type='text/plain',
        headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no','X-AI-Provider':'Ubuntu-Ollama'})
