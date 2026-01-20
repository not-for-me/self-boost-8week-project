"""Tests for CLI commands."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from fin_stat_table_detector.cli.commands.detect import (
    create_detectors,
    detect,
    find_pdf_files,
)
from fin_stat_table_detector.cli.main import main


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


class TestMainCLI:
    """Main CLI 테스트."""

    def test_main_shows_help(self, runner: CliRunner) -> None:
        """메인 명령어 도움말이 출력됨."""
        # When
        result = runner.invoke(main, ["--help"])

        # Then
        assert result.exit_code == 0
        assert "Financial statement table detector CLI" in result.output
        assert "detect" in result.output

    def test_main_shows_version(self, runner: CliRunner) -> None:
        """버전 정보가 출력됨."""
        # When
        result = runner.invoke(main, ["--version"])

        # Then
        assert result.exit_code == 0
        assert "0.1.0" in result.output


class TestDetectCommand:
    """detect 명령어 테스트."""

    def test_detect_command_shows_help(self, runner: CliRunner) -> None:
        """detect 명령어 도움말이 출력됨."""
        # When
        result = runner.invoke(detect, ["--help"])

        # Then
        assert result.exit_code == 0
        assert "Detect financial tables in PDF files" in result.output
        assert "--output" in result.output
        assert "--images-dir" in result.output
        assert "--dpi" in result.output
        assert "--dry-run" in result.output
        assert "--summary-only" in result.output
        assert "--parallel" in result.output
        assert "--workers" in result.output

    def test_detect_nonexistent_file_fails(self, runner: CliRunner) -> None:
        """존재하지 않는 파일은 오류 발생."""
        # When
        result = runner.invoke(detect, ["/nonexistent/path/file.pdf"])

        # Then
        assert result.exit_code != 0
        assert (
            "does not exist" in result.output.lower()
            or "invalid" in result.output.lower()
        )

    def test_detect_dry_run_lists_files(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """dry-run 모드에서 처리할 파일 목록이 출력됨."""
        # Given
        pdf1 = tmp_path / "report1.pdf"
        pdf2 = tmp_path / "report2.pdf"
        pdf1.touch()
        pdf2.touch()

        # When
        result = runner.invoke(detect, [str(tmp_path), "--dry-run"])

        # Then
        assert result.exit_code == 0
        assert "Files to process" in result.output
        assert "report1.pdf" in result.output
        assert "report2.pdf" in result.output

    def test_detect_dry_run_empty_directory(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """빈 디렉토리에서 dry-run 시 파일 없음 메시지 출력."""
        # When
        result = runner.invoke(detect, [str(tmp_path), "--dry-run"])

        # Then
        assert result.exit_code == 0
        assert "No PDF files found" in result.output

class TestFindPdfFiles:
    """find_pdf_files 함수 테스트."""

    def test_find_single_pdf_file(self, tmp_path: Path) -> None:
        """단일 PDF 파일을 찾음."""
        # Given
        pdf_file = tmp_path / "test.pdf"
        pdf_file.touch()

        # When
        result = find_pdf_files(pdf_file)

        # Then
        assert len(result) == 1
        assert result[0] == pdf_file

    def test_find_pdf_files_in_directory(self, tmp_path: Path) -> None:
        """디렉토리에서 PDF 파일을 재귀적으로 찾음."""
        # Given
        (tmp_path / "file1.pdf").touch()
        (tmp_path / "file2.pdf").touch()
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file3.pdf").touch()
        (tmp_path / "not_pdf.txt").touch()

        # When
        result = find_pdf_files(tmp_path)

        # Then
        assert len(result) == 3
        names = {f.name for f in result}
        assert names == {"file1.pdf", "file2.pdf", "file3.pdf"}

    def test_find_pdf_files_returns_sorted(self, tmp_path: Path) -> None:
        """결과가 정렬되어 반환됨."""
        # Given
        (tmp_path / "z_report.pdf").touch()
        (tmp_path / "a_report.pdf").touch()
        (tmp_path / "m_report.pdf").touch()

        # When
        result = find_pdf_files(tmp_path)

        # Then
        assert result[0].name == "a_report.pdf"
        assert result[1].name == "m_report.pdf"
        assert result[2].name == "z_report.pdf"

    def test_non_pdf_file_returns_empty(self, tmp_path: Path) -> None:
        """PDF가 아닌 파일은 빈 리스트 반환."""
        # Given
        txt_file = tmp_path / "test.txt"
        txt_file.touch()

        # When
        result = find_pdf_files(txt_file)

        # Then
        assert result == []


class TestCreateDetectors:
    """create_detectors 함수 테스트."""

    def test_creates_docling_detector(self) -> None:
        """docling detector를 생성함."""
        # When
        detectors = create_detectors()

        # Then
        assert len(detectors) == 1
        assert detectors[0].name == "docling"


class TestDetectCommandIntegration:
    """detect 명령어 통합 테스트."""

    def test_detect_with_summary_only(self, runner: CliRunner, tmp_path: Path) -> None:
        """summary-only 모드에서 이미지 생성 없이 요약만 출력."""
        # Given - Create a minimal valid PDF
        pdf_file = tmp_path / "test.pdf"
        # Create a minimal PDF (empty but valid structure)
        pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer
<< /Size 4 /Root 1 0 R >>
startxref
196
%%EOF"""
        pdf_file.write_bytes(pdf_content)

        # When
        result = runner.invoke(detect, [str(pdf_file), "--summary-only"])

        # Then
        assert result.exit_code == 0
        assert "Detection Summary" in result.output
        # Should not create images directory contents
        images_dir = tmp_path / "images"
        assert not images_dir.exists() or not list(images_dir.glob("*.jpg"))
