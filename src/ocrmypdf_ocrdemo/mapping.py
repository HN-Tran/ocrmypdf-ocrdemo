"""Map ocr-demo JSON into OCRmyPDF OcrElement trees and orientation hints."""

from __future__ import annotations

import math
from typing import Any, cast

from ocrmypdf.hocrtransform import BoundingBox, OcrClass, OcrElement
from ocrmypdf.pluginspec import OrientationConfidence


def decompose_server_net_ccw(net: float) -> tuple[int, float]:
    """Split ocr-demo ``page_info.angle`` (net CCW correction) into cardinal + fine.

    Returns ``(cardinal_ccw, fine_ccw)`` where ``cardinal_ccw`` is a multiple of
    90 in ``{0, 90, 180, 270}`` and ``fine_ccw`` is the residual in roughly
    ``(-45, 45]`` (best-effort).
    """
    n = float(net)
    if not math.isfinite(n) or abs(n) < 1e-9:
        return 0, 0.0
    k = int(round(n / 90.0))
    cardinal = (k * 90) % 360
    fine = n - k * 90
    # nudge fine into (-45, 45] by shifting cardinal
    while fine > 45.0:
        fine -= 90.0
        cardinal = (cardinal + 90) % 360
    while fine < -45.0:
        fine += 90.0
        cardinal = (cardinal - 90) % 360
    return int(cardinal) % 360, float(fine)


def server_angle_to_orientation(net_ccw: float) -> OrientationConfidence:
    """Map server net CCW correction to OCRmyPDF :class:`OrientationConfidence`.

    This is a **heuristic**: ocr-demo stores total **CCW** correction applied during
    preprocessing, while OCRmyPDF's rotate-pages path expects the same convention as
    Tesseract OSD (see OCRmyPDF docs). When in doubt, disable ``--rotate-pages`` or
    set ``--ocrdemo-no-remote-geometry-hints`` and rely on OCRmyPDF-only geometry.
    """
    cardinal_ccw, _fine = decompose_server_net_ccw(net_ccw)
    if cardinal_ccw == 0:
        return OrientationConfidence(angle=0, confidence=0.0)
    return OrientationConfidence(angle=int(cardinal_ccw) % 360, confidence=15.0)


def server_angle_to_deskew(net_ccw: float) -> float:
    """Return fine CCW skew (Pillow ``rotate`` degrees) from server net correction."""
    _cardinal, fine = decompose_server_net_ccw(net_ccw)
    return fine


def _polygon_to_bbox(poly: list[float]) -> BoundingBox | None:
    if len(poly) < 8:
        return None
    xs = poly[0::2]
    ys = poly[1::2]
    return BoundingBox(
        left=min(xs),
        top=min(ys),
        right=max(xs),
        bottom=max(ys),
    )


def _bbox_2d_to_bbox(b: list[float]) -> BoundingBox | None:
    if len(b) < 4:
        return None
    x0, y0, x1, y1 = float(b[0]), float(b[1]), float(b[2]), float(b[3])
    return BoundingBox(
        left=min(x0, x1),
        top=min(y0, y1),
        right=max(x0, x1),
        bottom=max(y0, y1),
    )


def _scale_bbox(
    bbox: BoundingBox,
    *,
    src_w: float,
    src_h: float,
    dst_w: float,
    dst_h: float,
) -> BoundingBox:
    sx = dst_w / src_w if src_w else 1.0
    sy = dst_h / src_h if src_h else 1.0
    return BoundingBox(
        left=bbox.left * sx,
        top=bbox.top * sy,
        right=bbox.right * sx,
        bottom=bbox.bottom * sy,
    )


def _regions_for_layout(
    layout: list[dict[str, Any]] | None, page_index: int
) -> list[dict[str, Any]]:
    if not layout:
        return []
    for item in layout:
        if isinstance(item, dict):
            pn = item.get("page_number")
            if pn is not None and int(pn) == page_index + 1:
                return cast(list[dict[str, Any]], item.get("regions") or [])
    if page_index < len(layout):
        return cast(list[dict[str, Any]], layout[page_index].get("regions") or [])
    return []


def build_ocr_tree_from_response(
    data: dict[str, Any],
    *,
    page_index: int,
    target_width: int,
    target_height: int,
    dpi: float,
) -> tuple[OcrElement, str]:
    """Build an ``OcrElement`` page tree and plain text from ocr-demo JSON."""
    text = str(data.get("text") or "")
    analyze = cast(dict[str, Any], data.get("analyzeResult") or {})
    pages = cast(list[dict[str, Any]], analyze.get("pages") or [])
    idx = min(max(0, page_index), max(0, len(pages) - 1)) if pages else 0
    page = pages[idx] if pages else {}

    src_w = float(page.get("width") or target_width)
    src_h = float(page.get("height") or target_height)
    if src_w <= 0:
        src_w = float(target_width)
    if src_h <= 0:
        src_h = float(target_height)

    page_bbox = BoundingBox(0.0, 0.0, float(target_width), float(target_height))

    words: list[dict[str, Any]] = cast(list[dict[str, Any]], page.get("words") or [])
    line_children: list[OcrElement] = []

    if words:
        for w in words:
            content = str(w.get("content") or w.get("text") or "").strip()
            poly = w.get("polygon")
            bbox: BoundingBox | None = None
            if isinstance(poly, list):
                try:
                    floats = [float(x) for x in poly]
                    bbox = _polygon_to_bbox(floats)
                except (TypeError, ValueError):
                    bbox = None
            if bbox is None:
                continue
            bbox = _scale_bbox(bbox, src_w=src_w, src_h=src_h, dst_w=target_width, dst_h=target_height)
            word_el = OcrElement(ocr_class=OcrClass.WORD, bbox=bbox, text=content)
            line_el = OcrElement(
                ocr_class=OcrClass.LINE,
                bbox=bbox,
                children=[word_el],
            )
            line_children.append(line_el)
    else:
        layout = cast(list[dict[str, Any]] | None, data.get("layout"))
        regions = _regions_for_layout(layout, idx)
        for reg in regions:
            content = str(reg.get("content") or "").strip()
            bb = reg.get("bbox_2d")
            bbox = _bbox_2d_to_bbox(cast(list[float], bb)) if isinstance(bb, list) else None
            if bbox is None or not content:
                continue
            bbox = _scale_bbox(
                bbox, src_w=src_w, src_h=src_h, dst_w=target_width, dst_h=target_height
            )
            word_el = OcrElement(ocr_class=OcrClass.WORD, bbox=bbox, text=content)
            line_el = OcrElement(ocr_class=OcrClass.LINE, bbox=bbox, children=[word_el])
            line_children.append(line_el)

    if not line_children:
        # Searchable full-page fallback (poor selection geometry)
        fb = page_bbox
        word_el = OcrElement(ocr_class=OcrClass.WORD, bbox=fb, text=text or " ")
        line_children.append(
            OcrElement(ocr_class=OcrClass.LINE, bbox=fb, children=[word_el]),
        )

    paragraph = OcrElement(ocr_class=OcrClass.PARAGRAPH, bbox=page_bbox, children=line_children)
    page_el = OcrElement(
        ocr_class=OcrClass.PAGE,
        bbox=page_bbox,
        children=[paragraph],
        page_number=page_index,
        dpi=dpi,
    )
    return page_el, text


def extract_net_angle_first_page(data: dict[str, Any]) -> float:
    """Read ``analyzeResult.pages[0].angle`` from an ocr-demo response."""
    analyze = cast(dict[str, Any], data.get("analyzeResult") or {})
    pages = cast(list[dict[str, Any]], analyze.get("pages") or [])
    if not pages:
        return 0.0
    ang = pages[0].get("angle")
    if isinstance(ang, (int, float)):
        return float(ang)
    return 0.0
