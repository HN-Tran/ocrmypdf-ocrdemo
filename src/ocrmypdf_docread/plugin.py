"""OCRmyPDF pluggy hooks and OcrEngine implementation for docread."""

from __future__ import annotations

import html
import logging
from pathlib import Path

from PIL import Image
from pydantic import ValidationError

import ocrmypdf
from ocrmypdf._options import OcrOptions
from ocrmypdf import hookimpl
from ocrmypdf.exceptions import BadArgsError
from ocrmypdf.font import MultiFontManager
from ocrmypdf.fpdf_renderer import Fpdf2PdfRenderer
from ocrmypdf.models.ocr_element import OcrElement
from ocrmypdf.pluginspec import OcrEngine, OrientationConfidence

from ocrmypdf_docread.client import post_ocr_sync
from ocrmypdf_docread.config import build_docread_options_from_extra, get_docread_options
from ocrmypdf_docread.mapping import (
    build_ocr_tree_from_response,
    extract_net_angle_first_page,
    server_angle_to_deskew,
    server_angle_to_orientation,
)

log = logging.getLogger(__name__)


def _ocr_tree_to_hocr(page: OcrElement) -> str:
    """Serialize a single-page ``OcrElement`` tree to minimal hOCR XHTML."""
    if page.bbox is None:
        raise ValueError("page bbox required")
    w = int(page.bbox.right)
    h = int(page.bbox.bottom)
    chunks: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" '
        '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">',
        '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">',
        "<head>",
        "<title>docread</title>",
        '<meta http-equiv="Content-Type" content="text/html;charset=utf-8"/>',
        "<meta name='ocr-system' content='ocrmypdf-docread'/>",
        "</head>",
        "<body>",
        f'<div class="ocr_page" id="page_0" title="bbox 0 0 {w} {h}">',
    ]
    for word in page.words:
        if word.bbox is None:
            continue
        b = word.bbox
        t = html.escape(word.text or "", quote=True)
        chunks.append(
            f'<span class="ocrx_word" title="bbox {int(b.left)} {int(b.top)} '
            f'{int(b.right)} {int(b.bottom)}">{t}</span>'
        )
    chunks.extend(["</div>", "</body>", "</html>"])
    return "\n".join(chunks) + "\n"


class DocreadOcrEngine(OcrEngine):
    """OCR engine that delegates recognition to a docread HTTP service."""

    @staticmethod
    def version() -> str:
        return "docread-remote"

    @staticmethod
    def creator_tag(options: OcrOptions) -> str:
        return "OCRmyPDF fpdf2 + docread HTTP API"

    def __str__(self) -> str:
        return "docread (HTTP)"

    @staticmethod
    def languages(options: OcrOptions) -> set[str]:
        return {"eng"}

    @staticmethod
    def get_orientation(input_file: Path, options: OcrOptions) -> OrientationConfidence:
        oc = get_docread_options(options)
        if not oc.use_remote_geometry_hints:
            return OrientationConfidence(angle=0, confidence=0.0)
        try:
            data = post_ocr_sync(input_file, options)
            net = extract_net_angle_first_page(data)
            return server_angle_to_orientation(net)
        except Exception as exc:  # noqa: BLE001
            log.warning("docread get_orientation failed: %s", exc)
            return OrientationConfidence(angle=0, confidence=0.0)

    @staticmethod
    def get_deskew(input_file: Path, options: OcrOptions) -> float:
        oc = get_docread_options(options)
        if not oc.use_remote_geometry_hints:
            return 0.0
        try:
            data = post_ocr_sync(input_file, options)
            net = extract_net_angle_first_page(data)
            return server_angle_to_deskew(net)
        except Exception as exc:  # noqa: BLE001
            log.warning("docread get_deskew failed: %s", exc)
            return 0.0

    @staticmethod
    def supports_generate_ocr() -> bool:
        return True

    @staticmethod
    def generate_ocr(
        input_file: Path,
        options: OcrOptions,
        page_number: int = 0,
    ) -> tuple[OcrElement, str]:
        data = post_ocr_sync(input_file, options)
        with Image.open(input_file) as im:
            tw, th = im.size
            dpi_info = im.info.get("dpi", (200.0, 200.0))
            if isinstance(dpi_info, tuple):
                dpi = float(dpi_info[0] or dpi_info[1] or 200.0)
            else:
                dpi = float(dpi_info or 200.0)
        idx = page_number
        tree, text = build_ocr_tree_from_response(
            data,
            page_index=idx,
            target_width=tw,
            target_height=th,
            dpi=dpi,
        )
        tree.page_number = page_number
        return tree, text

    @staticmethod
    def generate_hocr(
        input_file: Path,
        output_hocr: Path,
        output_text: Path,
        options: OcrOptions,
    ) -> None:
        tree, text = DocreadOcrEngine.generate_ocr(input_file, options, page_number=0)
        output_hocr.write_text(_ocr_tree_to_hocr(tree), encoding="utf-8")
        output_text.write_text(text, encoding="utf-8")

    @staticmethod
    def generate_pdf(
        input_file: Path,
        output_pdf: Path,
        output_text: Path,
        options: OcrOptions,
    ) -> None:
        tree, text = DocreadOcrEngine.generate_ocr(input_file, options, page_number=0)
        output_text.write_text(text, encoding="utf-8")
        with Image.open(input_file) as im:
            dpi_info = im.info.get("dpi", (200.0, 200.0))
            if isinstance(dpi_info, tuple):
                dpi = float(dpi_info[0] or dpi_info[1] or 200.0)
            else:
                dpi = float(dpi_info or 200.0)
        font_dir = Path(ocrmypdf.__file__).resolve().parent / "data"
        mgr = MultiFontManager(font_dir)
        renderer = Fpdf2PdfRenderer(
            tree,
            dpi=dpi,
            multi_font_manager=mgr,
            invisible_text=True,
        )
        renderer.render(output_pdf)


@hookimpl
def add_options(parser) -> None:
    from ocrmypdf_docread.options import DocreadOptions

    DocreadOptions.add_arguments_to_parser(parser)
    for action in parser._actions:
        if getattr(action, "dest", None) == "ocr_engine" and action.choices is not None:
            ch = list(action.choices)
            if "docread" not in ch:
                ch.append("docread")
            action.choices = ch
            break


@hookimpl
def check_options(options: OcrOptions) -> None:
    if getattr(options, "ocr_engine", None) != "docread":
        return
    try:
        oc = build_docread_options_from_extra(options)
    except ValidationError as exc:
        raise BadArgsError(f"Invalid docread options: {exc}") from exc
    if oc.base_url is None:
        raise BadArgsError(
            "When using --ocr-engine docread, you must set --docread-base-url "
            "to the root URL of a running docread instance (e.g. http://127.0.0.1:8000)."
        )
    options.extra_attrs["_docread"] = oc


@hookimpl
def get_ocr_engine(options: OcrOptions | None) -> DocreadOcrEngine | None:
    if options is None:
        return None
    if getattr(options, "ocr_engine", None) != "docread":
        return None
    return DocreadOcrEngine()
