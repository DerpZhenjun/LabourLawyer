from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

from .base import SourceAdapter
from ..models import TemplateCandidate


class ZhejiangAdapter(SourceAdapter):
    async def discover(self) -> tuple[list[TemplateCandidate], dict[str, Any]]:
        endpoint = self.source.options["material_api"]
        local_code = self.source.options["local_inner_code"]
        payload = await self.client.request_json(
            "POST",
            endpoint,
            data={"localInnerCode": local_code},
            headers={"Referer": self.source.guide_url},
        )
        materials = payload["data"]["DATAAREA"]["MATERIALS"]["MATERIAL"]
        candidates = []
        for selector in self.source.options["templates"]:
            material = materials[selector["material_index"]]
            relative_url = material["EMPTYTABLE"]["FILEURL"]
            if not relative_url:
                raise ValueError(f"Official API returned no blank form for {selector['document_type']}")
            candidates.append(
                TemplateCandidate(
                    document_type=selector["document_type"],
                    display_name=selector["display_name"],
                    download_url=urljoin("https://portal.zjzwfw.gov.cn", relative_url),
                    source_url=self.source.guide_url,
                    production_path=selector.get("production_path"),
                )
            )
        return candidates, payload
