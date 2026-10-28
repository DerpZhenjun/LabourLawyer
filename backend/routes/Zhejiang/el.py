"""Compatibility endpoint sharing the audited province template generator."""
from fastapi import APIRouter, BackgroundTasks
from routes.province_documents import EvidenceItem as _EvidenceItem, EvidenceRequest as _EvidenceRequest, generate_province_evidence
router=APIRouter()
EvidenceItem = _EvidenceItem
EvidenceRequest = _EvidenceRequest

@router.post('/generate')
async def generate_zhejiang_evidence(req: EvidenceRequest, background_tasks: BackgroundTasks):
    return generate_province_evidence('zhejiang',req,background_tasks)
