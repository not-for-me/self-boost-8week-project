"""Batch processing strategies for multiple PDF files."""

import os
from abc import ABC, abstractmethod
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

from rich.console import Console
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn

from fin_stat_table_detector.detectors.factory import create_detectors
from fin_stat_table_detector.ensemble import EnsembleDetector
from fin_stat_table_detector.exporters import LabelStudioExporter
from fin_stat_table_detector.processing.config import (
    ProcessingConfig,
    ProcessingResult,
)
from fin_stat_table_detector.processing.pdf_processor import PdfProcessor


class BatchProcessor(ABC):
    """Abstract base class for batch PDF processing.

    Defines the interface for processing multiple PDF files.
    Subclasses implement different processing strategies (sequential, parallel).
    """

    def __init__(
        self,
        config: ProcessingConfig,
        exporter: LabelStudioExporter | None = None,
        console: Console | None = None,
    ) -> None:
        """Initialize BatchProcessor.

        Args:
            config: Processing configuration.
            exporter: Optional exporter for Label Studio format.
            console: Rich console for output. If None, creates a new one.
        """
        self._config = config
        self._exporter = exporter
        self._console = console or Console()

    @property
    def config(self) -> ProcessingConfig:
        """The processing configuration."""
        return self._config

    @property
    def console(self) -> Console:
        """The Rich console for output."""
        return self._console

    @property
    def exporter(self) -> LabelStudioExporter | None:
        """The optional Label Studio exporter."""
        return self._exporter

    @abstractmethod
    def process(self, pdf_files: list[Path]) -> list[ProcessingResult]:
        """Process multiple PDF files.

        Args:
            pdf_files: List of PDF file paths.

        Returns:
            List of ProcessingResult objects.
        """
        pass


class SequentialBatchProcessor(BatchProcessor):
    """Processes PDF files sequentially with progress display.

    Suitable for small batches or when memory is constrained.
    """

    def process(self, pdf_files: list[Path]) -> list[ProcessingResult]:
        """Process PDF files sequentially.

        Args:
            pdf_files: List of PDF file paths.

        Returns:
            List of ProcessingResult objects.
        """
        detector_instances = create_detectors()
        ensemble = EnsembleDetector(detector_instances)

        self._console.print(
            f"[dim]Using detectors: {', '.join(d.name for d in detector_instances)}[/dim]\n"
        )

        processor = PdfProcessor(ensemble, self._config)
        results: list[ProcessingResult] = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self._console,
        ) as progress:
            task = progress.add_task("Processing PDFs...", total=len(pdf_files))

            for pdf_path in pdf_files:
                progress.update(task, description=f"Processing {pdf_path.name}...")

                result = processor.process(pdf_path)

                if self._exporter:
                    self._exporter.export(result)

                if not result.is_success:
                    self._console.print(
                        f"[red]Error processing {pdf_path}: {result.error}[/red]"
                    )

                results.append(result)
                progress.advance(task)

        return results


class ParallelBatchProcessor(BatchProcessor):
    """Processes PDF files in parallel using multiprocessing.

    Suitable for large batches on multi-core systems.
    """

    def __init__(
        self,
        config: ProcessingConfig,
        exporter: LabelStudioExporter | None = None,
        console: Console | None = None,
        workers: int | None = None,
        progress_display_builder: Callable | None = None,
    ) -> None:
        """Initialize ParallelBatchProcessor.

        Args:
            config: Processing configuration.
            exporter: Optional exporter for Label Studio format.
            console: Rich console for output.
            workers: Number of worker processes. Defaults to CPU count.
            progress_display_builder: Function to build progress display.
        """
        super().__init__(config, exporter, console)
        self._workers = workers or os.cpu_count() or 4
        self._progress_display_builder = progress_display_builder

    @property
    def workers(self) -> int:
        """Number of worker processes."""
        return self._workers

    def process(self, pdf_files: list[Path]) -> list[ProcessingResult]:
        """Process PDF files in parallel.

        Args:
            pdf_files: List of PDF file paths.

        Returns:
            List of ProcessingResult objects.
        """
        self._console.print("[dim]Using detectors: docling[/dim]")
        self._console.print(f"[dim]Workers: {self._workers}[/dim]\n")

        # Get progress display builder
        if self._progress_display_builder is None:
            from fin_stat_table_detector.cli.display import build_progress_display
            progress_builder = build_progress_display
        else:
            progress_builder = self._progress_display_builder

        completed: dict[str, ProcessingResult] = {}
        in_progress: set[str] = set()
        results: list[ProcessingResult] = []
        future_to_path: dict = {}

        with Live(
            progress_builder(pdf_files, {}, in_progress, self._workers),
            console=self._console,
            refresh_per_second=4,
        ) as live:
            with ProcessPoolExecutor(max_workers=self._workers) as executor:
                # Submit all tasks
                for pdf_path in pdf_files:
                    future = executor.submit(
                        _process_pdf_worker,
                        str(pdf_path),
                        str(self._config.images_dir),
                        self._config.dpi,
                        self._config.summary_only,
                    )
                    future_to_path[future] = pdf_path
                    in_progress.add(str(pdf_path))
                    live.update(
                        progress_builder(
                            pdf_files,
                            {k: v.to_dict() for k, v in completed.items()},
                            in_progress,
                            self._workers,
                        )
                    )

                # Process completed tasks
                for future in as_completed(future_to_path):
                    pdf_path = future_to_path[future]
                    path_str = str(pdf_path)

                    try:
                        result = future.result()
                    except Exception as e:
                        result = ProcessingResult(pdf_path=pdf_path, error=str(e))

                    in_progress.discard(path_str)
                    completed[path_str] = result
                    results.append(result)

                    live.update(
                        progress_builder(
                            pdf_files,
                            {k: v.to_dict() for k, v in completed.items()},
                            in_progress,
                            self._workers,
                        )
                    )

        # Add results to exporter if provided
        if self._exporter and not self._config.summary_only:
            for result in results:
                self._exporter.export(result)

        return results


def _process_pdf_worker(
    pdf_path_str: str,
    images_dir_str: str,
    dpi: int,
    summary_only: bool,
) -> ProcessingResult:
    """Worker function for parallel PDF processing.

    This is a standalone function that can be pickled for multiprocessing.
    Creates its own detector and processor instances in the worker process.

    Args:
        pdf_path_str: Path to the PDF file (as string for pickling).
        images_dir_str: Directory to save images (as string for pickling).
        dpi: Image resolution.
        summary_only: If True, don't generate images.

    Returns:
        ProcessingResult with detected tables and statistics.
    """
    pdf_path = Path(pdf_path_str)
    images_dir = Path(images_dir_str)

    # Create config and processor in worker process
    config = ProcessingConfig(
        images_dir=images_dir,
        dpi=dpi,
        summary_only=summary_only,
    )

    detector_instances = create_detectors()
    ensemble = EnsembleDetector(detector_instances)
    processor = PdfProcessor(ensemble, config)

    return processor.process(pdf_path)
