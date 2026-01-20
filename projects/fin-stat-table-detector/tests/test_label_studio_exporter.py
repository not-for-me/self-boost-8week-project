"""Tests for Label Studio exporter."""

import json
from pathlib import Path

import pytest

from fin_stat_table_detector.exporters.converters import PageDimensions
from fin_stat_table_detector.exporters.label_studio import (
    LabelStudioAnnotation,
    LabelStudioExporter,
    LabelStudioTask,
)
from fin_stat_table_detector.models import BBox, FinancialTable


class TestLabelStudioAnnotation:
    """LabelStudioAnnotation 데이터 모델 테스트."""

    def test_to_dict_format(self) -> None:
        """Label Studio 어노테이션 형식으로 올바르게 변환됨."""
        # Given
        annotation = LabelStudioAnnotation(
            x=10.5,
            y=15.2,
            width=80.0,
            height=30.0,
            labels=["income_statement"],
            annotation_id="test123",
        )

        # When
        result = annotation.to_dict()

        # Then
        assert result["id"] == "test123"
        assert result["type"] == "rectanglelabels"
        assert result["from_name"] == "label"
        assert result["to_name"] == "image"
        assert result["value"]["x"] == 10.5
        assert result["value"]["y"] == 15.2
        assert result["value"]["width"] == 80.0
        assert result["value"]["height"] == 30.0
        assert result["value"]["rotation"] == 0
        assert result["value"]["rectanglelabels"] == ["income_statement"]

    def test_auto_generates_annotation_id(self) -> None:
        """어노테이션 ID가 자동 생성됨."""
        # Given / When
        annotation1 = LabelStudioAnnotation(
            x=0, y=0, width=100, height=100, labels=["test"]
        )
        annotation2 = LabelStudioAnnotation(
            x=0, y=0, width=100, height=100, labels=["test"]
        )

        # Then
        assert annotation1.annotation_id != annotation2.annotation_id
        assert len(annotation1.annotation_id) == 8

    def test_multiple_labels_supported(self) -> None:
        """여러 레이블을 지원함."""
        # Given
        annotation = LabelStudioAnnotation(
            x=0,
            y=0,
            width=100,
            height=100,
            labels=["income_statement", "consolidated"],
        )

        # When
        result = annotation.to_dict()

        # Then
        assert result["value"]["rectanglelabels"] == [
            "income_statement",
            "consolidated",
        ]


class TestLabelStudioTask:
    """LabelStudioTask 데이터 모델 테스트."""

    def test_task_to_dict_format(self) -> None:
        """Label Studio 태스크 형식으로 올바르게 변환됨."""
        # Given
        annotation = LabelStudioAnnotation(
            x=10.0,
            y=20.0,
            width=50.0,
            height=40.0,
            labels=["balance_sheet"],
            annotation_id="ann001",
        )
        task = LabelStudioTask(
            image_path="/images/page_001.jpg",
            annotations=[annotation],
            model_version="ensemble-v1",
        )

        # When
        result = task.to_dict()

        # Then
        assert result["data"]["image"] == "/images/page_001.jpg"
        assert "predictions" in result
        assert len(result["predictions"]) == 1
        assert result["predictions"][0]["model_version"] == "ensemble-v1"
        assert len(result["predictions"][0]["result"]) == 1

    def test_empty_task_has_no_predictions(self) -> None:
        """어노테이션이 없는 태스크는 predictions 키가 없음."""
        # Given
        task = LabelStudioTask(
            image_path="/images/page_002.jpg",
            annotations=[],
        )

        # When
        result = task.to_dict()

        # Then
        assert result["data"]["image"] == "/images/page_002.jpg"
        assert "predictions" not in result

    def test_multiple_annotations_in_task(self) -> None:
        """여러 어노테이션이 하나의 태스크에 포함됨."""
        # Given
        ann1 = LabelStudioAnnotation(
            x=10, y=10, width=30, height=20, labels=["income_statement"]
        )
        ann2 = LabelStudioAnnotation(
            x=50, y=50, width=40, height=30, labels=["balance_sheet"]
        )
        task = LabelStudioTask(
            image_path="/images/page.jpg",
            annotations=[ann1, ann2],
        )

        # When
        result = task.to_dict()

        # Then
        assert len(result["predictions"][0]["result"]) == 2


class TestLabelStudioExporter:
    """LabelStudioExporter 테스트."""

    def test_add_page_results_creates_task(self) -> None:
        """페이지 결과 추가 시 태스크가 생성됨."""
        # Given
        exporter = LabelStudioExporter()
        table = FinancialTable(
            page=1,
            bbox=BBox(x0=0, y0=0, x1=612, y1=792),
            category="income_statement",
            confidence=0.9,
            matched_keywords=["매출액"],
            detector_source="pdfplumber",
        )
        dims = PageDimensions(
            pdf_width=612.0,
            pdf_height=792.0,
            image_width=1224,
            image_height=1584,
        )

        # When
        exporter.add_page_results("/images/page_001.jpg", [table], dims)

        # Then
        assert exporter.task_count == 1
        result = exporter.to_list()
        assert len(result) == 1
        assert result[0]["data"]["image"] == "/images/page_001.jpg"

    def test_to_list_returns_correct_format(self) -> None:
        """to_list가 올바른 형식의 리스트를 반환함."""
        # Given
        exporter = LabelStudioExporter(model_version="test-v1")
        table = FinancialTable(
            page=1,
            bbox=BBox(x0=61.2, y0=79.2, x1=550.8, y1=712.8),
            category="balance_sheet",
            confidence=0.85,
            matched_keywords=["자산"],
            detector_source="camelot",
        )
        dims = PageDimensions(
            pdf_width=612.0,
            pdf_height=792.0,
            image_width=1224,
            image_height=1584,
        )

        # When
        exporter.add_page_results("/images/test.jpg", [table], dims)
        result = exporter.to_list()

        # Then
        assert len(result) == 1
        task = result[0]
        assert task["data"]["image"] == "/images/test.jpg"
        pred = task["predictions"][0]
        assert pred["model_version"] == "test-v1"
        ann = pred["result"][0]
        assert ann["value"]["x"] == pytest.approx(10.0, rel=1e-3)
        assert ann["value"]["y"] == pytest.approx(10.0, rel=1e-3)
        assert ann["value"]["rectanglelabels"] == ["balance_sheet"]

    def test_empty_tables_creates_task_without_predictions(self) -> None:
        """테이블이 없으면 predictions 없이 태스크 생성."""
        # Given
        exporter = LabelStudioExporter()
        dims = PageDimensions(
            pdf_width=612.0,
            pdf_height=792.0,
            image_width=1224,
            image_height=1584,
        )

        # When
        exporter.add_page_results("/images/empty.jpg", [], dims)
        result = exporter.to_list()

        # Then
        assert len(result) == 1
        assert result[0]["data"]["image"] == "/images/empty.jpg"
        assert "predictions" not in result[0]

    def test_save_creates_valid_json(self, tmp_path: Path) -> None:
        """JSON 파일이 올바르게 저장됨."""
        # Given
        exporter = LabelStudioExporter()
        table = FinancialTable(
            page=1,
            bbox=BBox(x0=100, y0=100, x1=500, y1=600),
            category="cash_flow",
            confidence=0.8,
            matched_keywords=["현금흐름"],
            detector_source="pdfplumber",
        )
        dims = PageDimensions(
            pdf_width=612.0,
            pdf_height=792.0,
            image_width=1224,
            image_height=1584,
        )
        exporter.add_page_results("/images/page.jpg", [table], dims)
        output_path = tmp_path / "output.json"

        # When
        exporter.save(output_path)

        # Then
        assert output_path.exists()
        with open(output_path, encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["data"]["image"] == "/images/page.jpg"

    def test_save_creates_parent_directories(self, tmp_path: Path) -> None:
        """부모 디렉토리가 없으면 자동 생성."""
        # Given
        exporter = LabelStudioExporter()
        dims = PageDimensions(612.0, 792.0, 1224, 1584)
        exporter.add_page_results("/images/test.jpg", [], dims)
        output_path = tmp_path / "subdir" / "deep" / "output.json"

        # When
        exporter.save(output_path)

        # Then
        assert output_path.exists()

    def test_save_preserves_korean_characters(self, tmp_path: Path) -> None:
        """한글 문자가 올바르게 저장됨."""
        # Given
        exporter = LabelStudioExporter()
        table = FinancialTable(
            page=1,
            bbox=BBox(x0=0, y0=0, x1=612, y1=792),
            category="income_statement",
            confidence=0.9,
            matched_keywords=["매출액", "영업이익"],
            detector_source="pdfplumber",
        )
        dims = PageDimensions(612.0, 792.0, 1224, 1584)
        exporter.add_page_results("/images/한글파일.jpg", [table], dims)
        output_path = tmp_path / "korean.json"

        # When
        exporter.save(output_path)

        # Then
        with open(output_path, encoding="utf-8") as f:
            content = f.read()
        assert "한글파일" in content

    def test_clear_removes_all_tasks(self) -> None:
        """clear 호출 시 모든 태스크가 제거됨."""
        # Given
        exporter = LabelStudioExporter()
        dims = PageDimensions(612.0, 792.0, 1224, 1584)
        exporter.add_page_results("/images/1.jpg", [], dims)
        exporter.add_page_results("/images/2.jpg", [], dims)
        assert exporter.task_count == 2

        # When
        exporter.clear()

        # Then
        assert exporter.task_count == 0
        assert exporter.to_list() == []

    def test_multiple_pages_added_sequentially(self) -> None:
        """여러 페이지가 순차적으로 추가됨."""
        # Given
        exporter = LabelStudioExporter()
        dims = PageDimensions(612.0, 792.0, 1224, 1584)

        # When
        for i in range(5):
            exporter.add_page_results(f"/images/page_{i:03d}.jpg", [], dims)

        # Then
        assert exporter.task_count == 5
        result = exporter.to_list()
        assert len(result) == 5
        for i, task in enumerate(result):
            assert task["data"]["image"] == f"/images/page_{i:03d}.jpg"
