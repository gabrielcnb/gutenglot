import logging
import math
from typing import Callable

import fitz  # PyMuPDF

from app.translator import batch_translate

logger = logging.getLogger(__name__)

BATCH_SIZE = 15
MIN_FONT_SIZE = 5


def _insert_fitted_text(page, bbox: "fitz.Rect", text: str, fontsize: float, color, page_idx: int) -> None:
    """Place translated text inside ``bbox``, shrinking the font so it fits.

    ``insert_textbox`` returns a NEGATIVE number when the text doesn't fit, and
    in that case renders nothing, so the original code silently dropped any
    translation longer than its source line. We estimate the wrapped height and
    shrink the font first, then fall back to un-clipped ``insert_text``.
    """
    width = max(bbox.width, 1.0)
    height = max(bbox.height, 1.0)
    size = fontsize
    for _ in range(8):
        text_width = fitz.get_text_length(text, fontname="helv", fontsize=size)
        lines = max(1, math.ceil(text_width / width))
        if lines * size * 1.2 <= height or size <= MIN_FONT_SIZE:
            break
        size *= 0.85

    try:
        rc = page.insert_textbox(bbox, text, fontsize=size, color=color, align=0)
    except Exception:
        rc = -1.0

    if rc is None or rc < 0:
        # Last resort: draw at the baseline without clipping (may overlap, but visible).
        try:
            page.insert_text((bbox.x0, bbox.y1), text, fontsize=min(size, 8), color=color)
        except Exception:
            logger.warning("Failed to insert text on page %d", page_idx + 1)


async def translate_pdf(
    file_bytes: bytes,
    source_lang: str,
    target_lang: str,
    progress_callback: Callable[[int], None] | None = None,
    engine: str = "google",
    glossary: list[str] | None = None,
) -> bytes:
    src_doc = fitz.open(stream=file_bytes, filetype="pdf")
    out_doc = fitz.open()
    total = len(src_doc)

    for page_idx, page in enumerate(src_doc):
        blocks = page.get_text("dict")["blocks"]
        new_page = out_doc.new_page(width=page.rect.width, height=page.rect.height)

        # Copy images from original page
        for img_info in page.get_images(full=True):
            xref = img_info[0]
            img_rect = page.get_image_bbox(img_info)
            try:
                base_image = src_doc.extract_image(xref)
                new_page.insert_image(img_rect, stream=base_image["image"])
            except Exception:
                logger.warning("Failed to copy image xref=%d on page %d", xref, page_idx + 1)

        # Collect all spans for this page
        span_data: list[tuple] = []  # (bbox, fontsize, color, text)
        for block in blocks:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if not text:
                        continue
                    color_int = span.get("color", 0)
                    r = ((color_int >> 16) & 0xFF) / 255
                    g = ((color_int >> 8) & 0xFF) / 255
                    b = (color_int & 0xFF) / 255
                    span_data.append((
                        fitz.Rect(span["bbox"]),
                        span.get("size", 11),
                        (r, g, b),
                        text,
                    ))

        if span_data:
            texts = [s[3] for s in span_data]

            def _on_batch_done(count, _page=page_idx):
                if progress_callback:
                    # Approximate: current page progress + previous pages
                    page_frac = (_page + count / max(len(texts), 1)) / total
                    progress_callback(int(page_frac * 90))

            translations = await batch_translate(
                texts, source_lang, target_lang, batch_size=BATCH_SIZE,
                on_batch_done=_on_batch_done, engine=engine, glossary=glossary,
            )

            for (bbox, fontsize, color, _), translated in zip(span_data, translations):
                if not translated:
                    continue
                _insert_fitted_text(new_page, bbox, translated, fontsize, color, page_idx)
        elif progress_callback:
            progress_callback(int((page_idx + 1) / total * 90))

    out_bytes = out_doc.tobytes()
    src_doc.close()
    out_doc.close()

    if progress_callback:
        progress_callback(100)

    return out_bytes
