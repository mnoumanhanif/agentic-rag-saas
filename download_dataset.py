#!/usr/bin/env python3
"""
PDF Dataset Downloader for RAG Chatbot Testing.

Downloads, validates, and organizes a collection of publicly available PDF
documents for testing the Agentic RAG chatbot pipeline.

Usage:
    python download_dataset.py [--output-dir DIR] [--sources FILE] [--retry N]

The script reads PDF sources from list_of_pdf_sources.json, downloads each file,
validates it as a proper text-based PDF, and organizes it into category folders.
"""

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests
from pypdf import PdfReader
from pypdf.errors import PdfReadError

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SOURCES = SCRIPT_DIR / "list_of_pdf_sources.json"
DEFAULT_OUTPUT = SCRIPT_DIR / "rag_dataset"
REQUEST_TIMEOUT = 60  # seconds
MAX_FILE_SIZE_MB = 200
USER_AGENT = (
    "Mozilla/5.0 (compatible; RAGDatasetDownloader/1.0; "
    "+https://github.com/k190462/rag-chatbot)"
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class DownloadResult:
    """Result of a single PDF download attempt."""

    name: str
    category: str
    url: str
    success: bool
    path: Optional[str] = None
    pages: int = 0
    size_bytes: int = 0
    error: Optional[str] = None
    has_text: bool = False


@dataclass
class DatasetReport:
    """Aggregated report of the download session."""

    total_attempted: int = 0
    successful: int = 0
    failed: int = 0
    total_pages: int = 0
    total_size_bytes: int = 0
    results: list = field(default_factory=list)
    categories: dict = field(default_factory=dict)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


# ---------------------------------------------------------------------------
# URL validation
# ---------------------------------------------------------------------------
def is_valid_url(url: str) -> bool:
    """Validate that a URL is well-formed and uses HTTP(S)."""
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# PDF validation
# ---------------------------------------------------------------------------
def validate_pdf(filepath: str) -> tuple[bool, int, bool, str]:
    """Validate a downloaded file is a real, text-based PDF.

    Returns:
        Tuple of (is_valid, page_count, has_extractable_text, error_message).
    """
    try:
        # Check the file starts with the PDF magic bytes
        with open(filepath, "rb") as f:
            header = f.read(5)
        if header != b"%PDF-":
            return False, 0, False, "File does not start with PDF header"

        reader = PdfReader(filepath)
        num_pages = len(reader.pages)
        if num_pages == 0:
            return False, 0, False, "PDF has zero pages"

        # Check if at least one page has extractable text
        has_text = False
        for page in reader.pages[:5]:  # Check first 5 pages
            text = page.extract_text() or ""
            if len(text.strip()) > 50:
                has_text = True
                break

        if not has_text:
            logger.warning(
                "PDF %s has no extractable text in first 5 pages", filepath
            )
            return True, num_pages, False, "No extractable text found"

        return True, num_pages, True, ""

    except PdfReadError as e:
        return False, 0, False, f"Corrupted PDF: {e}"
    except Exception as e:
        return False, 0, False, f"Validation error: {e}"


# ---------------------------------------------------------------------------
# Download a single PDF
# ---------------------------------------------------------------------------
def download_pdf(
    url: str,
    dest_path: str,
    max_retries: int = 3,
) -> tuple[bool, str]:
    """Download a PDF from *url* and save it to *dest_path*.

    Returns:
        Tuple of (success, error_message).
    """
    headers = {"User-Agent": USER_AGENT}

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
                stream=True,
                allow_redirects=True,
            )
            response.raise_for_status()

            # Verify content type if provided
            content_type = response.headers.get("Content-Type", "").lower()
            if content_type and "pdf" not in content_type and "octet-stream" not in content_type:
                # Some servers don't set the right content type; allow if the
                # body still looks like a PDF.
                first_bytes = next(response.iter_content(chunk_size=5), b"")
                if first_bytes != b"%PDF-":
                    return False, f"Unexpected content type: {content_type}"
                # If it looks like a PDF, write the bytes we already read.
                with open(dest_path, "wb") as f:
                    f.write(first_bytes)
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            else:
                with open(dest_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

            # Size sanity check
            file_size = os.path.getsize(dest_path)
            if file_size < 1024:  # Less than 1 KB is suspicious
                os.remove(dest_path)
                return False, f"File too small ({file_size} bytes)"
            if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
                os.remove(dest_path)
                return False, f"File exceeds {MAX_FILE_SIZE_MB}MB limit"

            return True, ""

        except requests.exceptions.RequestException as e:
            if attempt < max_retries:
                wait = 2 ** attempt
                logger.info(
                    "  Retry %d/%d after %ds: %s", attempt, max_retries, wait, e
                )
                time.sleep(wait)
            else:
                return False, f"Download failed after {max_retries} attempts: {e}"

    return False, "Unknown download error"


# ---------------------------------------------------------------------------
# Load sources JSON
# ---------------------------------------------------------------------------
def load_sources(sources_path: str) -> dict:
    """Load and parse the PDF sources JSON file."""
    with open(sources_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Main download orchestrator
# ---------------------------------------------------------------------------
def download_dataset(
    sources_path: str,
    output_dir: str,
    max_retries: int = 3,
) -> DatasetReport:
    """Download the full PDF dataset.

    Args:
        sources_path: Path to list_of_pdf_sources.json.
        output_dir: Root directory for the dataset.
        max_retries: Number of retries per download.

    Returns:
        A DatasetReport summarising the session.
    """
    report = DatasetReport(start_time=datetime.now())
    data = load_sources(sources_path)

    categories = data.get("categories", {})
    for category_name, category_info in categories.items():
        cat_dir = os.path.join(output_dir, category_name)
        os.makedirs(cat_dir, exist_ok=True)

        sources = category_info.get("sources", [])
        logger.info(
            "=== Category: %s (%d files) ===", category_name, len(sources)
        )
        report.categories[category_name] = {"total": len(sources), "success": 0, "failed": 0}

        for source in sources:
            report.total_attempted += 1
            name = source["name"]
            url = source["url"]
            title = source.get("title", name)
            dest_path = os.path.join(cat_dir, name)

            logger.info("[%d] Downloading: %s", report.total_attempted, title)
            logger.info("    URL: %s", url)

            # URL validation
            if not is_valid_url(url):
                result = DownloadResult(
                    name=name, category=category_name, url=url,
                    success=False, error="Invalid URL",
                )
                report.results.append(result)
                report.failed += 1
                report.categories[category_name]["failed"] += 1
                logger.error("    ✗ Invalid URL: %s", url)
                continue

            # Download
            ok, err = download_pdf(url, dest_path, max_retries)
            if not ok:
                result = DownloadResult(
                    name=name, category=category_name, url=url,
                    success=False, error=err,
                )
                report.results.append(result)
                report.failed += 1
                report.categories[category_name]["failed"] += 1
                logger.error("    ✗ Download failed: %s", err)
                continue

            # Validate
            valid, pages, has_text, val_err = validate_pdf(dest_path)
            if not valid:
                os.remove(dest_path)
                result = DownloadResult(
                    name=name, category=category_name, url=url,
                    success=False, error=val_err,
                )
                report.results.append(result)
                report.failed += 1
                report.categories[category_name]["failed"] += 1
                logger.error("    ✗ Validation failed: %s", val_err)
                continue

            size = os.path.getsize(dest_path)
            result = DownloadResult(
                name=name, category=category_name, url=url,
                success=True, path=dest_path, pages=pages,
                size_bytes=size, has_text=has_text,
            )
            report.results.append(result)
            report.successful += 1
            report.total_pages += pages
            report.total_size_bytes += size
            report.categories[category_name]["success"] += 1
            logger.info(
                "    ✓ Saved: %s (%d pages, %.1f MB, text=%s)",
                name, pages, size / (1024 * 1024), has_text,
            )

    report.end_time = datetime.now()
    return report


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------
def print_report(report: DatasetReport) -> None:
    """Print a human-readable summary of the download session."""
    duration = (report.end_time - report.start_time).total_seconds() if report.end_time and report.start_time else 0

    print("\n" + "=" * 60)
    print("  PDF DATASET DOWNLOAD REPORT")
    print("=" * 60)
    print(f"  Date:          {report.start_time:%Y-%m-%d %H:%M:%S}" if report.start_time else "")
    print(f"  Duration:      {duration:.1f}s")
    print(f"  Total files:   {report.total_attempted}")
    print(f"  Successful:    {report.successful}")
    print(f"  Failed:        {report.failed}")
    print(f"  Total pages:   {report.total_pages}")
    print(f"  Total size:    {report.total_size_bytes / (1024 * 1024):.1f} MB")
    print()

    print("  Category breakdown:")
    for cat, stats in report.categories.items():
        print(f"    {cat}: {stats['success']}/{stats['total']} downloaded")
    print()

    if report.failed > 0:
        print("  Failed downloads:")
        for r in report.results:
            if not r.success:
                print(f"    ✗ {r.name}: {r.error}")
        print()

    print("  Successful downloads:")
    for r in report.results:
        if r.success:
            text_status = "✓ text" if r.has_text else "⚠ no text"
            print(f"    ✓ {r.name} ({r.pages} pages, {text_status})")
    print("=" * 60)


def save_report(report: DatasetReport, output_dir: str) -> None:
    """Save the download report as JSON."""
    report_path = os.path.join(output_dir, "download_report.json")
    report_data = {
        "timestamp": report.start_time.isoformat() if report.start_time else None,
        "summary": {
            "total_attempted": report.total_attempted,
            "successful": report.successful,
            "failed": report.failed,
            "total_pages": report.total_pages,
            "total_size_mb": round(report.total_size_bytes / (1024 * 1024), 2),
        },
        "categories": report.categories,
        "files": [
            {
                "name": r.name,
                "category": r.category,
                "url": r.url,
                "success": r.success,
                "pages": r.pages,
                "size_bytes": r.size_bytes,
                "has_text": r.has_text,
                "error": r.error,
            }
            for r in report.results
        ],
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)
    logger.info("Report saved to %s", report_path)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download and validate a PDF dataset for RAG chatbot testing."
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT),
        help="Root directory for the dataset (default: rag_dataset/)",
    )
    parser.add_argument(
        "--sources",
        default=str(DEFAULT_SOURCES),
        help="Path to the PDF sources JSON file",
    )
    parser.add_argument(
        "--retry",
        type=int,
        default=3,
        help="Number of download retries per file (default: 3)",
    )
    args = parser.parse_args()

    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)

    logger.info("Starting PDF dataset download")
    logger.info("Sources: %s", args.sources)
    logger.info("Output:  %s", args.output_dir)

    report = download_dataset(args.sources, args.output_dir, args.retry)

    print_report(report)
    save_report(report, args.output_dir)

    # Exit with non-zero if no files were downloaded
    if report.successful == 0:
        logger.error("No files were downloaded successfully.")
        sys.exit(1)

    logger.info("Dataset ready at %s", args.output_dir)


if __name__ == "__main__":
    main()
