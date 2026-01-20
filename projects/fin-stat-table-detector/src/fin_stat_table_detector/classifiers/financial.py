"""Financial table classifier module.

Provides FinancialTableClassifier for classifying table candidates
as financial statements based on keywords, numeric density, and temporal patterns.
"""

import re

from fin_stat_table_detector.classifiers.constants import (
    FINANCIAL_STATEMENT_PATTERNS,
    TEMPORAL_PATTERNS,
)
from fin_stat_table_detector.models import BBox, FinancialTable, TableCandidate


class FinancialTableClassifier:
    """Classifier for determining if a table is a financial statement.

    Uses keyword matching, numeric density analysis, and temporal pattern
    detection to classify tables as financial statements.

    Attributes:
        numeric_density_threshold: Minimum ratio of numeric tokens (default 0.2).
        min_temporal_matches: Minimum number of temporal pattern matches (default 2).
        min_confidence: Minimum confidence score for classification (default 0.3).
    """

    def __init__(
        self,
        numeric_density_threshold: float = 0.2,
        min_temporal_matches: int = 2,
        min_confidence: float = 0.3,
    ) -> None:
        """Initialize the classifier.

        Args:
            numeric_density_threshold: Minimum ratio of numeric tokens (default 20%).
            min_temporal_matches: Minimum number of temporal pattern matches.
            min_confidence: Minimum confidence threshold for classification.
        """
        self.numeric_density_threshold = numeric_density_threshold
        self.min_temporal_matches = min_temporal_matches
        self.min_confidence = min_confidence

    def classify(
        self,
        candidate: TableCandidate,
        pdf_path: str | None = None,
        page_width: float | None = None,
        page_height: float | None = None,
    ) -> FinancialTable | None:
        """Classify a table candidate as a financial statement.

        Args:
            candidate: The TableCandidate to classify.
            pdf_path: Path to PDF file for text extraction if text_content is missing.
            page_width: Page width for size validation.
            page_height: Page height for size validation.

        Returns:
            FinancialTable if classified as financial statement, None otherwise.
        """
        # Get text content
        text = candidate.text_content
        if not text and pdf_path:
            text = self._extract_text_from_bbox(
                pdf_path, candidate.page, candidate.bbox
            )

        if not text:
            return None

        # 1. Validate table size
        if page_width and page_height:
            if not self._is_valid_table_size(
                candidate.bbox,
                page_width,
                page_height,
                candidate.row_count,
                candidate.col_count,
            ):
                return None

        # 2. Keyword matching
        category, keyword_score, matched_keywords = self._calculate_keyword_score(text)
        if category is None:
            return None

        # 3. Numeric density check
        if not self._check_numeric_density(text):
            return None

        # 4. Temporal column check (bonus score)
        has_temporal = self._check_temporal_columns(text)

        # 5. Calculate final confidence
        confidence = self._calculate_final_confidence(keyword_score, has_temporal)

        if confidence < self.min_confidence:
            return None

        return FinancialTable(
            page=candidate.page,
            bbox=candidate.bbox,
            category=category,
            confidence=confidence,
            matched_keywords=matched_keywords,
            detector_source=candidate.detector,
        )

    def _calculate_keyword_score(
        self,
        text: str,
    ) -> tuple[str | None, float, list[str]]:
        """Calculate keyword matching score.

        Args:
            text: Text content to analyze.

        Returns:
            Tuple of (best_category, confidence, matched_keywords).
            Returns (None, 0.0, []) if no category matches minimum requirements.
        """
        scores: dict[str, float] = {}
        all_matched: dict[str, list[str]] = {}

        for category, config in FINANCIAL_STATEMENT_PATTERNS.items():
            matched = [kw for kw in config["keywords"] if kw in text]
            if len(matched) >= config["min_matches"]:
                scores[category] = len(matched) * config["weight"]
                all_matched[category] = matched

        if not scores:
            return None, 0.0, []

        best_category = max(scores, key=lambda k: scores[k])
        # confidence: scale by number of matched keywords (0.0 ~ 1.0)
        confidence = min(scores[best_category] / 6.0, 1.0)

        return best_category, confidence, all_matched[best_category]

    def _check_numeric_density(
        self,
        text: str,
        threshold: float | None = None,
    ) -> bool:
        """Check if text has sufficient numeric token density.

        Financial statements typically have 20% or more numeric content.

        Args:
            text: Text content to analyze.
            threshold: Optional override for numeric density threshold.

        Returns:
            True if numeric density meets threshold, False otherwise.
        """
        threshold = threshold or self.numeric_density_threshold

        tokens = text.split()
        if not tokens:
            return False

        numeric_pattern = r"^[\d,.\-+()%]+$"
        numeric_count = sum(1 for t in tokens if re.match(numeric_pattern, t))

        return (numeric_count / len(tokens)) >= threshold

    def _check_temporal_columns(
        self,
        text: str,
        min_matches: int | None = None,
    ) -> bool:
        """Check if text contains sufficient temporal patterns.

        Args:
            text: Text content to analyze.
            min_matches: Optional override for minimum temporal matches.

        Returns:
            True if temporal patterns meet minimum requirement, False otherwise.
        """
        min_matches = min_matches or self.min_temporal_matches
        total_matches = 0

        for pattern in TEMPORAL_PATTERNS:
            matches = re.findall(pattern, text)
            total_matches += len(set(matches))  # Deduplicate matches

        return total_matches >= min_matches

    def _is_valid_table_size(
        self,
        bbox: BBox,
        page_width: float,
        page_height: float,
        row_count: int | None,
        col_count: int | None,
        min_area_ratio: float = 0.05,
        max_area_ratio: float = 0.95,
    ) -> bool:
        """Validate table size constraints.

        Requirements:
        - Minimum 3 rows, 2 columns
        - Table area between 5% and 95% of page area

        Args:
            bbox: Table bounding box.
            page_width: Page width.
            page_height: Page height.
            row_count: Number of rows (optional).
            col_count: Number of columns (optional).
            min_area_ratio: Minimum area ratio (default 5%).
            max_area_ratio: Maximum area ratio (default 95%).

        Returns:
            True if table size is valid, False otherwise.
        """
        # Check row/column counts
        if row_count is not None and row_count < 3:
            return False
        if col_count is not None and col_count < 2:
            return False

        # Check area ratio
        page_area = page_width * page_height
        table_area = bbox.area
        ratio = table_area / page_area

        return min_area_ratio <= ratio <= max_area_ratio

    def _calculate_final_confidence(
        self,
        keyword_score: float,
        has_temporal: bool,
    ) -> float:
        """Calculate final confidence score.

        Args:
            keyword_score: Base score from keyword matching.
            has_temporal: Whether temporal columns were detected.

        Returns:
            Final confidence score (0.0 ~ 1.0).
        """
        confidence = keyword_score

        # Add bonus for temporal columns
        if has_temporal:
            confidence = min(confidence + 0.1, 1.0)

        return confidence

    def _extract_text_from_bbox(
        self,
        pdf_path: str,
        page: int,
        bbox: BBox,
    ) -> str:
        """Extract text from a bounding box region in a PDF.

        Args:
            pdf_path: Path to the PDF file.
            page: Page number (1-indexed).
            bbox: Bounding box coordinates.

        Returns:
            Extracted text content.
        """
        import pdfplumber

        with pdfplumber.open(pdf_path) as pdf:
            page_obj = pdf.pages[page - 1]
            cropped = page_obj.within_bbox((bbox.x0, bbox.y0, bbox.x1, bbox.y1))
            text = cropped.extract_text() or ""

        return text
