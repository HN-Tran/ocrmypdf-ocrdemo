"""Resolve OcrdemoOptions from OcrOptions.extra_attrs (CLI argparse extras)."""

from __future__ import annotations

from typing import Any

from ocrmypdf._options import OcrOptions
from ocrmypdf.exceptions import BadArgsError

from ocrmypdf_ocrdemo.options import OcrdemoOptions


def get_ocrdemo_options(options: OcrOptions) -> OcrdemoOptions:
    """Return validated ocrdemo options (set by :func:`check_options`)."""
    cached = options.extra_attrs.get("_ocrdemo")
    if isinstance(cached, OcrdemoOptions):
        return cached
    raise BadArgsError(
        "ocr-demo engine options are missing. Ensure --plugin loads ocrmypdf_ocrdemo "
        "and check_options ran successfully."
    )


def build_ocrdemo_options_from_extra(options: OcrOptions) -> OcrdemoOptions:
    """Construct OcrdemoOptions from argparse leftovers in ``extra_attrs``."""
    ea: dict[str, Any] = dict(options.extra_attrs)
    return OcrdemoOptions(
        base_url=ea.get("ocrdemo_base_url"),
        timeout=float(ea.get("ocrdemo_timeout", 300.0)),
        verify_ssl=not bool(ea.get("ocrdemo_no_verify_ssl")),
        mode=str(ea.get("ocrdemo_mode", "plain")),
        backend=ea.get("ocrdemo_backend"),
        task=ea.get("ocrdemo_task"),
        token_limit=ea.get("ocrdemo_token_limit"),
        api_token=ea.get("ocrdemo_api_token"),
        use_remote_geometry_hints=not bool(ea.get("ocrdemo_no_remote_geometry_hints")),
    )
