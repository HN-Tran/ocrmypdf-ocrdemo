"""Resolve DocreadOptions from OcrOptions.extra_attrs (CLI argparse extras)."""

from __future__ import annotations

from typing import Any

from ocrmypdf._options import OcrOptions
from ocrmypdf.exceptions import BadArgsError

from ocrmypdf_docread.options import DocreadOptions


def get_docread_options(options: OcrOptions) -> DocreadOptions:
    """Return validated docread options (set by :func:`check_options`)."""
    cached = options.extra_attrs.get("_docread")
    if isinstance(cached, DocreadOptions):
        return cached
    raise BadArgsError(
        "docread engine options are missing. Ensure --plugin loads ocrmypdf_docread "
        "and check_options ran successfully."
    )


def build_docread_options_from_extra(options: OcrOptions) -> DocreadOptions:
    """Construct DocreadOptions from argparse leftovers in ``extra_attrs``."""
    ea: dict[str, Any] = dict(options.extra_attrs)
    return DocreadOptions(
        base_url=ea.get("docread_base_url"),
        timeout=float(ea.get("docread_timeout", 300.0)),
        verify_ssl=not bool(ea.get("docread_no_verify_ssl")),
        mode=str(ea.get("docread_mode", "plain")),
        backend=ea.get("docread_backend"),
        task=ea.get("docread_task"),
        token_limit=ea.get("docread_token_limit"),
        api_token=ea.get("docread_api_token"),
        use_remote_geometry_hints=not bool(ea.get("docread_no_remote_geometry_hints")),
    )
