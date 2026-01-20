"""Coordinate conversion utilities for Label Studio export.

Provides functions to convert PDF coordinates (points) to Label Studio
percentage-based coordinates (0-100).
"""

from dataclasses import dataclass

from fin_stat_table_detector.models import BBox


@dataclass
class PageDimensions:
    """Page dimensions for coordinate conversion.

    Attributes:
        pdf_width: PDF page width in points.
        pdf_height: PDF page height in points.
        image_width: Rendered image width in pixels.
        image_height: Rendered image height in pixels.
    """

    pdf_width: float
    pdf_height: float
    image_width: int
    image_height: int


def bbox_to_label_studio(bbox: BBox, page_dims: PageDimensions) -> dict:
    """Convert BBox to Label Studio percentage coordinates.

    Label Studio uses percentage-based coordinates (0-100) relative to the
    image dimensions. This function converts PDF point coordinates to
    these percentages.

    Args:
        bbox: Bounding box with PDF point coordinates.
        page_dims: Page dimensions for coordinate conversion.

    Returns:
        Dictionary with x, y, width, height as percentages (0-100).
        - x: Left edge percentage
        - y: Top edge percentage
        - width: Width percentage
        - height: Height percentage

    Raises:
        ValueError: If page dimensions have zero width or height.

    Example:
        >>> bbox = BBox(x0=0, y0=0, x1=306, y1=396)
        >>> dims = PageDimensions(pdf_width=612, pdf_height=792, ...)
        >>> result = bbox_to_label_studio(bbox, dims)
        >>> # result = {"x": 0.0, "y": 0.0, "width": 50.0, "height": 50.0}
    """
    if page_dims.pdf_width <= 0 or page_dims.pdf_height <= 0:
        raise ValueError("Page dimensions must be positive")

    return {
        "x": (bbox.x0 / page_dims.pdf_width) * 100,
        "y": (bbox.y0 / page_dims.pdf_height) * 100,
        "width": (bbox.width / page_dims.pdf_width) * 100,
        "height": (bbox.height / page_dims.pdf_height) * 100,
    }
