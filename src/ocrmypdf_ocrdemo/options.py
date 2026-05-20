"""CLI / OcrOptions extension for the ocr-demo engine."""

from __future__ import annotations

import argparse
from typing import Annotated

from pydantic import BaseModel, Field, HttpUrl


class OcrdemoOptions(BaseModel):
    """Options for the ocr-demo remote OCR engine."""

    base_url: Annotated[
        HttpUrl | None,
        Field(
            default=None,
            description="Base URL of ocr-demo (e.g. http://127.0.0.1:8000)",
        ),
    ] = None
    timeout: Annotated[
        float,
        Field(ge=1.0, le=3600.0, description="HTTP timeout for each OCR request (seconds)"),
    ] = 300.0
    verify_ssl: Annotated[bool, Field(description="Verify TLS certificates")] = True
    mode: Annotated[str, Field(description="ocr-demo mode query (plain|structured)")] = "plain"
    backend: Annotated[
        str | None,
        Field(default=None, description="ocr-demo backend query (direct|expert|...)"),
    ] = None
    task: Annotated[
        str | None,
        Field(default=None, description="Optional ocr-demo task query parameter"),
    ] = None
    token_limit: Annotated[
        int | None,
        Field(default=None, ge=1, le=128000, description="Optional token_limit query"),
    ] = None
    api_token: Annotated[
        str | None,
        Field(default=None, description="Bearer token sent as Authorization header"),
    ] = None
    use_remote_geometry_hints: Annotated[
        bool,
        Field(
            description=(
                "If true, call /api/ocr in get_orientation/get_deskew when "
                "rotate_pages/deskew are enabled (extra HTTP requests per page)"
            ),
        ),
    ] = True

    @classmethod
    def add_arguments_to_parser(cls, parser: argparse.ArgumentParser) -> None:
        group = parser.add_argument_group(
            "ocr-demo",
            "Remote OCR via ocr-demo HTTP API (POST /api/ocr).",
        )
        group.add_argument(
            "--ocrdemo-base-url",
            default=None,
            dest="ocrdemo_base_url",
            metavar="URL",
            help="Base URL of the running ocr-demo instance (required for --ocr-engine ocrdemo).",
        )
        group.add_argument(
            "--ocrdemo-timeout",
            type=float,
            default=300.0,
            metavar="SEC",
            dest="ocrdemo_timeout",
            help="HTTP timeout in seconds for each OCR request (default: 300).",
        )
        group.add_argument(
            "--ocrdemo-no-verify-ssl",
            action="store_true",
            dest="ocrdemo_no_verify_ssl",
            help="Disable TLS certificate verification (not recommended).",
        )
        group.add_argument(
            "--ocrdemo-mode",
            default="plain",
            dest="ocrdemo_mode",
            help="Value for ocr-demo ?mode= (default: plain).",
        )
        group.add_argument(
            "--ocrdemo-backend",
            default=None,
            dest="ocrdemo_backend",
            help="Optional ocr-demo ?backend= override (e.g. direct, expert).",
        )
        group.add_argument(
            "--ocrdemo-task",
            default=None,
            dest="ocrdemo_task",
            help="Optional ocr-demo ?task= query parameter.",
        )
        group.add_argument(
            "--ocrdemo-token-limit",
            type=int,
            default=None,
            dest="ocrdemo_token_limit",
            metavar="N",
            help="Optional ocr-demo ?token_limit=.",
        )
        group.add_argument(
            "--ocrdemo-api-token",
            default=None,
            dest="ocrdemo_api_token",
            metavar="TOKEN",
            help="If set, send Authorization: Bearer TOKEN on each request.",
        )
        group.add_argument(
            "--ocrdemo-no-remote-geometry-hints",
            action="store_true",
            dest="ocrdemo_no_remote_geometry_hints",
            help=(
                "Do not call ocr-demo for get_orientation/get_deskew (avoids extra "
                "HTTP traffic; use when ocr-demo DESKEW_ENABLED=false and you rely on "
                "local --rotate-pages/--deskew only)."
            ),
        )
