"""Ensemble detector for combining multiple table detectors.

Provides EnsembleDetector class for running multiple detectors and merging
their results using IoU-based deduplication.
"""

from collections import defaultdict

from fin_stat_table_detector.classifiers.financial import FinancialTableClassifier
from fin_stat_table_detector.detectors.base import AbstractDetector
from fin_stat_table_detector.models import BBox, FinancialTable, TableCandidate
from fin_stat_table_detector.utils import SpatialIndex, UnionFind


def calculate_iou(bbox1: BBox, bbox2: BBox) -> float:
    """Calculate Intersection over Union (IoU) of two bounding boxes.

    Args:
        bbox1: First bounding box.
        bbox2: Second bounding box.

    Returns:
        IoU value between 0.0 and 1.0.
        - 1.0: Identical regions
        - 0.0: No overlap
    """
    # Calculate intersection area
    x0 = max(bbox1.x0, bbox2.x0)
    y0 = max(bbox1.y0, bbox2.y0)
    x1 = min(bbox1.x1, bbox2.x1)
    y1 = min(bbox1.y1, bbox2.y1)

    # No overlap case
    if x0 >= x1 or y0 >= y1:
        return 0.0

    intersection = (x1 - x0) * (y1 - y0)
    union = bbox1.area + bbox2.area - intersection

    return intersection / union if union > 0 else 0.0


def merge_candidates(
    candidates: list[TableCandidate],
    iou_threshold: float = 0.3,
) -> list[TableCandidate]:
    """Merge overlapping table candidates using Union-Find and Spatial Index.

    Steps:
    1. Separate by page (different pages cannot be merged)
    2. Use Spatial Index to quickly find overlapping candidates
    3. Calculate IoU to confirm actual overlap
    4. Use Union-Find for transitive grouping
    5. Select representative from each group (largest bbox)

    Args:
        candidates: List of table candidates to merge.
        iou_threshold: IoU threshold for considering candidates as overlapping.

    Returns:
        List of merged TableCandidate with duplicates removed.
    """
    if not candidates:
        return []

    # Separate by page (candidates on different pages cannot be merged)
    by_page: dict[int, list[tuple[int, TableCandidate]]] = defaultdict(list)
    for i, c in enumerate(candidates):
        by_page[c.page].append((i, c))

    merged: list[TableCandidate] = []

    for page, page_items in by_page.items():
        n = len(page_items)
        if n == 1:
            merged.append(page_items[0][1])
            continue

        # 1. Build Spatial Index
        index = SpatialIndex()
        for local_idx, (_, c) in enumerate(page_items):
            index.insert(local_idx, c.bbox)

        # 2. Initialize Union-Find
        uf = UnionFind(n)

        # 3. Find overlapping pairs and union them
        for local_idx, (_, c) in enumerate(page_items):
            overlapping = index.query_overlapping(c.bbox)
            for other_idx in overlapping:
                if other_idx <= local_idx:
                    continue  # Avoid duplicate comparison (including self)

                other_bbox = page_items[other_idx][1].bbox
                if calculate_iou(c.bbox, other_bbox) > iou_threshold:
                    uf.union(local_idx, other_idx)

        # 4. Select representative for each group (largest bbox)
        for group_indices in uf.get_groups().values():
            group_candidates = [page_items[i][1] for i in group_indices]
            best = max(group_candidates, key=lambda x: x.bbox.area)
            merged.append(best)

    return merged


class EnsembleDetector:
    """Ensemble detector combining multiple table detectors.

    Runs multiple detectors on a PDF, merges overlapping results using IoU,
    and optionally classifies detected tables as financial statements.

    Attributes:
        detectors: List of table detectors to use.
        iou_threshold: IoU threshold for deduplication.
        classifier: Financial table classifier instance.
    """

    def __init__(
        self,
        detectors: list[AbstractDetector],
        iou_threshold: float = 0.3,
        classifier: FinancialTableClassifier | None = None,
    ) -> None:
        """Initialize the ensemble detector.

        Args:
            detectors: List of detectors to use.
            iou_threshold: IoU threshold for deduplication (default 0.3).
            classifier: Financial table classifier (uses default if None).

        Raises:
            ValueError: If detectors list is empty.
        """
        if not detectors:
            raise ValueError("At least one detector is required")

        self.detectors = detectors
        self.iou_threshold = iou_threshold
        self.classifier = classifier or FinancialTableClassifier()

    def detect_all_tables(
        self,
        pdf_path: str,
        pages: list[int] | None = None,
    ) -> list[TableCandidate]:
        """Detect all table candidates using all detectors (no classification).

        Args:
            pdf_path: Path to the PDF file.
            pages: List of page numbers to process (1-indexed). None for all pages.

        Returns:
            List of deduplicated TableCandidate objects.
        """
        all_candidates: list[TableCandidate] = []

        # 1. Run all detectors
        for detector in self.detectors:
            try:
                candidates = detector.detect(pdf_path, pages)
                all_candidates.extend(candidates)
            except Exception as e:
                # Log individual detector failures but continue
                print(f"Warning: {detector.name} failed: {e}")

        # 2. Merge overlapping candidates
        merged = merge_candidates(all_candidates, self.iou_threshold)

        return merged

    def detect_financial_tables(
        self,
        pdf_path: str,
        pages: list[int] | None = None,
    ) -> list[FinancialTable]:
        """Detect financial statement tables from PDF.

        Steps:
        1. Detect table candidates using all detectors
        2. Remove duplicates (IoU-based)
        3. Classify as financial statements
        4. Return results sorted by confidence

        Args:
            pdf_path: Path to the PDF file.
            pages: List of page numbers to process (1-indexed). None for all pages.

        Returns:
            List of FinancialTable objects classified as financial statements,
            sorted by confidence (descending) then page number (ascending).
        """
        # 1-2. Detect and deduplicate table candidates
        candidates = self.detect_all_tables(pdf_path, pages)

        # 3. Classify as financial statements
        financial_tables: list[FinancialTable] = []
        for candidate in candidates:
            result = self.classifier.classify(candidate, pdf_path)
            if result is not None:
                financial_tables.append(result)

        # 4. Sort by confidence (descending), then page (ascending)
        financial_tables.sort(key=lambda x: (-x.confidence, x.page))

        return financial_tables
