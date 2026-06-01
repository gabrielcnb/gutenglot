# Gutenglot

> Translate any book into any language. Covers preserved, ready for any e-reader.

*Gutenberg gave us the printed book — Gutenglot gives it every language.*

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?logo=fastapi)
![Docker](https://img.shields.io/badge/Docker-ready-blue?logo=docker)
![License](https://img.shields.io/badge/License-MIT-yellow)

**Live:** [gutenglot.onrender.com](https://gutenglot.onrender.com)

---

## Features

- **EPUB & PDF translation** — upload either format, get it back translated
- **MOBI & AZW3 support** — converted to EPUB first (via Calibre), then translated
- **Format conversion** — EPUB ↔ PDF (Calibre when available, smart fallback)
- **Bilingual mode** — original and translation side by side in the same file
- **Cover preserved** — the book cover stays intact in every output
- **Glossary** — protect names and terms from being translated
- **100+ languages** — powered by Google Translate / MyMemory, no API key needed
- **E-reader-ready** — EPUB output works on Kindle, Kobo, and any e-reader

## How to Use

1. Open the app and **upload** your EPUB, PDF, MOBI or AZW3 (drag & drop or click)
2. Choose the **Translate** or **Convert Format** tab
3. Select source and target languages
4. Optionally enable **Bilingual mode** or add a **glossary**
5. Click **Translate Book** and wait for the download

### Sending to a Kindle

Amazon's *Send to Kindle* accepts EPUB directly:

- [Send to Kindle](https://www.amazon.com/sendtokindle) (web upload)
- Email the EPUB to your Kindle address
- Transfer via USB

---

## Self-hosting

### Docker (recommended)

```bash
git clone https://github.com/gabrielcnb/gutenglot
cd gutenglot
docker-compose up --build
```

Open **http://localhost:8000**.

### Without Docker

```bash
git clone https://github.com/gabrielcnb/gutenglot
cd gutenglot
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

> Note: MOBI/AZW3 input and the highest-quality EPUB↔PDF conversion require [Calibre](https://calibre-ebook.com/) installed. Without it, EPUB↔PDF falls back to a simpler text-only converter.

### Configuration

| Env var | Default | Purpose |
|---------|---------|---------|
| `CORS_ORIGINS` | `https://gutenglot.onrender.com,https://gutenglot.com,…,http://localhost:8000` | Comma-separated list of allowed origins |
| `DEBUG` | `false` | Set `true` for auto-reload in development |

---

## Architecture

```
Browser -> FastAPI
  |
  |-- EPUB translation: ebooklib -> parse HTML blocks -> batch translate -> repack
  |-- PDF translation:  PyMuPDF -> extract text spans -> translate -> overlay
  |-- MOBI/AZW3:        Calibre -> EPUB -> translate
  |-- EPUB <-> PDF:     Calibre (or paginated fallback)
  |
  +-- Google Translate / MyMemory (deep-translator, batched, cached)
```

| Component | Library |
|-----------|---------|
| Web framework | FastAPI + Uvicorn |
| EPUB processing | ebooklib + BeautifulSoup4 |
| PDF processing | PyMuPDF (fitz) |
| Translation | deep-translator (Google Translate, MyMemory fallback) |
| Format conversion | Calibre CLI (fallback: PyMuPDF) |
| Caching | Disk-backed dictionary cache |

### Performance

- EPUB chapters and PDF pages translated in parallel (`asyncio.gather`)
- Batch translation: ~12–15 blocks per request
- Disk-backed translation cache for repeated phrases
- Rate limiting: 5 jobs/hour per IP, limited concurrency

### Limitations

- Max file size: 50 MB
- **Scanned/image-only PDFs are not supported** — there is no OCR; pages without an embedded text layer come out blank. Use an EPUB or a text-based PDF.
- **PDF output in non-Latin scripts** (Chinese, Arabic, Hindi, Cyrillic, etc.) may render poorly — the PDF overlay uses a Latin font. For those languages, prefer **EPUB output**, which lets the e-reader pick the font.
- Translated text that is longer than the original may overflow or clip in PDF output.
- Complex multi-column PDF layouts may shift slightly.
- Free tier (Render): cold starts after inactivity (~30s on first request).

---

## Deploy on Render

1. Fork this repo
2. Create a new **Web Service** on [Render](https://render.com)
3. Select the **Docker** runtime (the included `render.yaml` configures it)
4. Deploy

To use a custom domain, add it under **Settings → Custom Domains** and point your DNS at Render, then add the domain to `CORS_ORIGINS`.

---

## Support

If this tool is useful to you, consider supporting development:

[Buy me a coffee on Ko-fi](https://ko-fi.com/gabrielcnb)

---

## Copyright & responsible use

Gutenglot is a tool for translating books **you have the right to translate** —
books you own, books you wrote, or works in the public domain. You are solely
responsible for ensuring you have the rights to any file you upload, and for
complying with the copyright laws that apply to you. The maintainers do not host,
store, or distribute any uploaded book: files are processed transiently and
deleted automatically (within 1 hour on the hosted instance).

The software is provided "as is", without warranty of any kind (see License).

---

## License

MIT
