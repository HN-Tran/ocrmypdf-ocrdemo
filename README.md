# ocrmypdf-ocrdemo

Apache-2.0. OCRmyPDF plugin that runs OCR through your **ocr-demo** service (`POST /api/ocr`) instead of Tesseract, and builds a searchable PDF text layer via OCRmyPDF’s fpdf2 path (`generate_ocr`).

## Install

```bash
cd ocrmypdf-ocrdemo
uv sync
# or: pip install .
```

OCRmyPDF still expects a **Tesseract** binary to be installed for its built-in plugin’s `check_options` hook, even when you select `--ocr-engine ocrdemo` (upstream behaviour). Install `tesseract-ocr` (or equivalent) on the machine that runs `ocrmypdf`.

## Usage

Start **ocr-demo**, then:

```bash
ocrmypdf \
  --ocr-engine ocrdemo \
  --ocrdemo-base-url http://127.0.0.1:8000 \
  --force-ocr \
  input.pdf output.pdf
```

Optional flags:

| Flag | Meaning |
|------|---------|
| `--ocrdemo-backend expert` | Passes `backend=` to ocr-demo |
| `--ocrdemo-mode plain` | Default; matches ocr-demo `mode` |
| `--ocrdemo-task ocr_text` | Sets `task=` query |
| `--ocrdemo-token-limit 8192` | Sets `token_limit=` |
| `--ocrdemo-api-token TOKEN` | Sends `Authorization: Bearer …` |
| `--ocrdemo-no-verify-ssl` | Disables TLS verification |
| `--ocrdemo-no-remote-geometry-hints` | Skips extra HTTP calls for `--rotate-pages` / `--deskew` hints (see below) |

### Word boxes and layout

Best selection alignment comes from ocr-demo **`analyzeResult.pages[].words`** with real polygons (for example `OCR_WORD_DETECTOR=doctr` or `paddleocr` on the server). If there are no words, the plugin falls back to **`layout`** region `bbox_2d` + `content`, then to full-page text.

### Rotation / deskew and `DESKEW_ENABLED`

When **`--rotate-pages`** or **`--deskew`** is enabled, OCRmyPDF calls `get_orientation` / `get_deskew` on the raster preview. By default this plugin performs **additional HTTP requests** to ocr-demo and maps `analyzeResult.pages[0].angle` (net CCW correction metadata when server deskew is on) into those hooks. This mapping is **heuristic**; for strict alignment when ocr-demo uses internal deskew, prefer **`DESKEW_ENABLED=false`** on the server and let OCRmyPDF handle deskew locally, or pass **`--ocrdemo-no-remote-geometry-hints`** and manage geometry entirely on the OCRmyPDF side.

## Tests

```bash
uv sync --extra dev
uv run pytest -q
```

## License

This project is licensed under the **Apache License 2.0** — see [LICENSE](LICENSE) and [NOTICE](NOTICE). [OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF) is a dependency distributed under its own **MPL-2.0** license.

## Entry point

The package registers a setuptools entry point so OCRmyPDF auto-loads this plugin when it is installed in the same environment. **Do not** also pass `--plugin ocrmypdf_ocrdemo.plugin` in that case (pluggy would try to register the module twice). Use `--plugin …` only for a one-off path, for example:

```bash
ocrmypdf --plugin /path/to/ocrmypdf_ocrdemo/plugin.py ...
```
