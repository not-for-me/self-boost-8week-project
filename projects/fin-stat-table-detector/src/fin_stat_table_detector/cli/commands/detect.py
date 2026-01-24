"""Detect command for financial statement table detection.

Processes PDF files and exports detection results to Label Studio format.
Uses docling ML-based detector to maximize recall.
"""

import time
from pathlib import Path

import click
from rich.console import Console

from fin_stat_table_detector.cli.display import print_summary
from fin_stat_table_detector.exporters import LabelStudioExporter
from fin_stat_table_detector.processing import process_parallel, process_sequential
from fin_stat_table_detector.utils.file_utils import find_pdf_files

console = Console()


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
@click.option(
    "--parallel",
    "-p",
    is_flag=True,
    help="Enable parallel processing for multiple files.",
)
@click.option(
    "--workers",
    "-w",
    type=int,
    default=None,
    help="Number of worker processes. Default: CPU count.",
)
@click.option(
    "--dataset-name",
    "-d",
    type=str,
    default=None,
    help="Dataset name for Label Studio local file paths. "
    "Images will be referenced as /data/local-files/?d=<dataset-name>/<filename>",
)
def detect(
    input_path: Path,
    output: Path | None,
    images_dir: Path,
    dpi: int,
    dry_run: bool,
    summary_only: bool,
    parallel: bool,
    workers: int | None,
    dataset_name: str | None,
) -> None:
    """Detect financial tables in PDF files.

    Uses docling ML-based detector with OCR support.

    INPUT_PATH can be a single PDF file or a directory containing PDF files.

    Examples:

        fin-stat-table-detector detect report.pdf

        fin-stat-table-detector detect ./data/ --dry-run

        fin-stat-table-detector detect report.pdf --summary-only

        fin-stat-table-detector detect ./data/ --parallel --workers 4

        fin-stat-table-detector detect report.pdf -d samsung_2024
    """
    # Find PDF files
    pdf_files = find_pdf_files(input_path)

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

    # Create exporter
    exporter = LabelStudioExporter(dataset_name=dataset_name)

    # Process files
    start_time = time.perf_counter()

    if parallel and len(pdf_files) > 1:
        # Parallel processing
        all_stats = process_parallel(
            pdf_files, images_dir, dpi, summary_only, workers, console
        )
    else:
        # Sequential processing
        all_stats = process_sequential(
            pdf_files, images_dir, dpi, summary_only, exporter, console
        )

    elapsed_time = time.perf_counter() - start_time

    # Save results (unless summary-only)
    if not summary_only:
        # For parallel processing, need to populate exporter from stats
        if parallel and len(pdf_files) > 1:
            for stats in all_stats:
                if "error" in stats or "page_results" not in stats:
                    continue
                tables = stats.get("tables", [])
                tables_by_page: dict[int, list] = {}
                for table in tables:
                    tables_by_page.setdefault(table.page, []).append(table)

                for page_num, image_path_str, dims in stats["page_results"]:
                    page_tables = tables_by_page.get(page_num, [])
                    exporter.add_page_results(image_path_str, page_tables, dims)

        exporter.save(output)
        console.print(f"\n[green]Results saved to: {output}[/green]")
        console.print(f"[green]Images saved to: {images_dir}[/green]")

    # Print summary
    print_summary(all_stats, elapsed_time, console)
