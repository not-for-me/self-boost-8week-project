"""Abstract base class for result exporters."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fin_stat_table_detector.processing.config import ProcessingResult


class ResultExporter(ABC):
    """Abstract base class for exporting detection results.

    Defines the interface for exporting ProcessingResult to various formats.
    Implementations can export to Label Studio, COCO, YOLO, or other formats.

    Example:
        >>> exporter = LabelStudioExporter()
        >>> for result in results:
        ...     exporter.export(result)
        >>> exporter.save("output.json")
    """

    @abstractmethod
    def export(self, result: "ProcessingResult") -> None:
        """Export a single processing result.

        Args:
            result: ProcessingResult containing detected tables and page info.
        """
        pass

    @abstractmethod
    def save(self, output_path: Path | str) -> None:
        """Save all exported results to a file.

        Args:
            output_path: Path to the output file.
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all accumulated export data."""
        pass
