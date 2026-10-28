from __future__ import annotations

from typing import Any

from .base import SourceAdapter
from ..models import TemplateCandidate


class GuangdongAdapter(SourceAdapter):
    async def discover(self) -> tuple[list[TemplateCandidate], dict[str, Any]]:
        endpoint = self.source.options["material_api"]
        payload = await self.client.request_json(
            "GET",
            endpoint,
            params={"TASK_CODE": self.source.options["task_code"]},
            headers={"Referer": self.source.guide_url},
        )
        materials = payload["AUDIT_MATERIAL"]
        candidates = []
        for selector in self.source.options["templates"]:
            material = materials[selector["material_index"]]
            forms = material.get("FORM_GUID") or []
            if not forms:
                raise ValueError(f"Official API returned no blank form for {selector['document_type']}")
            candidates.append(
                TemplateCandidate(
                    document_type=selector["document_type"],
                    display_name=selector["display_name"],
                    download_url=forms[0]["FILEPATH"],
                    source_url=self.source.guide_url,
                    production_path=selector.get("production_path"),
                )
            )
        return candidates, payload
