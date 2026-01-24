"""File utility functions for PDF discovery."""

from pathlib import Path


def find_pdf_files(path: Path) -> list[Path]:
    """Find PDF files in the given path.

    Args:
        path: File or directory path.

    Returns:
        List of PDF file paths, sorted alphabetically.
    """
    if path.is_file():
        if path.suffix.lower() == ".pdf":
            return [path]
        return []

    pdf_files = list(path.glob("**/*.pdf"))
    return sorted(pdf_files)
