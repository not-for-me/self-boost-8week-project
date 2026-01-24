"""PDF processing logic for table detection.

Provides functions for processing PDF files sequentially or in parallel,
detecting tables using the ensemble detector.
"""

import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from pypdf import PdfReader
from rich.console import Console
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn

from fin_stat_table_detector.detectors.factory import create_detectors
from fin_stat_table_detector.ensemble import EnsembleDetector
from fin_stat_table_detector.exporters import LabelStudioExporter
from fin_stat_table_detector.utils.pdf_utils import convert_pdf_to_images

# Import display functions from cli module (will be created)
# For now, define locally and move later


def process_pdf_worker(
    pdf_path_str: str,
    images_dir_str: str,
    dpi: int,
    summary_only: bool,
) -> dict:
    """Worker function for parallel PDF processing.

    This is a standalone function that can be pickled for multiprocessing.
    It creates its own detector instance.

    Args:
        pdf_path_str: Path to the PDF file (as string for pickling).
        images_dir_str: Directory to save images (as string for pickling).
        dpi: Image resolution.
        summary_only: If True, don't generate images.

    Returns:
        Dictionary with processing statistics.
    """
    pdf_path = Path(pdf_path_str)
    images_dir = Path(images_dir_str)

    # Create detector in worker process
    detector_instances = create_detectors()
    ensemble = EnsembleDetector(detector_instances)

    stats = {
        "pdf_path": str(pdf_path),
        "pages": 0,
        "tables_detected": 0,
        "categories": {},
        "tables": [],  # Store table data for later export
    }

    try:
        # Detect financial tables
        tables = ensemble.detect_financial_tables(str(pdf_path))
        stats["tables_detected"] = len(tables)
        stats["tables"] = tables

        # Count by category
        for table in tables:
            cat = table.category
            stats["categories"][cat] = stats["categories"].get(cat, 0) + 1

        if summary_only:
            reader = PdfReader(pdf_path)
            stats["pages"] = len(reader.pages)
        else:
            page_results = convert_pdf_to_images(pdf_path, images_dir, dpi)
            stats["pages"] = len(page_results)
            stats["page_results"] = [
                (pn, str(ip), dims) for pn, ip, dims in page_results
            ]

    except Exception as e:
        stats["error"] = str(e)

    return stats


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
        reader = PdfReader(pdf_path)
        stats["pages"] = len(reader.pages)
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


def process_sequential(
    pdf_files: list[Path],
    images_dir: Path,
    dpi: int,
    summary_only: bool,
    exporter: LabelStudioExporter,
    console: Console | None = None,
) -> list[dict]:
    """Process PDF files sequentially with spinner progress.

    Args:
        pdf_files: List of PDF file paths.
        images_dir: Directory to save images.
        dpi: Image resolution.
        summary_only: If True, don't generate images.
        exporter: LabelStudioExporter instance.
        console: Rich console for output. If None, creates a new one.

    Returns:
        List of statistics dictionaries.
    """
    if console is None:
        console = Console()

    detector_instances = create_detectors()
    ensemble = EnsembleDetector(detector_instances)

    console.print(
        f"[dim]Using detectors: {', '.join(d.name for d in detector_instances)}[/dim]\n"
    )

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

    return all_stats


def process_parallel(
    pdf_files: list[Path],
    images_dir: Path,
    dpi: int,
    summary_only: bool,
    workers: int | None,
    console: Console | None = None,
    build_progress_display=None,
) -> list[dict]:
    """Process PDF files in parallel with live progress display.

    Args:
        pdf_files: List of PDF file paths.
        images_dir: Directory to save images.
        dpi: Image resolution.
        summary_only: If True, don't generate images.
        workers: Number of worker processes.
        console: Rich console for output. If None, creates a new one.
        build_progress_display: Function to build progress display.
            Must accept (pdf_files, completed, in_progress, num_workers).

    Returns:
        List of statistics dictionaries.
    """
    if console is None:
        console = Console()

    num_workers = workers or os.cpu_count() or 4

    console.print("[dim]Using detectors: docling[/dim]")
    console.print(f"[dim]Workers: {num_workers}[/dim]\n")

    completed: dict[str, dict] = {}
    in_progress: set[str] = set()
    all_stats: list[dict] = []

    # Map future to pdf_path
    future_to_path: dict = {}

    # Use provided display builder or create a simple one
    if build_progress_display is None:
        from fin_stat_table_detector.cli.display import build_progress_display

    with Live(
        build_progress_display(pdf_files, completed, in_progress, num_workers),
        console=console,
        refresh_per_second=4,
    ) as live:
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            # Submit all tasks
            for pdf_path in pdf_files:
                future = executor.submit(
                    process_pdf_worker,
                    str(pdf_path),
                    str(images_dir),
                    dpi,
                    summary_only,
                )
                future_to_path[future] = pdf_path
                in_progress.add(str(pdf_path))
                live.update(
                    build_progress_display(
                        pdf_files, completed, in_progress, num_workers
                    )
                )

            # Process completed tasks
            for future in as_completed(future_to_path):
                pdf_path = future_to_path[future]
                path_str = str(pdf_path)

                try:
                    stats = future.result()
                except Exception as e:
                    stats = {"pdf_path": path_str, "error": str(e)}

                in_progress.discard(path_str)
                completed[path_str] = stats
                all_stats.append(stats)

                live.update(
                    build_progress_display(
                        pdf_files, completed, in_progress, num_workers
                    )
                )

    return all_stats
