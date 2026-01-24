"""Tests for PdfProcessor class."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from fin_stat_table_detector.processing.config import ProcessingConfig
from fin_stat_table_detector.processing.pdf_processor import PdfProcessor


class TestPdfProcessorInit:
    """PdfProcessor initialization tests."""

    def test_init_stores_detector_and_config(self, tmp_path: Path) -> None:
        """초기화 시 detector와 config 저장."""
        # Given
        mock_detector = MagicMock()
        config = ProcessingConfig(images_dir=tmp_path)

        # When
        processor = PdfProcessor(detector=mock_detector, config=config)

        # Then
        assert processor.detector == mock_detector
        assert processor.config == config


class TestPdfProcessorProcess:
    """PdfProcessor process method tests."""

    def test_process_returns_result_with_tables(self, tmp_path: Path) -> None:
        """process는 감지된 테이블과 함께 결과 반환."""
        # Given
        mock_detector = MagicMock()
        mock_table = MagicMock(category="income_statement")
        mock_detector.detect_financial_tables.return_value = [mock_table]

        config = ProcessingConfig(images_dir=tmp_path, summary_only=True)
        processor = PdfProcessor(detector=mock_detector, config=config)

        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\n"
            b"xref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n"
            b"0000000052 00000 n\n0000000101 00000 n\ntrailer\n"
            b"<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF"
        )

        # When
        result = processor.process(pdf_path)

        # Then
        assert result.is_success
        assert result.tables_detected == 1
        assert result.tables[0] == mock_table
        mock_detector.detect_financial_tables.assert_called_once_with(str(pdf_path))

    def test_process_catches_exception(self, tmp_path: Path) -> None:
        """process는 예외 발생 시 에러 결과 반환."""
        # Given
        mock_detector = MagicMock()
        mock_detector.detect_financial_tables.side_effect = Exception("Test error")

        config = ProcessingConfig(images_dir=tmp_path)
        processor = PdfProcessor(detector=mock_detector, config=config)

        # When
        result = processor.process(tmp_path / "test.pdf")

        # Then
        assert not result.is_success
        assert "Test error" in result.error

    def test_process_with_summary_only_skips_images(self, tmp_path: Path) -> None:
        """summary_only=True면 이미지 변환 생략."""
        # Given
        mock_detector = MagicMock()
        mock_detector.detect_financial_tables.return_value = []

        config = ProcessingConfig(images_dir=tmp_path, summary_only=True)
        processor = PdfProcessor(detector=mock_detector, config=config)

        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\n"
            b"xref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n"
            b"0000000052 00000 n\n0000000101 00000 n\ntrailer\n"
            b"<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF"
        )

        # When
        with patch(
            "fin_stat_table_detector.processing.pdf_processor.convert_pdf_to_images"
        ) as mock_convert:
            result = processor.process(pdf_path)

        # Then
        mock_convert.assert_not_called()
        assert result.page_results == []


