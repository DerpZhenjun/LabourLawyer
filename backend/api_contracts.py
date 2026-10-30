"""Stable wire models. Dynamic locality forms remain adapter-owned contracts."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ExtensibleResponse(BaseModel):
    # Public metadata grows independently; never discard existing source fields.
    model_config = ConfigDict(extra='allow')


class HealthResponse(BaseModel):
    status: str
    service: str


class AIStatusResponse(ExtensibleResponse):
    ready: bool
    provider: str
    model: str
    local_model_started: bool
    message: str | None = None
    status: str | None = None
    transport: str | None = None


class ChatMessage(BaseModel):
    role: Literal['user', 'assistant']
    content: str = Field(min_length=1, max_length=8000)


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=8000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=12)


class DocumentFieldDefinition(ExtensibleResponse):
    label: str
    type: str
    maxLength: int
    options: list[str] = Field(default_factory=list)
    rows: int = 1
    placeholder: str = ''


class FormLimits(BaseModel):
    maxRequests: int
    requestLength: int
    factsLength: int
    maxEvidence: int


class ProvinceForms(ExtensibleResponse):
    version: int
    applicationFields: list[str]
    evidenceFields: list[str]
    limits: FormLimits
    fieldDefinitions: dict[str, DocumentFieldDefinition]


class ProvinceCatalogEntry(ExtensibleResponse):
    slug: str
    name: str
    source_url: str
    documents: dict[str, str | None]
    forms: ProvinceForms | None = None


class ProvinceCatalogResponse(BaseModel):
    items: list[ProvinceCatalogEntry]
