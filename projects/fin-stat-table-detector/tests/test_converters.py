"""Tests for coordinate conversion utilities."""

import pytest

from fin_stat_table_detector.exporters.converters import (
    PageDimensions,
    bbox_to_label_studio,
)
from fin_stat_table_detector.models import BBox


class TestPageDimensions:
    """PageDimensions 데이터 모델 테스트."""

    def test_create_page_dimensions(self) -> None:
        """페이지 크기 정보를 올바르게 생성함."""
        # Given / When
        dims = PageDimensions(
            pdf_width=612.0,
            pdf_height=792.0,
            image_width=1224,
            image_height=1584,
        )

        # Then
        assert dims.pdf_width == 612.0
        assert dims.pdf_height == 792.0
        assert dims.image_width == 1224
        assert dims.image_height == 1584


class TestBboxToLabelStudio:
    """BBox → Label Studio 좌표 변환 테스트."""

    def test_full_page_bbox_converts_to_100_percent(self) -> None:
        """전체 페이지 BBox는 (0, 0, 100, 100)으로 변환됨."""
        # Given
        bbox = BBox(x0=0, y0=0, x1=612, y1=792)
        dims = PageDimensions(
            pdf_width=612.0,
            pdf_height=792.0,
            image_width=1224,
            image_height=1584,
        )

        # When
        result = bbox_to_label_studio(bbox, dims)

        # Then
        assert result["x"] == 0.0
        assert result["y"] == 0.0
        assert result["width"] == 100.0
        assert result["height"] == 100.0

    def test_half_page_bbox_converts_correctly(self) -> None:
        """절반 크기 BBox는 (0, 0, 50, 50)으로 변환됨."""
        # Given
        bbox = BBox(x0=0, y0=0, x1=306, y1=396)
        dims = PageDimensions(
            pdf_width=612.0,
            pdf_height=792.0,
            image_width=1224,
            image_height=1584,
        )

        # When
        result = bbox_to_label_studio(bbox, dims)

        # Then
        assert result["x"] == 0.0
        assert result["y"] == 0.0
        assert result["width"] == 50.0
        assert result["height"] == 50.0

    def test_centered_bbox_converts_correctly(self) -> None:
        """중앙에 위치한 BBox가 올바르게 변환됨."""
        # Given: 중앙 25% 영역 (12.5%~37.5% on each axis)
        # 612 * 0.125 = 76.5, 612 * 0.375 = 229.5 => width 153 (25%)
        # 792 * 0.125 = 99, 792 * 0.375 = 297 => height 198 (25%)
        bbox = BBox(x0=153, y0=198, x1=459, y1=594)
        dims = PageDimensions(
            pdf_width=612.0,
            pdf_height=792.0,
            image_width=1224,
            image_height=1584,
        )

        # When
        result = bbox_to_label_studio(bbox, dims)

        # Then
        assert result["x"] == 25.0
        assert result["y"] == 25.0
        assert result["width"] == 50.0
        assert result["height"] == 50.0

    def test_arbitrary_bbox_converts_with_precision(self) -> None:
        """임의의 BBox가 정밀하게 변환됨."""
        # Given
        bbox = BBox(x0=100, y0=150, x1=400, y1=500)
        dims = PageDimensions(
            pdf_width=612.0,
            pdf_height=792.0,
            image_width=1224,
            image_height=1584,
        )

        # When
        result = bbox_to_label_studio(bbox, dims)

        # Then
        assert result["x"] == pytest.approx(100 / 612 * 100, rel=1e-5)
        assert result["y"] == pytest.approx(150 / 792 * 100, rel=1e-5)
        assert result["width"] == pytest.approx(300 / 612 * 100, rel=1e-5)
        assert result["height"] == pytest.approx(350 / 792 * 100, rel=1e-5)

    def test_zero_size_bbox_converts_to_zero_dimensions(self) -> None:
        """크기가 0인 BBox는 width/height 0으로 변환됨."""
        # Given
        bbox = BBox(x0=100, y0=100, x1=100, y1=100)
        dims = PageDimensions(
            pdf_width=612.0,
            pdf_height=792.0,
            image_width=1224,
            image_height=1584,
        )

        # When
        result = bbox_to_label_studio(bbox, dims)

        # Then
        assert result["width"] == 0.0
        assert result["height"] == 0.0

    def test_raises_error_for_zero_page_width(self) -> None:
        """페이지 너비가 0이면 ValueError 발생."""
        # Given
        bbox = BBox(x0=0, y0=0, x1=100, y1=100)
        dims = PageDimensions(
            pdf_width=0.0,
            pdf_height=792.0,
            image_width=1224,
            image_height=1584,
        )

        # When / Then
        with pytest.raises(ValueError, match="Page dimensions must be positive"):
            bbox_to_label_studio(bbox, dims)

    def test_raises_error_for_zero_page_height(self) -> None:
        """페이지 높이가 0이면 ValueError 발생."""
        # Given
        bbox = BBox(x0=0, y0=0, x1=100, y1=100)
        dims = PageDimensions(
            pdf_width=612.0,
            pdf_height=0.0,
            image_width=1224,
            image_height=1584,
        )

        # When / Then
        with pytest.raises(ValueError, match="Page dimensions must be positive"):
            bbox_to_label_studio(bbox, dims)

    def test_raises_error_for_negative_page_dimensions(self) -> None:
        """페이지 크기가 음수이면 ValueError 발생."""
        # Given
        bbox = BBox(x0=0, y0=0, x1=100, y1=100)
        dims = PageDimensions(
            pdf_width=-612.0,
            pdf_height=792.0,
            image_width=1224,
            image_height=1584,
        )

        # When / Then
        with pytest.raises(ValueError, match="Page dimensions must be positive"):
            bbox_to_label_studio(bbox, dims)
