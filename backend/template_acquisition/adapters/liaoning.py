from __future__ import annotations

import re
from typing import Any

from lxml import html

from .base import SourceAdapter
from ..models import TemplateCandidate


class LiaoningAdapter(SourceAdapter):
    async def discover(self) -> tuple[list[TemplateCandidate], dict[str, Any]]:
        page_html = await self.client.request_text("GET", self.source.guide_url)
        page_html = re.sub(r"^\s*<\?xml[^>]+>\s*", "", page_html, flags=re.IGNORECASE)
        document = html.fromstring(page_html)
        links = {}
        for anchor in document.xpath("//a[@href]"):
            label = "".join(anchor.xpath(".//text()")).strip()
            href = anchor.get("href", "")
            if label and href:
                links[label] = href

        candidates = []
        for selector in self.source.options["templates"]:
            match = next(
                ((label, href) for label, href in links.items() if selector["link_text_contains"] in label),
                None,
            )
            if not match:
                raise ValueError(f"Liaoning guide returned no official file for {selector['display_name']}")
            _, download_url = match
            candidates.append(
                TemplateCandidate(
                    document_type=selector["document_type"],
                    display_name=selector["display_name"],
                    download_url=download_url,
                    source_url=self.source.guide_url,
                    production_path=selector.get("production_path"),
                    file_format=selector.get("file_format", "docx"),
                    original_path=selector.get("original_path"),
                )
            )
        return candidates, {
            "guide_url": self.source.guide_url,
            "official_files": {item.display_name: item.download_url for item in candidates},
            "notice": "The provincial guide provides an application form but no evidence-list blank form.",
        }
