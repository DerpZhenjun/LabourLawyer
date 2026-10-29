"""Exact JSON slots for Suzhou E own blanks; no field coercion before validation."""
from typing import Annotated, ClassVar
from pydantic import BaseModel, ConfigDict, Field, model_validator
from regional_jiangsu_oct29e import _validate_data

Text = Annotated[str, Field(strict=True, max_length=300)]
LongText = Annotated[str, Field(strict=True, max_length=1200)]
Copies = Annotated[int, Field(strict=True, ge=1, le=30)] | None


def _plain(value):
    """Support already validated nested models without removing raw draft keys."""
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value


class _OwnSlots(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    _slot_kind: ClassVar[str]

    @model_validator(mode='before')
    @classmethod
    def raw_slots(cls, value):
        # The provider validates the uncoerced mapping, including unknown empty
        # keys, Unicode/XML, copy counts and actual calendar dates. Defaults are
        # added only after that check, so a draft cannot lose unsupported keys.
        value = _plain(value)
        if cls._slot_kind == 'evidence_item':
            return _validate_data('evidence', {'evidenceList': [value]})['evidenceList'][0]
        return _validate_data(cls._slot_kind, value)


class ApplicationRequest(_OwnSlots):
    _slot_kind = 'application'
    committeeName: Text = ''
    applicantName: Text = ''
    birthDate: Text = ''
    gender: Text = ''
    idNumber: Text = ''
    idAddress: Text = ''
    otherDocumentType: Text = ''
    otherDocumentNumber: Text = ''
    applicantMailingAddress: Text = ''
    phone: Text = ''
    acceptMediation: Text = ''
    legalAid: Text = ''
    respondentName: Text = ''
    respondentType: Text = ''
    registeredAddress: Text = ''
    socialCreditCode: Text = ''
    legalRepName: Text = ''
    legalRepPosition: Text = ''
    departmentHead: Text = ''
    departmentHeadPosition: Text = ''
    mailingAddress: Text = ''
    companyContact: Text = ''
    companyContactPhone: Text = ''
    requests: list[LongText] = Field(default_factory=list, max_length=4)
    factsReason: str = Field(default='', strict=True, max_length=12000)
    applicationDate: Text = ''
    copyCount: Copies = None
    evidenceCopyCount: Copies = None


class EvidenceItem(_OwnSlots):
    _slot_kind = 'evidence_item'
    name: Text = ''
    source: Text = ''
    purpose: LongText = ''
    originalType: Text = ''
    pageCount: Text = ''


class EvidenceRequest(_OwnSlots):
    _slot_kind = 'evidence'
    committeeName: Text = ''
    caseNumber: Text = ''
    submitDate: Text = ''
    evidenceList: list[EvidenceItem] = Field(default_factory=list, max_length=40)
