"""Tests for ProcessingConfig and ProcessingResult dataclasses."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from fin_stat_table_detector.processing.config import (
    PageResult,
    ProcessingConfig,
    ProcessingResult,
)


class TestProcessingConfig:
    """ProcessingConfig dataclass tests."""

    def test_create_with_required_fields(self, tmp_path: Path) -> None:
        """이미지 디렉토리만으로 생성 가능."""
        # When
        config = ProcessingConfig(images_dir=tmp_path)

        # Then
        assert config.images_dir == tmp_path
        assert config.dpi == 150  # default
        assert config.summary_only is False  # default

    def test_create_with_all_fields(self, tmp_path: Path) -> None:
        """모든 필드를 지정하여 생성."""
        # When
        config = ProcessingConfig(
            images_dir=tmp_path,
            dpi=300,
            summary_only=True,
        )

        # Then
        assert config.images_dir == tmp_path
        assert config.dpi == 300
        assert config.summary_only is True


class TestPageResult:
    """PageResult dataclass tests."""

    def test_create_page_result(self, tmp_path: Path) -> None:
        """PageResult 생성."""
        # Given
        image_path = tmp_path / "page_001.jpg"
        dims = MagicMock()

        # When
        result = PageResult(
            page_num=1,
            image_path=image_path,
            dimensions=dims,
        )

        # Then
        assert result.page_num == 1
        assert result.image_path == image_path
        assert result.dimensions == dims


class TestProcessingResult:
    """ProcessingResult dataclass tests."""

    def test_create_with_defaults(self, tmp_path: Path) -> None:
        """기본값으로 생성."""
        # Given
        pdf_path = tmp_path / "test.pdf"

        # When
        result = ProcessingResult(pdf_path=pdf_path)

        # Then
        assert result.pdf_path == pdf_path
        assert result.pages == 0
        assert result.tables == []
        assert result.page_results == []
        assert result.error is None

    def test_tables_detected_property(self, tmp_path: Path) -> None:
        """tables_detected는 테이블 개수 반환."""
        # Given
        pdf_path = tmp_path / "test.pdf"
        tables = [MagicMock(), MagicMock(), MagicMock()]

        # When
        result = ProcessingResult(pdf_path=pdf_path, tables=tables)

        # Then
        assert result.tables_detected == 3

    def test_categories_property(self, tmp_path: Path) -> None:
        """categories는 카테고리별 개수 반환."""
        # Given
        pdf_path = tmp_path / "test.pdf"
        table1 = MagicMock(category="income_statement")
        table2 = MagicMock(category="balance_sheet")
        table3 = MagicMock(category="income_statement")

        # When
        result = ProcessingResult(pdf_path=pdf_path, tables=[table1, table2, table3])

        # Then
        assert result.categories == {"income_statement": 2, "balance_sheet": 1}

    def test_is_success_true_when_no_error(self, tmp_path: Path) -> None:
        """에러 없으면 is_success는 True."""
        # When
        result = ProcessingResult(pdf_path=tmp_path / "test.pdf")

        # Then
        assert result.is_success is True

    def test_is_success_false_when_error(self, tmp_path: Path) -> None:
        """에러 있으면 is_success는 False."""
        # When
        result = ProcessingResult(
            pdf_path=tmp_path / "test.pdf",
            error="Something went wrong",
        )

        # Then
        assert result.is_success is False

    def test_to_dict_basic(self, tmp_path: Path) -> None:
        """to_dict는 기본 필드를 포함."""
        # Given
        pdf_path = tmp_path / "test.pdf"
        table = MagicMock(category="income_statement")

        result = ProcessingResult(
            pdf_path=pdf_path,
            pages=5,
            tables=[table],
        )

        # When
        d = result.to_dict()

        # Then
        assert d["pdf_path"] == str(pdf_path)
        assert d["pages"] == 5
        assert d["tables_detected"] == 1
        assert d["categories"] == {"income_statement": 1}
        assert d["tables"] == [table]

    def test_to_dict_with_error(self, tmp_path: Path) -> None:
        """to_dict는 에러가 있으면 error 필드 포함."""
        # Given
        result = ProcessingResult(
            pdf_path=tmp_path / "test.pdf",
            error="Test error",
        )

        # When
        d = result.to_dict()

        # Then
        assert "error" in d
        assert d["error"] == "Test error"

    def test_to_dict_with_page_results(self, tmp_path: Path) -> None:
        """to_dict는 page_results를 튜플 리스트로 변환."""
        # Given
        dims = MagicMock()
        page_result = PageResult(
            page_num=1,
            image_path=tmp_path / "page_001.jpg",
            dimensions=dims,
        )
        result = ProcessingResult(
            pdf_path=tmp_path / "test.pdf",
            pages=1,
            page_results=[page_result],
        )

        # When
        d = result.to_dict()

        # Then
        assert "page_results" in d
        assert len(d["page_results"]) == 1
        assert d["page_results"][0][0] == 1
        assert d["page_results"][0][1] == str(tmp_path / "page_001.jpg")
        assert d["page_results"][0][2] == dims
