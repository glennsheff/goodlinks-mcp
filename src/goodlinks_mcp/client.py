"""HTTP client for the GoodLinks local API."""

from __future__ import annotations

import os
from typing import Any

import httpx


DEFAULT_BASE_URL = "http://localhost:9428/api/v1"


class GoodLinksError(Exception):
    """Raised when the GoodLinks API returns an error or is unreachable."""


class GoodLinksClient:
    """Thin async wrapper around the GoodLinks local HTTP API."""

    def __init__(
        self,
        token: str | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._token = token or os.environ.get("GOODLINKS_API_TOKEN", "").strip()
        if not self._token:
            raise GoodLinksError(
                "GOODLINKS_API_TOKEN is not set. "
                "Get a token from GoodLinks → Settings → API and export it as "
                "GOODLINKS_API_TOKEN."
            )

        self._base_url = (
            base_url
            or os.environ.get("GOODLINKS_API_BASE_URL", "").strip()
            or DEFAULT_BASE_URL
        ).rstrip("/")
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        expect_json: bool = True,
    ) -> Any:
        url = f"{self._base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.request(
                    method,
                    url,
                    params=_clean_params(params),
                    json=json_body,
                    headers=self._headers(),
                )
        except httpx.ConnectError as exc:
            raise GoodLinksError(
                "Could not connect to GoodLinks. Check that the GoodLinks app "
                "is running and that the API is enabled in Settings → API."
            ) from exc
        except httpx.TimeoutException as exc:
            raise GoodLinksError(
                f"Request to GoodLinks timed out after {self._timeout}s."
            ) from exc

        if response.status_code == 401:
            raise GoodLinksError(
                "GoodLinks rejected the API token (401 Unauthorized). "
                "Verify GOODLINKS_API_TOKEN matches Settings → API and "
                "restart the MCP server after changing it."
            )
        if response.status_code == 404:
            raise GoodLinksError(
                f"Not found: {method} {path} returned 404. "
                "The resource may not exist or the list name may be invalid."
            )
        if response.status_code >= 400:
            detail = _extract_error_detail(response)
            raise GoodLinksError(
                f"GoodLinks API error {response.status_code}: {detail}"
            )

        if not expect_json:
            return response.text
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    # --- Links ---------------------------------------------------------

    async def get_link(self, link_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/links/{link_id}")

    async def get_link_by_url(self, url: str) -> dict[str, Any]:
        return await self._request("GET", "/links", params={"url": url})

    async def get_current_link(self) -> dict[str, Any]:
        return await self._request("GET", "/links/current")

    async def search_links(self, params: dict[str, Any]) -> dict[str, Any]:
        return await self._request("GET", "/links", params=params)

    async def save_link(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST /links — create or upsert by URL."""
        return await self._request("POST", "/links", json_body=payload)

    async def get_list(self, list_name: str, params: dict[str, Any]) -> dict[str, Any]:
        return await self._request("GET", f"/lists/{list_name}", params=params)

    async def get_link_content(self, link_id: str, fmt: str) -> str:
        return await self._request(
            "GET",
            f"/links/{link_id}/content",
            params={"format": fmt},
            expect_json=False,
        )

    # --- Lists & tags --------------------------------------------------

    async def get_lists(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/lists")

    async def get_tags(self) -> list[str]:
        return await self._request("GET", "/tags")

    # --- Highlights ----------------------------------------------------

    async def search_highlights(self, params: dict[str, Any]) -> dict[str, Any]:
        return await self._request("GET", "/highlights", params=params)

    async def export_link_highlights(self, link_id: str) -> str:
        return await self._request(
            "GET",
            f"/links/{link_id}/highlights/export",
            expect_json=False,
        )


def _clean_params(params: dict[str, Any] | None) -> dict[str, Any] | None:
    """Drop None values; httpx keeps them as 'key=' otherwise."""
    if not params:
        return None
    return {k: v for k, v in params.items() if v is not None}


def _extract_error_detail(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text or response.reason_phrase
    msg = body.get("error") or response.reason_phrase
    details = body.get("details")
    if details:
        return f"{msg} ({details})"
    return msg
