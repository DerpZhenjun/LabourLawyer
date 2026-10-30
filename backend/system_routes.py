"""Dependency-free health route shared by the application and schema export."""
from fastapi import APIRouter
from api_contracts import HealthResponse

router = APIRouter()


@router.get('/health', tags=['系统'], response_model=HealthResponse)
async def health():
    return {'status': 'healthy', 'service': 'api'}
