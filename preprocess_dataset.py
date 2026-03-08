#!/usr/bin/env python3
"""
PDF Dataset Preprocessor for RAG Chatbot Testing.

Extracts text from downloaded PDFs, splits documents into chunks, and stores
metadata.  The output is a JSON-lines file that can be fed directly into the
RAG ingestion pipeline for indexing.

Usage:
    python preprocess_dataset.py [--dataset-dir DIR] [--output FILE]
                                  [--chunk-size N] [--chunk-overlap N]
"""

import argparse
import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from pypdf import PdfReader
from pypdf.errors import PdfReadError

# ---------------------------------------------------------------------------
# Logging
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
DEFAULT_DATASET = SCRIPT_DIR / "rag_dataset"
DEFAULT_OUTPUT = SCRIPT_DIR / "rag_dataset" / "preprocessed_dataset.jsonl"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class DocumentChunk:
    """A single chunk of extracted text with metadata.

    Note: page_start and page_end represent the full document's page range,
    not the specific pages this chunk was extracted from.
    """

    text: str
    source_file: str
    title: str
    category: str
    page_start: int  # First page of the source document
    page_end: int  # Last page of the source document
    chunk_index: int
    total_chunks: int
    char_count: int
    word_count: int


@dataclass
class DocumentMetadata:
    """Metadata about a processed PDF."""

    filename: str
    category: str
    pages: int
    total_chars: int
    total_words: int
    chunks: int
    file_size_bytes: int


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------
def extract_text_from_pdf(filepath: str) -> list[tuple[int, str]]:
    """Extract text from each page of a PDF.

    Returns:
        List of (page_number, page_text) tuples.
    """
    pages: list[tuple[int, str]] = []
    try:
        reader = PdfReader(filepath)
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                pages.append((i + 1, text))
    except PdfReadError as e:
        logger.error("Cannot read %s: %s", filepath, e)
    except Exception as e:
        logger.error("Error extracting text from %s: %s", filepath, e)
    return pages


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------
def chunk_text(
    full_text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[str]:
    """Split text into overlapping chunks.

    Uses a simple character-based splitter that respects paragraph boundaries
    where possible.
    """
    if not full_text.strip():
        return []

    separators = ["\n\n", "\n", ". ", " "]
    chunks: list[str] = []
    start = 0
    text_len = len(full_text)

    while start < text_len:
        end = start + chunk_size

        # If we haven't reached the end, try to break at a separator
        if end < text_len:
            best_break = -1
            for sep in separators:
                # Search backwards from end for the separator
                idx = full_text.rfind(sep, start, end)
                if idx > start:
                    best_break = idx + len(sep)
                    break
            if best_break > start:
                end = best_break

        chunk = full_text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move start forward, respecting overlap
        start = max(start + 1, end - chunk_overlap)

    return chunks


# ---------------------------------------------------------------------------
# Process a single PDF
# ---------------------------------------------------------------------------
def process_pdf(
    filepath: str,
    category: str,
    chunk_size: int,
    chunk_overlap: int,
) -> tuple[list[DocumentChunk], Optional[DocumentMetadata]]:
    """Process a PDF file into chunks with metadata."""
    filename = os.path.basename(filepath)
    title = filename.replace(".pdf", "").replace("_", " ").title()

    pages = extract_text_from_pdf(filepath)
    if not pages:
        logger.warning("No text extracted from %s", filepath)
        return [], None

    # Combine all page text
    full_text = "\n\n".join(text for _, text in pages)
    text_chunks = chunk_text(full_text, chunk_size, chunk_overlap)

    if not text_chunks:
        return [], None

    doc_chunks: list[DocumentChunk] = []
    for i, chunk_text_str in enumerate(text_chunks):
        doc_chunks.append(
            DocumentChunk(
                text=chunk_text_str,
                source_file=filename,
                title=title,
                category=category,
                page_start=pages[0][0],
                page_end=pages[-1][0],
                chunk_index=i,
                total_chunks=len(text_chunks),
                char_count=len(chunk_text_str),
                word_count=len(chunk_text_str.split()),
            )
        )

    metadata = DocumentMetadata(
        filename=filename,
        category=category,
        pages=len(pages),
        total_chars=len(full_text),
        total_words=len(full_text.split()),
        chunks=len(text_chunks),
        file_size_bytes=os.path.getsize(filepath),
    )

    return doc_chunks, metadata


# ---------------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------------
def preprocess_dataset(
    dataset_dir: str,
    output_path: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> None:
    """Walk the dataset directory and preprocess all PDFs."""
    all_chunks: list[DocumentChunk] = []
    all_metadata: list[DocumentMetadata] = []

    dataset_path = Path(dataset_dir)
    categories = [
        d for d in sorted(dataset_path.iterdir())
        if d.is_dir() and not d.name.startswith(".")
    ]

    for cat_dir in categories:
        category = cat_dir.name
        pdf_files = sorted(cat_dir.glob("*.pdf"))

        if not pdf_files:
            continue

        logger.info("Processing category: %s (%d files)", category, len(pdf_files))

        for pdf_path in pdf_files:
            logger.info("  Processing: %s", pdf_path.name)
            chunks, meta = process_pdf(
                str(pdf_path), category, chunk_size, chunk_overlap
            )
            if chunks:
                all_chunks.extend(chunks)
                logger.info(
                    "    → %d chunks, %d pages", len(chunks), meta.pages if meta else 0
                )
            if meta:
                all_metadata.append(meta)

    # Save chunks as JSON Lines
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")
    logger.info("Saved %d chunks to %s", len(all_chunks), output_path)

    # Save metadata summary
    meta_path = output_path.replace(".jsonl", "_metadata.json")
    summary = {
        "timestamp": datetime.now().isoformat(),
        "settings": {
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
        },
        "totals": {
            "documents": len(all_metadata),
            "chunks": len(all_chunks),
            "total_pages": sum(m.pages for m in all_metadata),
            "total_words": sum(m.total_words for m in all_metadata),
        },
        "documents": [asdict(m) for m in all_metadata],
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    logger.info("Saved metadata to %s", meta_path)

    # Print summary
    print("\n" + "=" * 60)
    print("  PREPROCESSING REPORT")
    print("=" * 60)
    print(f"  Documents processed:  {len(all_metadata)}")
    print(f"  Total chunks:         {len(all_chunks)}")
    print(f"  Total pages:          {sum(m.pages for m in all_metadata)}")
    print(f"  Total words:          {sum(m.total_words for m in all_metadata):,}")
    print(f"  Avg chunk size:       {sum(c.char_count for c in all_chunks) // max(len(all_chunks), 1)} chars")
    print()
    for meta in all_metadata:
        print(f"    {meta.filename}: {meta.pages} pages → {meta.chunks} chunks")
    print("=" * 60)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Preprocess PDF dataset for RAG chatbot indexing."
    )
    parser.add_argument(
        "--dataset-dir",
        default=str(DEFAULT_DATASET),
        help="Path to the dataset directory (default: rag_dataset/)",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output JSONL file path",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1000,
        help="Chunk size in characters (default: 1000)",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=200,
        help="Overlap between chunks in characters (default: 200)",
    )
    args = parser.parse_args()

    preprocess_dataset(
        args.dataset_dir, args.output, args.chunk_size, args.chunk_overlap
    )


if __name__ == "__main__":
    main()
