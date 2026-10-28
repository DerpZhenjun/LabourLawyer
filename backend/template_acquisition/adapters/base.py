from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..http_client import OfficialHttpClient
from ..models import SourceConfig, TemplateCandidate


class SourceAdapter(ABC):
    def __init__(self, source: SourceConfig, client: OfficialHttpClient) -> None:
        self.source = source
        self.client = client

    @abstractmethod
    async def discover(self) -> tuple[list[TemplateCandidate], dict[str, Any]]:
        raise NotImplementedError
