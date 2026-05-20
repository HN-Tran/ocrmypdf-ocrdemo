"""HTTP client for docread /api/ocr."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import httpx

from ocrmypdf._options import OcrOptions

from ocrmypdf_docread.config import get_docread_options

log = logging.getLogger(__name__)


def post_ocr_sync(
    image_path: Path,
    options: OcrOptions,
) -> dict[str, Any]:
    """POST a single page image to docread and return JSON."""
    oc = get_docread_options(options)
    base = str(oc.base_url).rstrip("/") if oc.base_url else ""
    if not base:
        raise ValueError("docread base_url is not configured")
    url = f"{base}/api/ocr"
    params: dict[str, str | int] = {"mode": oc.mode}
    if oc.backend:
        params["backend"] = oc.backend
    if oc.task:
        params["task"] = oc.task
    if oc.token_limit is not None:
        params["token_limit"] = int(oc.token_limit)

    headers: dict[str, str] = {"Content-Type": "application/octet-stream"}
    if oc.api_token:
        headers["Authorization"] = f"Bearer {oc.api_token}"

    data = image_path.read_bytes()
    with httpx.Client(timeout=oc.timeout, verify=oc.verify_ssl) as client:
        resp = client.post(url, content=data, params=params, headers=headers)
    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        log.error("docread HTTP %s: %s", exc.response.status_code, exc.response.text[:500])
        raise
    return resp.json()
