"""Detection evaluation logic.

Evaluates detection results against ground truth using IoU-based matching.
"""

from data_evaluator.metrics.iou import calculate_iou
from data_evaluator.models import Detection, EvaluationResult, MatchedPair


class DetectionEvaluator:
    """Evaluator for object detection results.

    Uses greedy IoU-based matching to compare predictions against ground truth.

    Attributes:
        iou_threshold: Minimum IoU for a match to be considered valid.
    """

    def __init__(self, iou_threshold: float = 0.5) -> None:
        """Initialize the evaluator.

        Args:
            iou_threshold: IoU threshold for matching (default: 0.5).

        Raises:
            ValueError: If iou_threshold is not between 0 and 1.
        """
        if not 0 <= iou_threshold <= 1:
            raise ValueError("iou_threshold must be between 0 and 1")
        self.iou_threshold = iou_threshold

    def evaluate_page(
        self,
        predictions: list[Detection],
        ground_truths: list[Detection],
    ) -> EvaluationResult:
        """Evaluate detections for a single page/image.

        Uses greedy matching: for each prediction, find the best matching
        ground truth (highest IoU above threshold). Each ground truth can
        only be matched once.

        Args:
            predictions: List of predicted detections.
            ground_truths: List of ground truth detections.

        Returns:
            EvaluationResult with TP, FP, FN counts and matched pairs.
        """
        matched_pairs: list[MatchedPair] = []
        matched_gt_indices: set[int] = set()

        iou_scores: list[tuple[int, int, float]] = []
        for pred_idx, pred in enumerate(predictions):
            for gt_idx, gt in enumerate(ground_truths):
                iou = calculate_iou(pred.bbox, gt.bbox)
                if iou >= self.iou_threshold:
                    iou_scores.append((pred_idx, gt_idx, iou))

        iou_scores.sort(key=lambda x: x[2], reverse=True)

        matched_pred_indices: set[int] = set()
        for pred_idx, gt_idx, iou in iou_scores:
            if pred_idx in matched_pred_indices or gt_idx in matched_gt_indices:
                continue

            matched_pred_indices.add(pred_idx)
            matched_gt_indices.add(gt_idx)

            matched_pairs.append(
                MatchedPair(
                    prediction=predictions[pred_idx],
                    ground_truth=ground_truths[gt_idx],
                    iou=iou,
                )
            )

        tp = len(matched_pairs)
        fp = len(predictions) - tp
        fn = len(ground_truths) - tp

        return EvaluationResult(
            tp=tp,
            fp=fp,
            fn=fn,
            matched_pairs=matched_pairs,
            iou_threshold=self.iou_threshold,
        )

    def evaluate_dataset(
        self,
        predictions: dict[str, list[Detection]],
        ground_truths: dict[str, list[Detection]],
    ) -> EvaluationResult:
        """Evaluate detections for an entire dataset.

        Args:
            predictions: Dict mapping image_id to list of predictions.
            ground_truths: Dict mapping image_id to list of ground truths.

        Returns:
            Combined EvaluationResult across all images.
        """
        all_image_ids = set(predictions.keys()) | set(ground_truths.keys())

        combined_result = EvaluationResult(
            tp=0, fp=0, fn=0, iou_threshold=self.iou_threshold
        )

        for image_id in all_image_ids:
            preds = predictions.get(image_id, [])
            gts = ground_truths.get(image_id, [])

            page_result = self.evaluate_page(preds, gts)
            combined_result = combined_result + page_result

        return combined_result
