"""File ingestion for lore documents."""

import hashlib
from pathlib import Path

import fitz  # pymupdf
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn


def ingest_file(filepath: str, profile: str = "balanced") -> str:
    """
    Ingest a file and return its text content.
    Supports: .txt, .md, .pdf
    """
    path = Path(filepath)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    if path.suffix.lower() == ".pdf":
        return _ingest_pdf(filepath, profile)
    elif path.suffix.lower() in [".txt", ".md"]:
        return _ingest_text_file(filepath)
    else:
        raise ValueError(
            f"Unsupported file type: {path.suffix}. " "Supported: .txt, .md, .pdf"
        )


def _ingest_text_file(filepath: str) -> str:
    """Ingest text or markdown file."""
    return Path(filepath).read_text()


def _ingest_pdf(filepath: str, profile: str = "balanced") -> str:
    """Extract text from PDF file with progress reporting."""
    with fitz.open(filepath) as doc:
        total_pages = len(doc)
        text_parts = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        ) as progress:
            task = progress.add_task(
                f"Extracting PDF ({total_pages} pages)...", total=total_pages
            )

            for page_num, page in enumerate(doc):
                text = page.get_text()
                if text.strip():
                    text_parts.append(f"[Page {page_num + 1}]\n{text}")
                progress.advance(task)

        full_text = "\n\n".join(text_parts)

        # Report chunking if large PDF
        if total_pages > 20:
            print(
                f"[*] PDF has {total_pages} pages - applying {profile} chunking strategy"
            )

        return full_text


def ingest_directory(
    directory: str, pattern: str = "*.{txt,md,pdf}", profile: str = "balanced"
) -> dict[str, str]:
    """
    Ingest all supported files in a directory.
    Returns dict of {filename: content}
    """
    dir_path = Path(directory)
    if not dir_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    results = {}
    files = (
        list(dir_path.rglob("*.txt"))
        + list(dir_path.rglob("*.md"))
        + list(dir_path.rglob("*.pdf"))
    )

    if not files:
        return results

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    ) as progress:
        task = progress.add_task(
            f"Ingesting {len(files)} files ({profile} profile)...", total=len(files)
        )

        for filepath in files:
            try:
                content = ingest_file(str(filepath), profile=profile)
                results[filepath.name] = content
                progress.advance(task)
            except Exception as e:
                progress.console.print(
                    f"[red]Error ingesting {filepath.name}: {e}[/red]"
                )
                progress.advance(task)

    return results


def chunk_text(text: str, chunk_size: int = 2000, overlap: int = 200) -> list[str]:
    """Chunk text for efficient RAG processing (legacy function)."""
    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        chunk = text[i : i + chunk_size]
        if chunk.strip():
            chunks.append(chunk)
    return chunks


def get_file_hash(filepath: str) -> str:
    """Get SHA256 hash of a file for change detection."""
    hash_obj = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def should_re_ingest(filepath: str, cache_dir: Path) -> bool:
    """Check if a file has been modified since last ingestion."""
    cache_file = cache_dir / f".{Path(filepath).name}.hash"

    if not cache_file.exists():
        return True

    current_hash = get_file_hash(filepath)
    cached_hash = cache_file.read_text().strip()

    return current_hash != cached_hash


def save_ingest_hash(filepath: str, cache_dir: Path) -> None:
    """Save hash of ingested file for future change detection."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f".{Path(filepath).name}.hash"
    current_hash = get_file_hash(filepath)
    cache_file.write_text(current_hash)
