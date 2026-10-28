from __future__ import annotations

import json
from pathlib import Path

from .models import SourceConfig


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = PROJECT_ROOT / "config" / "template_sources.json"


def load_sources(path: Path = DEFAULT_REGISTRY) -> list[SourceConfig]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    sources = []
    for item in raw["sources"]:
        if item.get("enabled", True):
            sources.append(
                SourceConfig(
                    province=item["province"],
                    adapter=item["adapter"],
                    guide_url=item["guide_url"],
                    allowed_domains=tuple(item["allowed_domains"]),
                    options=item.get("options", {}),
                )
            )
    return sources


def select_sources(provinces: list[str] | None, path: Path = DEFAULT_REGISTRY) -> list[SourceConfig]:
    sources = load_sources(path)
    if not provinces:
        return sources
    wanted = {value.casefold() for value in provinces}
    selected = [source for source in sources if source.province.casefold() in wanted]
    missing = sorted(wanted - {source.province.casefold() for source in selected})
    if missing:
        raise ValueError(f"Unknown or disabled province: {', '.join(missing)}")
    return selected
