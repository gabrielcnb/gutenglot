"""
Lightweight safety checks for untrusted uploads.

Covered here:
- Decompression-bomb guard: an EPUB/MOBI/AZW3 is a ZIP; a tiny upload can expand
  to hundreds of MB and OOM the worker. We reject archives whose declared
  uncompressed size, or whose compression ratio, is implausible.
- Output filename sanitization: strip path separators and control characters so
  the suggested download name (Content-Disposition) is always plain and safe.
"""

import io
import re
import zipfile
from pathlib import Path

# Max total uncompressed bytes we'll allow a ZIP-based book to expand to.
# Real books are well under this; legitimate big EPUBs with images still pass.
MAX_UNCOMPRESSED = 400 * 1024 * 1024  # 400 MB
# Reject absurd compression ratios (classic zip-bomb signature).
MAX_COMPRESSION_RATIO = 200


class UnsafeFileError(Exception):
    """Raised when an upload looks like a decompression bomb or is malformed."""


def check_zip_safety(data: bytes) -> None:
    """Raise UnsafeFileError if a ZIP-based upload looks like a bomb.

    No-op for non-ZIP data (e.g. PDFs) — those are size-capped on read and
    parsed by PyMuPDF, which streams rather than inflating an archive.
    """
    if not data[:2] == b"PK":
        return  # not a ZIP container; nothing to check here
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            total = 0
            for info in zf.infolist():
                total += info.file_size
                if total > MAX_UNCOMPRESSED:
                    raise UnsafeFileError(
                        "This file expands to too much data and was rejected."
                    )
                # Per-entry ratio check catches a single highly-compressed member.
                if info.compress_size > 0:
                    ratio = info.file_size / info.compress_size
                    if ratio > MAX_COMPRESSION_RATIO and info.file_size > 1_000_000:
                        raise UnsafeFileError(
                            "This file expands to too much data and was rejected."
                        )
    except zipfile.BadZipFile:
        # Not a valid zip — let the downstream parser produce the corrupt-file
        # error so the user gets a clear, format-specific message.
        return


_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._ \-]")


def safe_output_stem(filename: str) -> str:
    """Return a clean filename stem: no directories, no control chars."""
    stem = Path(filename or "book").stem
    stem = _SAFE_NAME_RE.sub("_", stem).strip() or "book"
    return stem[:100]
