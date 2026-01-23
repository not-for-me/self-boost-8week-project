"""Data models for detection evaluation."""

from dataclasses import dataclass, field
from enum import Enum


class DetectionSource(Enum):
    """Source of a detection."""

    PREDICTION = "prediction"
    GROUND_TRUTH = "ground_truth"


@dataclass(frozen=True)
class BBox:
    """Bounding box in percentage coordinates (0-100).

    Attributes:
        x: Left edge percentage (0-100).
        y: Top edge percentage (0-100).
        width: Width percentage (0-100).
        height: Height percentage (0-100).
    """

    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        """Validate bbox values."""
        if self.width < 0 or self.height < 0:
            raise ValueError("Width and height must be non-negative")

    @property
    def x1(self) -> float:
        """Right edge (x + width)."""
        return self.x + self.width

    @property
    def y1(self) -> float:
        """Bottom edge (y + height)."""
        return self.y + self.height

    @property
    def area(self) -> float:
        """Area of the bounding box."""
        return self.width * self.height


@dataclass(frozen=True)
class Detection:
    """A single detection (predicted or ground truth).

    Attributes:
        bbox: Bounding box coordinates.
        label: Category label (e.g., "income_statement").
        source: Whether this is a prediction or ground truth.
        image_id: Identifier for the source image (e.g., filename).
    """

    bbox: BBox
    label: str
    source: DetectionSource
    image_id: str = ""


@dataclass
class MatchedPair:
    """A matched pair of prediction and ground truth.

    Attributes:
        prediction: The predicted detection.
        ground_truth: The matched ground truth detection.
        iou: IoU score between the two bboxes.
        label_match: Whether the labels match.
    """

    prediction: Detection
    ground_truth: Detection
    iou: float
    label_match: bool = field(init=False)

    def __post_init__(self) -> None:
        """Calculate label match."""
        self.label_match = self.prediction.label == self.ground_truth.label


@dataclass
class EvaluationResult:
    """Results of detection evaluation.

    Attributes:
        tp: True positives (correctly detected).
        fp: False positives (incorrectly detected).
        fn: False negatives (missed detections).
        matched_pairs: List of matched (prediction, ground_truth) pairs.
        iou_threshold: IoU threshold used for matching.
    """

    tp: int
    fp: int
    fn: int
    matched_pairs: list[MatchedPair] = field(default_factory=list)
    iou_threshold: float = 0.5

    @property
    def precision(self) -> float:
        """Precision: TP / (TP + FP)."""
        total = self.tp + self.fp
        return self.tp / total if total > 0 else 0.0

    @property
    def recall(self) -> float:
        """Recall: TP / (TP + FN)."""
        total = self.tp + self.fn
        return self.tp / total if total > 0 else 0.0

    @property
    def f1(self) -> float:
        """F1 Score: 2 * P * R / (P + R)."""
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0

    @property
    def category_accuracy(self) -> float | None:
        """Category accuracy among matched pairs.

        Returns:
            Accuracy as float, or None if no matches.
        """
        if not self.matched_pairs:
            return None
        correct = sum(1 for pair in self.matched_pairs if pair.label_match)
        return correct / len(self.matched_pairs)

    def __add__(self, other: "EvaluationResult") -> "EvaluationResult":
        """Combine two evaluation results."""
        if self.iou_threshold != other.iou_threshold:
            raise ValueError("Cannot combine results with different IoU thresholds")
        return EvaluationResult(
            tp=self.tp + other.tp,
            fp=self.fp + other.fp,
            fn=self.fn + other.fn,
            matched_pairs=self.matched_pairs + other.matched_pairs,
            iou_threshold=self.iou_threshold,
        )
