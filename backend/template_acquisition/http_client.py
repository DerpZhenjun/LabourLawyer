from __future__ import annotations

import httpx
import ssl
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .security import MAX_DOWNLOAD_BYTES, validate_download_url


class OfficialHttpClient:
    def __init__(self, allowed_domains: tuple[str, ...], legacy_tls: bool = False) -> None:
        self.allowed_domains = allowed_domains
        verify: bool | ssl.SSLContext = True
        if legacy_tls:
            context = ssl.create_default_context()
            context.options |= 0x4  # SSL_OP_LEGACY_SERVER_CONNECT for older government servers.
            verify = context
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(60, connect=20),
            follow_redirects=False,
            headers={"User-Agent": "Partlawyer-Template-Monitor/1.0 (+official-template-monitor)"},
            verify=verify,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self._client.aclose()

    async def _send(self, method: str, url: str, *, stream: bool = False, **kwargs) -> httpx.Response:
        request = self._client.build_request(method, url, **kwargs)
        for _ in range(10):
            validate_download_url(str(request.url), self.allowed_domains)
            response = await self._client.send(request, stream=stream, follow_redirects=False)
            if not response.is_redirect:
                validate_download_url(str(response.url), self.allowed_domains)
                return response
            next_request = response.next_request
            await response.aclose()
            if next_request is None:
                raise ValueError("Redirect response did not provide a destination")
            validate_download_url(str(next_request.url), self.allowed_domains)
            request = next_request
        raise ValueError("Too many redirects while retrieving official content")

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def request_json(self, method: str, url: str, **kwargs):
        response = await self._send(method, url, **kwargs)
        try:
            response.raise_for_status()
            return response.json()
        finally:
            await response.aclose()

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def request_text(self, method: str, url: str, **kwargs) -> str:
        response = await self._send(method, url, **kwargs)
        try:
            response.raise_for_status()
            return response.text
        finally:
            await response.aclose()

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def download(self, url: str) -> bytes:
        response = await self._send("GET", url, stream=True)
        try:
            response.raise_for_status()
            declared = int(response.headers.get("content-length", "0") or 0)
            if declared > MAX_DOWNLOAD_BYTES:
                raise ValueError("Server declared a file larger than the configured limit")
            chunks: list[bytes] = []
            size = 0
            async for chunk in response.aiter_bytes():
                size += len(chunk)
                if size > MAX_DOWNLOAD_BYTES:
                    raise ValueError("Download exceeded the configured limit")
                chunks.append(chunk)
            return b"".join(chunks)
        finally:
            await response.aclose()
