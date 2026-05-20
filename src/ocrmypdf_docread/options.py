"""CLI / OcrOptions extension for the docread engine."""

from __future__ import annotations

import argparse
from typing import Annotated

from pydantic import BaseModel, Field, HttpUrl


class DocreadOptions(BaseModel):
    """Options for the docread remote OCR engine."""

    base_url: Annotated[
        HttpUrl | None,
        Field(
            default=None,
            description="Base URL of docread (e.g. http://127.0.0.1:8000)",
        ),
    ] = None
    timeout: Annotated[
        float,
        Field(ge=1.0, le=3600.0, description="HTTP timeout for each OCR request (seconds)"),
    ] = 300.0
    verify_ssl: Annotated[bool, Field(description="Verify TLS certificates")] = True
    mode: Annotated[str, Field(description="docread mode query (plain|structured)")] = "plain"
    backend: Annotated[
        str | None,
        Field(default=None, description="docread backend query (direct|expert|...)"),
    ] = None
    task: Annotated[
        str | None,
        Field(default=None, description="Optional docread task query parameter"),
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
            "docread",
            "Remote OCR via docread HTTP API (POST /api/ocr).",
        )
        group.add_argument(
            "--docread-base-url",
            default=None,
            dest="docread_base_url",
            metavar="URL",
            help="Base URL of the running docread instance (required for --ocr-engine docread).",
        )
        group.add_argument(
            "--docread-timeout",
            type=float,
            default=300.0,
            metavar="SEC",
            dest="docread_timeout",
            help="HTTP timeout in seconds for each OCR request (default: 300).",
        )
        group.add_argument(
            "--docread-no-verify-ssl",
            action="store_true",
            dest="docread_no_verify_ssl",
            help="Disable TLS certificate verification (not recommended).",
        )
        group.add_argument(
            "--docread-mode",
            default="plain",
            dest="docread_mode",
            help="Value for docread ?mode= (default: plain).",
        )
        group.add_argument(
            "--docread-backend",
            default=None,
            dest="docread_backend",
            help="Optional docread ?backend= override (e.g. direct, expert).",
        )
        group.add_argument(
            "--docread-task",
            default=None,
            dest="docread_task",
            help="Optional docread ?task= query parameter.",
        )
        group.add_argument(
            "--docread-token-limit",
            type=int,
            default=None,
            dest="docread_token_limit",
            metavar="N",
            help="Optional docread ?token_limit=.",
        )
        group.add_argument(
            "--docread-api-token",
            default=None,
            dest="docread_api_token",
            metavar="TOKEN",
            help="If set, send Authorization: Bearer TOKEN on each request.",
        )
        group.add_argument(
            "--docread-no-remote-geometry-hints",
            action="store_true",
            dest="docread_no_remote_geometry_hints",
            help=(
                "Do not call docread for get_orientation/get_deskew (avoids extra "
                "HTTP traffic; use when docread DESKEW_ENABLED=false and you rely on "
                "local --rotate-pages/--deskew only)."
            ),
        )
