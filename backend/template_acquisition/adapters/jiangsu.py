from __future__ import annotations

import re
from typing import Any

from lxml import html

from .base import SourceAdapter
from ..models import TemplateCandidate


class JiangsuAdapter(SourceAdapter):
    async def discover(self) -> tuple[list[TemplateCandidate], dict[str, Any]]:
        page_html = await self.client.request_text("GET", self.source.guide_url)
        page_html = re.sub(r"^\s*<\?xml[^>]+>\s*", "", page_html, flags=re.IGNORECASE)
        document = html.fromstring(page_html)
        blank_forms: dict[str, str] = {}
        rows = document.xpath('//tr[contains(concat(" ", normalize-space(@class), " "), " tsize ")]')
        for row in rows:
            name = "".join(row.xpath(".//p//text()")).strip()
            anchors = row.xpath(
                './/a[contains(concat(" ", normalize-space(@class), " "), " kbbg ")]'
            )
            for anchor in anchors:
                match = re.search(r"downloadClyb\('([^']+)'", anchor.get("onclick", ""))
                if match:
                    blank_forms[name] = match.group(1)
                    break

        candidates = []
        for selector in self.source.options["templates"]:
            material_name = selector["material_name"]
            download_url = blank_forms.get(material_name)
            if not download_url:
                raise ValueError(f"Jiangsu guide returned no blank form for {material_name}")
            candidates.append(
                TemplateCandidate(
                    document_type=selector["document_type"],
                    display_name=material_name,
                    download_url=download_url,
                    source_url=self.source.guide_url,
                    production_path=selector.get("production_path"),
                )
            )
        snapshot = {
            "guide_url": self.source.guide_url,
            "blank_forms": blank_forms,
        }
        return candidates, snapshot
