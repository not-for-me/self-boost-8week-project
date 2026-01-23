"""Label Studio JSON format parser.

Parses both predictions (model output) and annotations (ground truth)
from Label Studio JSON export format.
"""

from typing import Any

from data_evaluator.models import BBox, Detection, DetectionSource


def _extract_image_id(task: dict[str, Any]) -> str:
    """Extract image identifier from task data.

    Args:
        task: Label Studio task dictionary.

    Returns:
        Image path or identifier.
    """
    data = task.get("data", {})
    return data.get("image", "")


def _parse_rectangle_result(
    result: dict[str, Any],
    source: DetectionSource,
    image_id: str,
) -> Detection | None:
    """Parse a single rectanglelabels result.

    Args:
        result: Single result from Label Studio format.
        source: Whether this is prediction or ground truth.
        image_id: Image identifier.

    Returns:
        Detection object or None if parsing fails.
    """
    if result.get("type") != "rectanglelabels":
        return None

    value = result.get("value", {})

    x = value.get("x")
    y = value.get("y")
    width = value.get("width")
    height = value.get("height")

    if any(v is None for v in [x, y, width, height]):
        return None

    labels = value.get("rectanglelabels", [])
    label = labels[0] if labels else "unknown"

    return Detection(
        bbox=BBox(x=x, y=y, width=width, height=height),
        label=label,
        source=source,
        image_id=image_id,
    )


def parse_predictions(json_data: list[dict[str, Any]]) -> dict[str, list[Detection]]:
    """Parse Label Studio predictions JSON.

    Predictions are model outputs, typically found in the "predictions" field.

    Args:
        json_data: List of Label Studio task dictionaries.

    Returns:
        Dictionary mapping image_id to list of detections.

    Example input:
        [{
            "data": {"image": "page_1.png"},
            "predictions": [{
                "model_version": "ensemble-v1",
                "result": [{
                    "type": "rectanglelabels",
                    "value": {"x": 10, "y": 20, "width": 80, "height": 30,
                              "rectanglelabels": ["income_statement"]}
                }]
            }]
        }]
    """
    detections: dict[str, list[Detection]] = {}

    for task in json_data:
        image_id = _extract_image_id(task)
        if not image_id:
            continue

        detections[image_id] = []

        predictions = task.get("predictions", [])
        for prediction in predictions:
            results = prediction.get("result", [])
            for result in results:
                detection = _parse_rectangle_result(
                    result, DetectionSource.PREDICTION, image_id
                )
                if detection:
                    detections[image_id].append(detection)

    return detections


def parse_annotations(json_data: list[dict[str, Any]]) -> dict[str, list[Detection]]:
    """Parse Label Studio annotations JSON (ground truth).

    Annotations are human-verified labels, typically found in the "annotations" field.

    Args:
        json_data: List of Label Studio task dictionaries.

    Returns:
        Dictionary mapping image_id to list of detections.

    Example input:
        [{
            "data": {"image": "page_1.png"},
            "annotations": [{
                "result": [{
                    "type": "rectanglelabels",
                    "value": {"x": 10, "y": 20, "width": 81, "height": 31,
                              "rectanglelabels": ["income_statement"]}
                }]
            }]
        }]
    """
    detections: dict[str, list[Detection]] = {}

    for task in json_data:
        image_id = _extract_image_id(task)
        if not image_id:
            continue

        detections[image_id] = []

        annotations = task.get("annotations", [])
        for annotation in annotations:
            results = annotation.get("result", [])
            for result in results:
                detection = _parse_rectangle_result(
                    result, DetectionSource.GROUND_TRUTH, image_id
                )
                if detection:
                    detections[image_id].append(detection)

    return detections
