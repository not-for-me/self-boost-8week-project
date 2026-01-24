"""PDF utility functions for page extraction and image conversion."""

from pathlib import Path

import click
from pypdf import PdfReader

from fin_stat_table_detector.exporters import PageDimensions


def get_pdf_page_info(pdf_path: Path) -> list[tuple[float, float]]:
    """Get page dimensions from PDF using pypdf.

    Args:
        pdf_path: Path to PDF file.

    Returns:
        List of (width, height) tuples for each page in points.
    """
    reader = PdfReader(pdf_path)
    page_dims = []
    for page in reader.pages:
        media_box = page.mediabox
        page_dims.append((float(media_box.width), float(media_box.height)))
    return page_dims


def convert_pdf_to_images(
    pdf_path: Path,
    images_dir: Path,
    dpi: int = 150,
) -> list[tuple[int, Path, PageDimensions]]:
    """Convert PDF pages to images.

    Args:
        pdf_path: Path to the PDF file.
        images_dir: Directory to save images.
        dpi: Image resolution (dots per inch).

    Returns:
        List of tuples: (page_number, image_path, page_dimensions).

    Raises:
        ClickException: If pdf2image is not installed.
    """
    try:
        from pdf2image import convert_from_path
    except ImportError:
        raise click.ClickException(
            "pdf2image is required for image conversion. Install with: uv add pdf2image"
        )

    images_dir.mkdir(parents=True, exist_ok=True)
    pdf_stem = pdf_path.stem

    # Get PDF page dimensions using pypdf
    page_dims_list = get_pdf_page_info(pdf_path)

    # Convert PDF to images
    images = convert_from_path(pdf_path, dpi=dpi)

    results = []
    for i, (image, (pdf_width, pdf_height)) in enumerate(
        zip(images, page_dims_list), start=1
    ):
        image_filename = f"{pdf_stem}_page_{i:03d}.jpg"
        image_path = images_dir / image_filename
        image.save(image_path, "JPEG", quality=95)

        dims = PageDimensions(
            pdf_width=pdf_width,
            pdf_height=pdf_height,
            image_width=image.width,
            image_height=image.height,
        )
        results.append((i, image_path, dims))

    return results
