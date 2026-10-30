"""Export actual stable route metadata without app startup, databases or AI IO."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from routes.ai import router as ai_router
from routes.province_documents import router as province_router
from system_routes import router as system_router
from routes.auth import router as auth_router


def stable_openapi():
    application = FastAPI(title='LabourLawyer Stable Client API', version='1.0.0')
    application.include_router(system_router)
    application.include_router(auth_router)
    application.include_router(ai_router)
    application.include_router(province_router, prefix='/api/province-documents')
    return application.openapi()


if __name__ == '__main__':
    print(json.dumps(stable_openapi(), ensure_ascii=False, sort_keys=True, indent=2))
