"""IoU (Intersection over Union) calculation for bounding boxes."""

from data_evaluator.models import BBox


def calculate_intersection_area(bbox1: BBox, bbox2: BBox) -> float:
    """Calculate the intersection area of two bounding boxes.

    Args:
        bbox1: First bounding box.
        bbox2: Second bounding box.

    Returns:
        Intersection area. Returns 0 if boxes don't overlap.
    """
    x_left = max(bbox1.x, bbox2.x)
    y_top = max(bbox1.y, bbox2.y)
    x_right = min(bbox1.x1, bbox2.x1)
    y_bottom = min(bbox1.y1, bbox2.y1)

    if x_right <= x_left or y_bottom <= y_top:
        return 0.0

    return (x_right - x_left) * (y_bottom - y_top)


def calculate_union_area(bbox1: BBox, bbox2: BBox) -> float:
    """Calculate the union area of two bounding boxes.

    Args:
        bbox1: First bounding box.
        bbox2: Second bounding box.

    Returns:
        Union area (area1 + area2 - intersection).
    """
    intersection = calculate_intersection_area(bbox1, bbox2)
    return bbox1.area + bbox2.area - intersection


def calculate_iou(bbox1: BBox, bbox2: BBox) -> float:
    """Calculate IoU (Intersection over Union) of two bounding boxes.

    IoU = Area of Intersection / Area of Union

    Args:
        bbox1: First bounding box.
        bbox2: Second bounding box.

    Returns:
        IoU score between 0 and 1.
        Returns 0 if boxes don't overlap or have zero area.
    """
    intersection = calculate_intersection_area(bbox1, bbox2)
    if intersection == 0:
        return 0.0

    union = calculate_union_area(bbox1, bbox2)
    if union == 0:
        return 0.0

    return intersection / union
