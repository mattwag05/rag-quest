"""File ingestion for lore documents."""

from pathlib import Path
from typing import Optional

import fitz  # pymupdf
from rich.progress import Progress, SpinnerColumn, TextColumn


def ingest_file(filepath: str) -> str:
    """
    Ingest a file and return its text content.
    Supports: .txt, .md, .pdf
    """
    path = Path(filepath)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    if path.suffix.lower() == ".pdf":
        return _ingest_pdf(filepath)
    elif path.suffix.lower() in [".txt", ".md"]:
        return _ingest_text_file(filepath)
    else:
        raise ValueError(
            f"Unsupported file type: {path.suffix}. "
            "Supported: .txt, .md, .pdf"
        )


def _ingest_text_file(filepath: str) -> str:
    """Ingest text or markdown file."""
    return Path(filepath).read_text()


def _ingest_pdf(filepath: str) -> str:
    """Extract text from PDF file."""
    text_parts = []
    with fitz.open(filepath) as doc:
        for page_num, page in enumerate(doc):
            text = page.get_text()
            if text.strip():
                text_parts.append(f"[Page {page_num + 1}]\n{text}")
    return "\n\n".join(text_parts)


def ingest_directory(
    directory: str, pattern: str = "*.{txt,md,pdf}"
) -> dict[str, str]:
    """
    Ingest all supported files in a directory.
    Returns dict of {filename: content}
    """
    dir_path = Path(directory)
    if not dir_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    results = {}
    files = list(dir_path.rglob("*.txt")) + list(
        dir_path.rglob("*.md")
    ) + list(dir_path.rglob("*.pdf"))

    if not files:
        return results

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
    ) as progress:
        task = progress.add_task(
            f"Ingesting {len(files)} files...", total=len(files)
        )

        for filepath in files:
            try:
                content = ingest_file(str(filepath))
                results[filepath.name] = content
                progress.advance(task)
            except Exception as e:
                progress.console.print(
                    f"[red]Error ingesting {filepath.name}: {e}[/red]"
                )
                progress.advance(task)

    return results


def chunk_text(text: str, chunk_size: int = 2000, overlap: int = 200) -> list[str]:
    """Chunk text for efficient RAG processing."""
    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        chunk = text[i : i + chunk_size]
        if chunk.strip():
            chunks.append(chunk)
    return chunks
