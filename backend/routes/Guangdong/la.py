"""Compatibility endpoint sharing the audited province template generator."""
from fastapi import APIRouter, BackgroundTasks
from routes.province_documents import ApplicationRequest, generate_province_application
router=APIRouter()
GuangdongApplicationRequest = ApplicationRequest

@router.post('/generate')
async def generate_guangdong_application(req: ApplicationRequest, background_tasks: BackgroundTasks):
    return generate_province_application('guangdong',req,background_tasks)
