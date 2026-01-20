"""Detect command for financial statement table detection.

Processes PDF files and exports detection results to Label Studio format.
"""

import re
from pathlib import Path

import click
import pdfplumber
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from fin_stat_table_detector.detectors import CamelotDetector, PdfplumberDetector
from fin_stat_table_detector.ensemble import EnsembleDetector
from fin_stat_table_detector.exporters import LabelStudioExporter, PageDimensions

console = Console()

# Mapping of detector names to classes
DETECTOR_MAP = {
    "pdfplumber": PdfplumberDetector,
    "camelot_lattice": lambda: CamelotDetector(flavor="lattice"),
    "camelot_stream": lambda: CamelotDetector(flavor="stream"),
}


def get_detectors(detector_names: list[str]) -> list:
    """Create detector instances from names.

    Args:
        detector_names: List of detector names.

    Returns:
        List of detector instances.

    Raises:
        click.BadParameter: If an unknown detector name is provided.
    """
    detectors = []
    for name in detector_names:
        name = name.strip()
        if name not in DETECTOR_MAP:
            raise click.BadParameter(
                f"Unknown detector: {name}. Available: {', '.join(DETECTOR_MAP.keys())}"
            )
        factory = DETECTOR_MAP[name]
        if callable(factory) and not isinstance(factory, type):
            detectors.append(factory())
        else:
            detectors.append(factory())
    return detectors


def find_pdf_files(path: Path, firm_filter: str | None = None) -> list[Path]:
    """Find PDF files in the given path.

    Args:
        path: File or directory path.
        firm_filter: Optional firm name filter (matches in filename).

    Returns:
        List of PDF file paths.
    """
    if path.is_file():
        if path.suffix.lower() == ".pdf":
            if firm_filter is None or firm_filter in path.name:
                return [path]
        return []

    pdf_files = list(path.glob("**/*.pdf"))
    if firm_filter:
        pattern = re.compile(re.escape(firm_filter), re.IGNORECASE)
        pdf_files = [f for f in pdf_files if pattern.search(f.name)]

    return sorted(pdf_files)


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
    """
    try:
        from pdf2image import convert_from_path
    except ImportError:
        raise click.ClickException(
            "pdf2image is required for image conversion. Install with: uv add pdf2image"
        )

    images_dir.mkdir(parents=True, exist_ok=True)
    pdf_stem = pdf_path.stem

    # Get PDF page dimensions using pdfplumber
    page_dims_list = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_dims_list.append((page.width, page.height))

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


def process_pdf(
    pdf_path: Path,
    detector: EnsembleDetector,
    exporter: LabelStudioExporter,
    images_dir: Path,
    dpi: int,
    summary_only: bool,
) -> dict:
    """Process a single PDF file.

    Args:
        pdf_path: Path to the PDF file.
        detector: EnsembleDetector instance.
        exporter: LabelStudioExporter instance.
        images_dir: Directory to save images.
        dpi: Image resolution.
        summary_only: If True, don't generate images.

    Returns:
        Dictionary with processing statistics.
    """
    stats = {
        "pdf_path": str(pdf_path),
        "pages": 0,
        "tables_detected": 0,
        "categories": {},
    }

    # Detect financial tables
    tables = detector.detect_financial_tables(str(pdf_path))
    stats["tables_detected"] = len(tables)

    # Count by category
    for table in tables:
        cat = table.category
        stats["categories"][cat] = stats["categories"].get(cat, 0) + 1

    if summary_only:
        # Just count pages without image conversion
        with pdfplumber.open(pdf_path) as pdf:
            stats["pages"] = len(pdf.pages)
        return stats

    # Convert PDF to images and add to exporter
    page_results = convert_pdf_to_images(pdf_path, images_dir, dpi)
    stats["pages"] = len(page_results)

    # Group tables by page
    tables_by_page: dict[int, list] = {}
    for table in tables:
        tables_by_page.setdefault(table.page, []).append(table)

    # Add each page to exporter
    for page_num, image_path, dims in page_results:
        page_tables = tables_by_page.get(page_num, [])
        exporter.add_page_results(str(image_path), page_tables, dims)

    return stats


@click.command()
@click.argument(
    "input_path",
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output JSON path. Default: <input>_labels.json",
)
@click.option(
    "--images-dir",
    "-i",
    type=click.Path(path_type=Path),
    default=Path("./images"),
    help="Directory to save page images. Default: ./images/",
)
@click.option(
    "--firm",
    "-f",
    type=str,
    default=None,
    help="Filter by firm name (matches filename).",
)
@click.option(
    "--detectors",
    "-d",
    type=str,
    default="pdfplumber,camelot_lattice",
    help="Comma-separated detector names. Default: pdfplumber,camelot_lattice",
)
@click.option(
    "--dpi",
    type=int,
    default=150,
    help="Image resolution (DPI). Default: 150",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show files to process without processing.",
)
@click.option(
    "--summary-only",
    "-s",
    is_flag=True,
    help="Show detection summary without generating images.",
)
def detect(
    input_path: Path,
    output: Path | None,
    images_dir: Path,
    firm: str | None,
    detectors: str,
    dpi: int,
    dry_run: bool,
    summary_only: bool,
) -> None:
    """Detect financial tables in PDF files.

    INPUT_PATH can be a single PDF file or a directory containing PDF files.

    Examples:

        fin-stat-detect detect report.pdf

        fin-stat-detect detect ./data/ --firm "한화투자증권"

        fin-stat-detect detect ./data/ --dry-run

        fin-stat-detect detect report.pdf --summary-only
    """
    # Find PDF files
    pdf_files = find_pdf_files(input_path, firm)

    if not pdf_files:
        console.print("[yellow]No PDF files found.[/yellow]")
        return

    # Dry run: just list files
    if dry_run:
        console.print(f"\n[bold]Files to process ({len(pdf_files)}):[/bold]\n")
        for pdf_path in pdf_files:
            console.print(f"  {pdf_path}")
        return

    # Determine output path
    if output is None:
        if input_path.is_file():
            output = input_path.with_suffix(".json").with_name(
                f"{input_path.stem}_labels.json"
            )
        else:
            output = input_path / "labels.json"

    # Create detectors
    detector_names = [d.strip() for d in detectors.split(",")]
    detector_instances = get_detectors(detector_names)
    ensemble = EnsembleDetector(detector_instances)

    # Create exporter
    exporter = LabelStudioExporter()

    # Process files
    all_stats = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Processing PDFs...", total=len(pdf_files))

        for pdf_path in pdf_files:
            progress.update(task, description=f"Processing {pdf_path.name}...")
            try:
                stats = process_pdf(
                    pdf_path,
                    ensemble,
                    exporter,
                    images_dir,
                    dpi,
                    summary_only,
                )
                all_stats.append(stats)
            except Exception as e:
                console.print(f"[red]Error processing {pdf_path}: {e}[/red]")
                all_stats.append(
                    {
                        "pdf_path": str(pdf_path),
                        "error": str(e),
                    }
                )
            progress.advance(task)

    # Save results (unless summary-only)
    if not summary_only:
        exporter.save(output)
        console.print(f"\n[green]Results saved to: {output}[/green]")
        console.print(f"[green]Images saved to: {images_dir}[/green]")

    # Print summary
    print_summary(all_stats)


def print_summary(all_stats: list[dict]) -> None:
    """Print processing summary.

    Args:
        all_stats: List of statistics dictionaries.
    """
    table = Table(title="\nDetection Summary")
    table.add_column("PDF", style="cyan")
    table.add_column("Pages", justify="right")
    table.add_column("Tables", justify="right")
    table.add_column("Categories", style="green")

    total_pages = 0
    total_tables = 0

    for stats in all_stats:
        if "error" in stats:
            table.add_row(
                Path(stats["pdf_path"]).name,
                "-",
                "-",
                f"[red]Error: {stats['error'][:30]}...[/red]",
            )
            continue

        pages = stats.get("pages", 0)
        tables = stats.get("tables_detected", 0)
        categories = stats.get("categories", {})

        total_pages += pages
        total_tables += tables

        cat_str = ", ".join(f"{k}:{v}" for k, v in categories.items()) or "-"

        table.add_row(
            Path(stats["pdf_path"]).name,
            str(pages),
            str(tables),
            cat_str,
        )

    # Add totals row
    table.add_section()
    table.add_row(
        "[bold]Total[/bold]",
        f"[bold]{total_pages}[/bold]",
        f"[bold]{total_tables}[/bold]",
        "",
    )

    console.print(table)
