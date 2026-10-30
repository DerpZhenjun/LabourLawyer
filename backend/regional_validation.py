"""Shared request checks without store access, filling, or model inference.

The route supplies its adapter-specific model factory and contract builder.
Keeping those dependencies explicit avoids importing routes here and preserves
the existing per-template policies and optional-contract legacy behavior.
"""
from pathlib import Path
from typing import Callable

from pydantic import BaseModel, ValidationError

from regional_form_contracts import validate_contract_data
from regional_guides import select_template


class RegionalValidationError(ValueError):
    """A validation failure whose existing HTTP status is retained by routes."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code


def validate_guide_context(
    guide: dict, *, province: str, city: str, district: str,
    source_id: str, version: int, missing_source_status: int = 409,
) -> None:
    """Require the exact requested locality and current source/version pair."""
    if not guide.get('source_id'):
        detail = ('该地区没有已核验文书资料' if missing_source_status == 404
                  else '办理地区或来源版本已改变，请重新查看指南')
        raise RegionalValidationError(missing_source_status, detail)
    requested = (province.strip(), city.strip(), district.strip())
    if tuple(guide.get(k) for k in ('province', 'city', 'district')) != requested:
        raise RegionalValidationError(409, '办理地区不匹配，不能使用邻区文书')
    if guide['source_id'] != source_id or guide.get('version') != version:
        raise RegionalValidationError(409, '办理地区或来源版本已改变，请重新查看指南')


def current_form_contract(
    guide: dict, template: dict, kind: str, *, root: Path,
    contract_builder: Callable,
) -> dict:
    """Use the same source-bound contract construction for reading and filling."""
    try:
        return contract_builder(guide, template, kind, root=root)
    except ValueError as exc:
        raise RegionalValidationError(409, str(exc)) from exc


def select_regional_template(
    guide: dict, template_id: str, kind: str, *, mode: str | None = None,
) -> dict:
    """Resolve one exact template, retaining each endpoint's existing errors.

    A contract read has no supplied filling mode. Generation still uses the
    existing selector's verification, kind and mode checks before own binding.
    Neither path may resolve an ambiguous template ID by picking the first row.
    """
    matches = [t for t in guide.get('templates', []) if t.get('id') == template_id]
    if mode is None:
        if len(matches) != 1:
            raise RegionalValidationError(409, '该地区没有已核验的填写附件')
        return matches[0]
    try:
        template = select_template(guide, template_id, kind, mode)
    except ValueError as exc:
        raise RegionalValidationError(409, str(exc)) from exc
    if len(matches) != 1:
        raise RegionalValidationError(409, '模板与办理地区不匹配')
    return template


def validate_generation_request(
    guide: dict, template: dict, kind: str, data: dict, contract_id: str | None, *,
    root: Path, adapter_checker: Callable, contract_builder: Callable,
    request_model_factory: Callable[[str, str], type[BaseModel]],
) -> tuple[str, BaseModel, str | None]:
    """Apply optional strict field policy before the existing local request model.

    Legacy calls intentionally skip contract construction and field rejection.
    Their model defaults, coercion and handling of extra keys remain unchanged.
    """
    try:
        adapter = adapter_checker(guide, template, kind)
    except ValueError as exc:
        raise RegionalValidationError(409, str(exc)) from exc
    submitted_data = data
    validated_contract_id = None
    if contract_id is not None:
        contract = current_form_contract(
            guide, template, kind, root=root, contract_builder=contract_builder)
        if contract['contract_id'] != contract_id:
            raise RegionalValidationError(409, '填写契约已改变，请重新核对当地文书')
        try:
            submitted_data = validate_contract_data(contract, data)
        except ValueError as exc:
            raise RegionalValidationError(422, str(exc)) from exc
        validated_contract_id = contract['contract_id']
    try:
        model = request_model_factory(adapter, kind).model_validate(submitted_data)
    except ValidationError as exc:
        raise RegionalValidationError(422, '填写内容过长或格式不正确，请缩短后重试') from exc
    return adapter, model, validated_contract_id
