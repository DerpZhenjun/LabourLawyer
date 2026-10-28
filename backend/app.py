import uvicorn
import os
import sys
import uuid
import warnings
from pathlib import Path
from typing import Literal

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / "backend" / ".env")

from platform_api import router as platform_router
from routes.province_documents import router as province_documents_router
from routes.portal_reports import router as portal_reports_router
from routes.regional_guides import router as regional_guides_router
from llm_service.QA import generate_lawyer_chat

try:
    from routes.Zhejiang.la import router as zj_la_router
    from routes.Zhejiang.el import router as zj_el_router
    from routes.Guangdong.la import router as gd_la_router
    from routes.Guangdong.el import router as gd_el_router
except ImportError as e:
    print(f"⚠️ 路由模块导入失败，跳过注册: {e}")
    from fastapi import APIRouter
    zj_la_router = zj_el_router = gd_la_router = gd_el_router = APIRouter()

app = FastAPI(
    title="LabourLawyer Platform API",
    description="劳动争议案件、证据、时效、文书与 AI 辅助能力。",
    version="1.0.0",
)

@app.on_event('startup')
async def load_initial_public_catalogue():
    # Explicit test/candidate stores never receive release data implicitly.
    if not os.getenv('LABOURLAWYER_REGIONAL_DB') and not os.getenv('LABOURLAWYER_DIRECTORY_DB'):
        from public_seed import bootstrap_public_data
        bootstrap_public_data(PROJECT_ROOT)

origins = [item.strip() for item in os.getenv(
    "LABOURLAWYER_CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost,https://localhost,capacitor://localhost"
).split(",") if item.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(zj_la_router, prefix="/api/zhejiang/la", tags=["浙江仲裁"])
app.include_router(zj_el_router, prefix="/api/zhejiang/el", tags=["浙江证据"])
app.include_router(gd_la_router, prefix="/api/guangdong/la", tags=["广东仲裁"])
app.include_router(gd_el_router, prefix="/api/guangdong/el", tags=["广东证据"])
app.include_router(province_documents_router, prefix="/api/province-documents", tags=["各省官方文书"])
app.include_router(portal_reports_router, prefix="/api/portal-reports", tags=["政务门户观察报告"])
app.include_router(regional_guides_router, prefix="/api/regional-guides", tags=["具体地区办理指南"])
app.include_router(platform_router)

@app.middleware("http")
async def security_headers(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "camera=(), geolocation=()"
    return response

@app.get("/")
async def root():
    return {"status": "online", "service": "LabourLawyer Platform API", "version": app.version, "docs": "/docs"}

@app.get("/health", tags=["系统"])
async def health():
    return {"status": "healthy", "service": "api"}

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=8000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=12)

@app.post("/api/ask")
async def qa_endpoint(req: QuestionRequest):
    chat_history = [message.model_dump() for message in req.history]
    if not chat_history or chat_history[-1] != {"role": "user", "content": req.question}:
        chat_history.append({"role": "user", "content": req.question})

    async def generate_stream():
        try:
            async for chunk in generate_lawyer_chat(history=chat_history):
                if chunk:
                    yield chunk
        except Exception as e:
            yield f"⚠️ 服务器内部错误: {str(e)}"

    # ==========================================
    # 核心修复区：加上禁用缓存的 Headers 和事件流 media_type
    # ==========================================
    return StreamingResponse(
        generate_stream(), 
        media_type="text/event-stream",  # 明确告诉前端和服务器：这是连绵不断的事件流
        headers={
            "Cache-Control": "no-cache", # 严禁浏览器缓存
            "Connection": "keep-alive",  # 保持连接不断开
            "X-Accel-Buffering": "no"    # 严禁网关/代理层（如 Nginx）缓冲数据
        }
    )

if __name__ == "__main__":
    print("🚀 服务启动中: http://localhost:8000")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
