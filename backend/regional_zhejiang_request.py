"""Lossless request contract for the slots in the Zhejiang D worker originals."""
from typing import Annotated
from pydantic import BaseModel,Field,field_validator
Text=Annotated[str,Field(max_length=300)]
Copies=str|Annotated[int,Field(strict=True,ge=1,le=30)]|None

class CopyCountModel(BaseModel):
    model_config={'extra':'forbid'}
    copyCount: Copies=''
    @field_validator('copyCount',mode='before')
    @classmethod
    def valid_copies(cls,value):
        if value is None or value=='':return value
        if type(value) is int and 1<=value<=30:return value
        if isinstance(value,str) and value.isascii() and value.isdecimal() and 1<=int(value)<=30:return value
        raise ValueError('副本份数须为1至30的整数或留空')

class ApplicationRequest(CopyCountModel):
    committeeName: Text=''
    applicantName: Text=''
    birthDate: Text=''
    gender: Text=''
    nationality: Text=''
    idNumber: Text=''
    phone: Text=''
    householdType: Text=''
    idAddress: Text=''
    respondentName: Text=''
    socialCreditCode: Text=''
    registeredAddress: Text=''
    mailingAddress: Text=''
    workAddress: Text=''
    legalRepName: Text=''
    legalRepPhone: Text=''
    legalRepPosition: Text=''
    companyContact: Text=''
    companyContactPhone: Text=''
    factsReason: str=Field(default='',max_length=12000)
    applicationDate: Text=''
    requests: list[Annotated[str,Field(max_length=1200)]]=Field(default_factory=list,max_length=4)

class EvidenceItem(BaseModel):
    model_config={'extra':'forbid'}
    name: Text=''
    pageCount: Text=''
    source: Text=''
    purpose: str=Field(default='',max_length=1200)

class EvidenceRequest(CopyCountModel):
    committeeName: Text=''
    caseNumber: Text=''
    submitDate: Text=''
    evidenceList: list[EvidenceItem]=Field(default_factory=list,max_length=40)
