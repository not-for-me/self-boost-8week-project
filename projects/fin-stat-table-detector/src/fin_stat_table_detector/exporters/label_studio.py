"""Label Studio JSON export for table detection results.

Provides classes and functions to export detected financial tables to
Label Studio compatible JSON format for annotation review.
"""

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from fin_stat_table_detector.exporters.converters import (
    PageDimensions,
    bbox_to_label_studio,
)
from fin_stat_table_detector.models import FinancialTable


@dataclass
class LabelStudioAnnotation:
    """Single annotation result in Label Studio format.

    Attributes:
        x: Left edge percentage (0-100).
        y: Top edge percentage (0-100).
        width: Width percentage (0-100).
        height: Height percentage (0-100).
        labels: List of label strings (e.g., ["income_statement"]).
        annotation_id: Unique identifier for this annotation.
    """

    x: float
    y: float
    width: float
    height: float
    labels: list[str]
    annotation_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def to_dict(self) -> dict:
        """Convert to Label Studio result format.

        Returns:
            Dictionary in Label Studio rectanglelabels format.
        """
        return {
            "id": self.annotation_id,
            "type": "rectanglelabels",
            "from_name": "label",
            "to_name": "image",
            "original_width": 100,
            "original_height": 100,
            "value": {
                "x": self.x,
                "y": self.y,
                "width": self.width,
                "height": self.height,
                "rotation": 0,
                "rectanglelabels": self.labels,
            },
        }


@dataclass
class LabelStudioTask:
    """Single Label Studio task (one image with annotations).

    Attributes:
        image_path: Path to the image file.
        annotations: List of annotations for this image.
        model_version: Version identifier for the detection model.
    """

    image_path: str
    annotations: list[LabelStudioAnnotation] = field(default_factory=list)
    model_version: str = "ensemble-v1"

    def to_dict(self) -> dict:
        """Convert to Label Studio task format.

        Returns:
            Dictionary in Label Studio import format.
        """
        task = {
            "data": {"image": self.image_path},
        }

        if self.annotations:
            task["predictions"] = [
                {
                    "model_version": self.model_version,
                    "result": [ann.to_dict() for ann in self.annotations],
                }
            ]

        return task


class LabelStudioExporter:
    """Export financial table detection results to Label Studio format.

    This exporter creates JSON files compatible with Label Studio's import
    format, including image paths and pre-annotation bounding boxes.

    Attributes:
        model_version: Version identifier for detection results.
    """

    def __init__(self, model_version: str = "ensemble-v1") -> None:
        """Initialize the exporter.

        Args:
            model_version: Version identifier for detection model.
        """
        self.model_version = model_version
        self._tasks: list[LabelStudioTask] = []

    def add_page_results(
        self,
        image_path: str,
        tables: list[FinancialTable],
        page_dims: PageDimensions,
    ) -> None:
        """Add detection results for a single page.

        Args:
            image_path: Path to the page image file.
            tables: List of detected financial tables on this page.
            page_dims: Page dimensions for coordinate conversion.
        """
        annotations = []
        for table in tables:
            coords = bbox_to_label_studio(table.bbox, page_dims)
            annotation = LabelStudioAnnotation(
                x=coords["x"],
                y=coords["y"],
                width=coords["width"],
                height=coords["height"],
                labels=[table.category],
            )
            annotations.append(annotation)

        task = LabelStudioTask(
            image_path=image_path,
            annotations=annotations,
            model_version=self.model_version,
        )
        self._tasks.append(task)

    def to_list(self) -> list[dict]:
        """Export all tasks as a list of dictionaries.

        Returns:
            List of task dictionaries in Label Studio format.
        """
        return [task.to_dict() for task in self._tasks]

    def save(self, output_path: str | Path) -> None:
        """Save results to a JSON file.

        Args:
            output_path: Path to the output JSON file.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.to_list(), f, ensure_ascii=False, indent=2)

    def clear(self) -> None:
        """Clear all accumulated tasks."""
        self._tasks.clear()

    @property
    def task_count(self) -> int:
        """Number of tasks in the exporter."""
        return len(self._tasks)
