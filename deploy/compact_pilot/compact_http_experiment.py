"""Private FastAPI TestClient surface for the independently reviewed candidate design."""

from typing import Annotated, Literal
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field

from compact_renderer_experiment import render

Kind = Literal['application', 'evidence']
MIME = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
SANITIZED_ORIGIN = 'official-blank-metadata-sanitized-layout'
SANITIZED_GENERATION = 'official-blank-metadata-sanitized-filled'


class Scope(BaseModel):
    model_config = ConfigDict(extra='forbid')

    province: str = Field(min_length=1, max_length=30)
    city: str = Field(min_length=1, max_length=80)
    district: str = Field(min_length=1, max_length=80)
    source_id: str = Field(min_length=1, max_length=64)
    version: int = Field(ge=1)
    case_scope: str | None = Field(default=None, max_length=32)


class FormScope(Scope):
    template_id: str = Field(min_length=1, max_length=64)
    kind: Kind


class FormQuery(FormScope):
    xlsx: bool = False


class Generation(FormScope):
    version: int = Field(ge=1, strict=True)
    contract_id: str = Field(pattern=r'^[0-9a-f]{64}$')
    mode: Literal['blank', 'reference_adaptation']
    data: dict


def create_test_app(proof, bindings, *, layout_hash=None):
    registry = {}
    for binding in bindings:
        contract, _ = proof.read(binding)
        context = contract['context']
        key = (context['province'], context['city'], context['district'], binding['template_id'])
        if key in registry or context.get('case_scope') is not None:
            raise ValueError('Ambiguous or unsupported pilot contract')
        registry[key] = binding.copy()
    if len(registry) != 36:
        raise ValueError('Incomplete locked cohort')

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_request: Request, _error: RequestValidationError):
        return JSONResponse({'detail': '请求字段缺失或不符合格式。'}, status_code=422,
                            headers={'Cache-Control': 'no-store'})

    def admitted(scope, template_id, kind=None):
        binding = registry.get((scope.province, scope.city, scope.district, template_id))
        if (binding is None or scope.case_scope is not None
                or scope.source_id != binding['source_id'] or scope.version != binding['version']
                or (kind is not None and binding['kind'] != kind)):
            raise HTTPException(409, '地区、来源或文书范围不匹配。')
        return binding

    def checked_read(binding):
        try:
            return proof.read(binding)
        except ValueError as exc:
            raise HTTPException(409, '原件或合约校验未通过。') from exc

    prefix = '/api/regional-guides'

    @app.get(prefix + '/templates/{template_id}')
    def download(template_id: str, scope: Annotated[Scope, Query()]):
        binding = admitted(scope, template_id)
        _, body = checked_read(binding)
        if layout_hash is not None:
            return _document(body, scope.district, binding, '依据官方原件制作的空白填写版', {
                'X-Template-SHA256': layout_hash(binding['original_sha256']),
                'X-Official-Original-SHA256': binding['original_sha256'],
                'X-Document-Origin': SANITIZED_ORIGIN,
            })
        return _document(body, scope.district, binding, '官方空白原件', {
            'X-Template-SHA256': binding['original_sha256'],
        })

    @app.get(prefix + '/form-contract')
    def contract(scope: Annotated[FormQuery, Query()]):
        fields, _ = checked_read(admitted(scope, scope.template_id, scope.kind))
        return JSONResponse(fields, headers={'Cache-Control': 'no-store'})

    @app.post(prefix + '/generate')
    def generate(payload: Generation):
        binding = admitted(payload, payload.template_id, payload.kind)
        if payload.mode != 'blank' or payload.contract_id != binding['contract_id']:
            raise HTTPException(409, '填写模式或字段合约不匹配。')
        checked_read(binding)
        try:
            body = render(proof, binding, payload.data)
        except ValueError as exc:
            raise HTTPException(422, '填写内容不符合当前文书合约。') from exc
        headers = {
            'X-Document-Origin': 'official-blank-filled',
            'X-Form-Contract-ID': binding['contract_id'],
        }
        suffix = '官方空白表格填写'
        if layout_hash is not None:
            suffix = '依据官方空白表版式填写'
            headers.update({'X-Document-Origin': SANITIZED_GENERATION, 'X-Document-Layout-Origin': SANITIZED_ORIGIN,
                            'X-Official-Original-SHA256': binding['original_sha256'],
                            'X-Template-SHA256': layout_hash(binding['original_sha256'])})
        return _document(body, payload.district, binding, suffix, headers)

    return app


def _document(body, district, binding, suffix, headers):
    title = '申请书' if binding['kind'] == 'application' else '证据清单'
    filename = quote(f'{district}{title}-{suffix}.docx', safe='')
    return Response(body, media_type=MIME, headers={
        'Content-Disposition': f"attachment; filename*=UTF-8''{filename}",
        'Cache-Control': 'no-store',
        'X-Guide-Source-ID': binding['source_id'],
        'X-Guide-Version': str(binding['version']),
        **headers,
    })
