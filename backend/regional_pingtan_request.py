"""Strict technical slots inspected in Pingtan's own two official blanks."""
import re
from typing import Annotated, Literal
from pydantic import BaseModel, Field, field_validator

def slot_text(value,capacity):
    if (type(value) is not str or len(value)>capacity or any(not (c=='\n' or 0x20<=ord(c)<=0xd7ff or 0xe000<=ord(c)<=0xfffd or 0x10000<=ord(c)<=0x10ffff) for c in value)):
        raise ValueError('填写内容的文字类型、字符或长度无效')
    return value.strip()

class PingtanApplicationRequest(BaseModel):
    model_config={'extra':'forbid','strict':True}
    applicantName:str=Field(default='',max_length=180)
    agentName:str=Field(default='',max_length=180)
    respondentName:str=Field(default='',max_length=180)
    requests:list[Annotated[str,Field(strict=True,max_length=360)]]=Field(default_factory=list,max_length=3)
    factsReason:str=Field(default='',max_length=2400)

    @field_validator('applicantName','agentName','respondentName','factsReason',mode='before')
    @classmethod
    def own_text(cls,value,info):return slot_text(value,2400 if info.field_name=='factsReason' else 180)

    @field_validator('requests',mode='before')
    @classmethod
    def own_requests(cls,value):
        if type(value) is not list or len(value)>3:raise ValueError('请求项数超出此表格的填写容量')
        return [slot_text(item,360) for item in value]

class PingtanEvidenceItem(BaseModel):
    model_config={'extra':'forbid','strict':True}
    name:str=Field(default='',max_length=60)
    pageCount:str=Field(default='',max_length=4)
    originalType:Literal['','原件','复印件']=''
    purpose:str=Field(default='',max_length=80)
    pageRange:str=Field(default='',max_length=32)

    @field_validator('name','pageCount','originalType','purpose','pageRange',mode='before')
    @classmethod
    def own_text(cls,value,info):
        text=slot_text(value,{'name':60,'pageCount':4,'originalType':4,'purpose':80,'pageRange':32}[info.field_name])
        if info.field_name=='pageCount' and text and not re.fullmatch('[1-9][0-9]{0,3}',text):
            raise ValueError('证据页数请留空或填写1至9999的整数')
        return text

class PingtanEvidenceRequest(BaseModel):
    model_config={'extra':'forbid','strict':True}
    evidenceList:list[PingtanEvidenceItem]=Field(default_factory=lambda:[PingtanEvidenceItem()],max_length=9)
