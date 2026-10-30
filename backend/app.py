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
from routes.ai import router as ai_router
from system_routes import router as system_router, health
from routes.auth import router as auth_router
from routes.official_collector import router as official_collector_router
from service_capabilities import router as service_capabilities_router
from deployment_app import DESKTOP_LOOPBACK_ORIGIN

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
    allow_origin_regex=DESKTOP_LOOPBACK_ORIGIN,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Guide-Source-ID", "X-Guide-Version", "X-Template-SHA256", "X-Document-Origin", "X-Form-Contract-ID", "Content-Disposition"],
)

app.include_router(zj_la_router, prefix="/api/zhejiang/la", tags=["浙江仲裁"])
app.include_router(zj_el_router, prefix="/api/zhejiang/el", tags=["浙江证据"])
app.include_router(gd_la_router, prefix="/api/guangdong/la", tags=["广东仲裁"])
app.include_router(gd_el_router, prefix="/api/guangdong/el", tags=["广东证据"])
app.include_router(province_documents_router, prefix="/api/province-documents", tags=["各省官方文书"])
app.include_router(portal_reports_router, prefix="/api/portal-reports", tags=["政务门户观察报告"])
app.include_router(regional_guides_router, prefix="/api/regional-guides", tags=["具体地区办理指南"])
app.include_router(platform_router)
app.include_router(ai_router)
app.include_router(system_router)
app.include_router(auth_router)
app.include_router(official_collector_router,prefix='/api/official-collector',tags=['公开指南采集'])
app.include_router(service_capabilities_router,tags=['部署服务'])

@app.middleware("http")
async def security_headers(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    if request.url.path.startswith(("/api/auth/","/api/platform/")):response.headers["Cache-Control"]="no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "camera=(), geolocation=()"
    return response

@app.get("/")
async def root():
    return {"status": "online", "service": "LabourLawyer Platform API", "version": app.version, "docs": "/docs"}

if __name__ == "__main__":
    print("🚀 服务启动中: http://localhost:8000")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
