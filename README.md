# ocrmypdf-docread

OCRmyPDF plugin that sends page images to **[docread](https://github.com/HN-Tran/docread)** (`POST /api/ocr`) instead of using Tesseract for recognition. OCRmyPDF still assembles the searchable PDF text layer via its fpdf2 path (`generate_ocr`). Use it from the **CLI** or from stacks such as **paperless-ngx** (see [Paperless-ngx integration](#paperless-ngx-integration)).

Source: [github.com/HN-Tran/ocrmypdf-docread](https://github.com/HN-Tran/ocrmypdf-docread)

## Install

```bash
cd ocrmypdf-docread
uv sync
# or: pip install .
```

OCRmyPDF still expects a **Tesseract** binary to be installed for its built-in plugin’s `check_options` hook, even when you select `--ocr-engine docread` (upstream behaviour). Install `tesseract-ocr` (or equivalent) on the machine that runs `ocrmypdf`.

## Usage

Start **docread**, then:

```bash
ocrmypdf \
  --ocr-engine docread \
  --docread-base-url http://127.0.0.1:8000 \
  --force-ocr \
  input.pdf output.pdf
```

Optional flags:

| Flag | Meaning |
|------|---------|
| `--docread-backend expert` | Passes `backend=` to docread |
| `--docread-mode plain` | Default; matches docread `mode` |
| `--docread-task ocr_text` | Sets `task=` query |
| `--docread-token-limit 8192` | Sets `token_limit=` |
| `--docread-api-token TOKEN` | Sends `Authorization: Bearer …` |
| `--docread-no-verify-ssl` | Disables TLS verification |
| `--docread-no-remote-geometry-hints` | Skips extra HTTP calls for `--rotate-pages` / `--deskew` hints (see below) |

### Word boxes and layout

Best selection alignment comes from docread **`analyzeResult.pages[].words`** with real polygons (for example `OCR_WORD_DETECTOR=doctr` or `paddleocr` on the server). If there are no words, the plugin falls back to **`layout`** region `bbox_2d` + `content`, then to full-page text.

### Rotation / deskew and `DESKEW_ENABLED`

When **`--rotate-pages`** or **`--deskew`** is enabled, OCRmyPDF calls `get_orientation` / `get_deskew` on the raster preview. By default this plugin performs **additional HTTP requests** to docread and maps `analyzeResult.pages[0].angle` (net CCW correction metadata when server deskew is on) into those hooks. This mapping is **heuristic**; for strict alignment when docread uses internal deskew, prefer **`DESKEW_ENABLED=false`** on the server and let OCRmyPDF handle deskew locally, or pass **`--docread-no-remote-geometry-hints`** and manage geometry entirely on the OCRmyPDF side.

## Paperless-ngx integration

[paperless-ngx](https://github.com/paperless-ngx/paperless-ngx) runs OCR through the **OCRmyPDF Python API** (`ocrmypdf.ocr(**kwargs)`), not the `ocrmypdf` shell command. Extra kwargs are merged from **`PAPERLESS_OCR_USER_ARGS`** (JSON). See the upstream docs: [Configuration → `PAPERLESS_OCR_USER_ARGS`](https://docs.paperless-ngx.com/configuration/#PAPERLESS_OCR_USER_ARGS). If OCR settings are overridden in the Paperless **web UI**, those values take precedence over the environment variable.

### Steps

1. **Run docread** on a host/port reachable from the **Paperless worker** (the process that consumes documents — often the `paperless` service in Docker Compose, not only the web container).

2. **Install this package** in the **same Python environment** as Paperless (same venv or extend the official Docker image with `pip install ocrmypdf-docread`). The setuptools entry point registers the plugin with OCRmyPDF; **do not** also pass a duplicate `plugins` list for this module (same rule as [Entry point](#entry-point)).

3. **OCRmyPDF version** — Paperless currently pins **`ocrmypdf~=16.12`** in its own dependencies, while **ocrmypdf-docread** requires **`ocrmypdf>=17`**. Until Paperless bumps that pin, you need a **custom image or dependency override** that installs OCRmyPDF 17+ and re-tests document consumption. After versions align, a normal `pip install ocrmypdf-docread` in the Paperless image is enough.

4. **Keep Tesseract** installed in that image (Paperless / OCRmyPDF still expect it for checks and the rest of the pipeline, even when `ocr_engine` is `docread`).

5. **Set user kwargs** so OCRmyPDF selects this engine and knows the API base URL. Option names use **underscores** (same as OCRmyPDF’s Python API / CLI `dest` names). Minimal example:

   ```json
   {
     "ocr_engine": "docread",
     "docread_base_url": "http://docread:8000"
   }
   ```

   In **Docker Compose**, pass the JSON as a single line (escape quotes as needed for your shell):

   ```yaml
   environment:
     PAPERLESS_OCR_USER_ARGS: '{"ocr_engine":"docread","docread_base_url":"http://docread:8000"}'
   ```

   Optional keys match the CLI flags above, for example `docread_api_token`, `docread_timeout`, `docread_mode`, `docread_backend`, `docread_no_verify_ssl`, `docread_no_remote_geometry_hints`, etc.

6. **Timeouts** — remote OCR can exceed local Tesseract. If tasks abort, increase **`PAPERLESS_TASK_WORKER_TIMEOUT`** and/or `docread_timeout` in user args.

7. **OCR mode** — continue to use Paperless’s **`PAPERLESS_OCR_MODE`** (`skip`, `redo`, `force`, …) as usual; those map to OCRmyPDF’s `skip_text` / `redo_ocr` / `force_ocr` before your user args are merged.

## Tests

```bash
uv sync --extra dev
uv run pytest -q
```

## License

This project is licensed under the **Apache License 2.0** — see [LICENSE](LICENSE) and [NOTICE](NOTICE). [OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF) is a dependency distributed under its own **MPL-2.0** license.

## Entry point

The package registers a setuptools entry point so OCRmyPDF auto-loads this plugin when it is installed in the same environment. **Do not** also pass `--plugin ocrmypdf_docread.plugin` in that case (pluggy would try to register the module twice). Use `--plugin …` only for a one-off path, for example:

```bash
ocrmypdf --plugin /path/to/ocrmypdf_docread/plugin.py ...
```
