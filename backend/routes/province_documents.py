from __future__ import annotations

import os
import re
import tempfile

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from province_documents import PROVINCE_DOCUMENTS, get_province_document
from document_forms import province_form, validate_content
from WenShu.generic_template_fill import generate_application, generate_evidence
from api_contracts import ProvinceCatalogResponse


router = APIRouter()


class ApplicationRequest(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)
    committeeName: str = Field(default="", max_length=120)
    applicantName: str = Field(default="", max_length=80)
    birthDate: str = ""
    age: str = Field(default="", max_length=10)
    gender: str = Field(default="", max_length=20)
    nationality: str = Field(default="", max_length=30)
    idNumber: str = Field(default="", max_length=40)
    phone: str = Field(default="", max_length=40)
    householdType: str = Field(default="", max_length=50)
    idAddress: str = Field(default="", max_length=300)
    applicantMailingAddress: str = Field(default="", max_length=300)
    currentAddress: str = Field(default="", max_length=300)
    applicantWorkUnit: str = Field(default="", max_length=200)
    applicantPostalCode: str = Field(default="", max_length=20)
    respondentPostalCode: str = Field(default="", max_length=20)
    nativePlace: str = Field(default="", max_length=100)
    identityDocumentType: str = Field(default="", max_length=50)
    otherDocumentType: str = Field(default="", max_length=50)
    otherDocumentNumber: str = Field(default="", max_length=80)
    acceptMediation: str = Field(default="", max_length=20)
    legalAid: str = Field(default="", max_length=20)
    respondentType: str = Field(default="", max_length=100)
    departmentHead: str = Field(default="", max_length=80)
    departmentHeadPosition: str = Field(default="", max_length=80)
    officeAtRegisteredAddress: str = Field(default="", max_length=20)
    actualOfficeAddress: str = Field(default="", max_length=300)
    occupation: str = Field(default="", max_length=100)
    employmentType: str = Field(default="", max_length=50)
    registeredCapital: str = Field(default="", max_length=100)
    lastWorkingDate: str = ""
    otherNotes: str = Field(default="", max_length=2000)
    respondentName: str = Field(default="", max_length=200)
    socialCreditCode: str = Field(default="", max_length=40)
    registeredAddress: str = Field(default="", max_length=300)
    mailingAddress: str = Field(default="", max_length=300)
    workAddress: str = Field(default="", max_length=300)
    legalRepName: str = Field(default="", max_length=80)
    legalRepPhone: str = Field(default="", max_length=40)
    legalRepPosition: str = Field(default="", max_length=80)
    companyContact: str = Field(default="", max_length=80)
    companyContactPhone: str = Field(default="", max_length=40)
    claimCalculation: str = Field(default="", max_length=2000)
    employmentDate: str = ""
    jobTitle: str = Field(default="", max_length=100)
    signedContract: str = Field(default="", max_length=20)
    contractStartDate: str = ""
    contractEndDate: str = ""
    workSchedule: str = Field(default="", max_length=500)
    attendanceRequired: str = Field(default="", max_length=20)
    attendanceMethod: str = Field(default="", max_length=100)
    salaryPaymentMethod: str = Field(default="", max_length=100)
    salaryReceiptRequired: str = Field(default="", max_length=100)
    startingSalary: str = Field(default="", max_length=100)
    salaryAdjustments: str = Field(default="", max_length=500)
    currentlyEmployed: str = Field(default="", max_length=20)
    departureDate: str = ""
    departureReason: str = Field(default="", max_length=1000)
    averageMonthlySalary: str = Field(default="", max_length=100)
    requests: list[str] = Field(default_factory=list, max_length=10)
    factsReason: str = Field(default="", max_length=12000)
    copyCount: int = Field(default=1, ge=1, le=30)
    applicationDate: str = ""

    @field_validator("requests")
    @classmethod
    def clean_requests(cls, value):
        cleaned = [item.strip() for item in value if item and item.strip()]
        if any(len(item) > 1200 for item in cleaned):
            raise ValueError("单项仲裁请求不能超过1200字")
        return cleaned


class EvidenceItem(BaseModel):
    name: str = Field(default="", max_length=300)
    pageCount: str = Field(default="", max_length=30)
    source: str = Field(default="", max_length=300)
    purpose: str = Field(default="", max_length=1200)
    kind: str = Field(default="", max_length=100)
    originalType: str = Field(default="", max_length=30)
    hasOriginal: str = Field(default="", max_length=20)
    pageRange: str = Field(default="", max_length=50)
    itemCount: str = Field(default="", max_length=30)
    notes: str = Field(default="", max_length=500)


class EvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)
    committeeName: str = Field(default="", max_length=120)
    caseNumber: str = Field(default="", max_length=100)
    copyCount: int = Field(default=2, ge=1, le=30)
    submitterName: str = Field(default="", max_length=80)
    submitDate: str = ""
    evidenceList: list[EvidenceItem] = Field(default_factory=list, max_length=40)


def _remove(path: str):
    try:
        os.remove(path)
    except OSError:
        pass


def _filename(value: str, fallback: str) -> str:
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", value).strip(" .")
    return (safe[:60] or fallback) + ".docx"


def _response(doc, filename: str, background_tasks: BackgroundTasks):
    from pathlib import Path
    output_dir=Path(__file__).resolve().parents[2]/'.runtime'/'generated'
    output_dir.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output_dir,delete=False, suffix=".docx") as tmp:
        doc.save(tmp.name)
        path = tmp.name
    background_tasks.add_task(_remove, path)
    return FileResponse(path, filename=filename, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers={"Cache-Control": "no-store"})


@router.get("", response_model=ProvinceCatalogResponse, response_model_exclude_unset=True)
def list_province_documents():
    return {"items": [{**item, 'forms': province_form(item['slug'])} for item in PROVINCE_DOCUMENTS.values()]}


@router.post("/{slug}/application/generate", response_class=FileResponse, responses={200: {'description': 'Generated Word document', 'content': {'application/vnd.openxmlformats-officedocument.wordprocessingml.document': {'schema': {'type': 'string', 'format': 'binary'}}}}})
def generate_province_application(slug: str, payload: ApplicationRequest, background_tasks: BackgroundTasks):
    try:
        province, path = get_province_document(slug, "application")
        validate_content(province['slug'], payload, 'application')
        doc = generate_application(payload.model_dump(), path)
        return _response(doc, _filename(payload.applicantName, province["name"] + "劳动仲裁申请书"), background_tasks)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"文书生成失败：{exc}") from exc


@router.post("/{slug}/evidence/generate", response_class=FileResponse, responses={200: {'description': 'Generated Word document', 'content': {'application/vnd.openxmlformats-officedocument.wordprocessingml.document': {'schema': {'type': 'string', 'format': 'binary'}}}}})
def generate_province_evidence(slug: str, payload: EvidenceRequest, background_tasks: BackgroundTasks):
    try:
        province, path = get_province_document(slug, "evidence")
        validate_content(province['slug'], payload, 'evidence')
        doc = generate_evidence(payload.model_dump(), path)
        return _response(doc, _filename(province["name"] + "劳动仲裁证据清单", "证据清单"), background_tasks)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"证据清单生成失败：{exc}") from exc
