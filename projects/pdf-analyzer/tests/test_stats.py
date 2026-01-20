"""Tests for multi-file statistics functionality."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from pdf_analyzer.cli import cli
from pdf_analyzer.analyzer import (
    CollectionStats,
    PDFStats,
    analyze_collection,
    analyze_single_pdf,
)


class TestAnalyzeSinglePDF:
    """Tests for analyze_single_pdf function."""

    def test_analyze_single_pdf_returns_stats(self, basic_pdf: Path):
        """Given: A valid PDF file
        When: analyze_single_pdf is called
        Then: PDFStats object is returned
        """
        stats = analyze_single_pdf(basic_pdf)

        assert isinstance(stats, PDFStats)

    def test_stats_has_correct_file_path(self, basic_pdf: Path):
        """Given: A valid PDF file
        When: analyze_single_pdf is called
        Then: file_path matches input
        """
        stats = analyze_single_pdf(basic_pdf)

        assert stats.file_path == basic_pdf

    def test_stats_has_positive_page_count(self, basic_pdf: Path):
        """Given: A valid PDF file
        When: analyze_single_pdf is called
        Then: page_count is positive
        """
        stats = analyze_single_pdf(basic_pdf)

        assert stats.page_count > 0

    def test_stats_has_nonnegative_totals(self, basic_pdf: Path):
        """Given: A valid PDF file
        When: analyze_single_pdf is called
        Then: All totals are non-negative
        """
        stats = analyze_single_pdf(basic_pdf)

        assert stats.total_chars >= 0
        assert stats.total_lines >= 0
        assert stats.total_images >= 0
        assert stats.total_tables >= 0

    def test_stats_page_sizes_match_page_count(self, multipage_pdf: Path):
        """Given: A multi-page PDF
        When: analyze_single_pdf is called
        Then: page_sizes has one entry per page
        """
        stats = analyze_single_pdf(multipage_pdf)

        assert len(stats.page_sizes) == stats.page_count

    def test_stats_fonts_is_dict(self, basic_pdf: Path):
        """Given: A PDF with text
        When: analyze_single_pdf is called
        Then: fonts is a dictionary
        """
        stats = analyze_single_pdf(basic_pdf)

        assert isinstance(stats.fonts, dict)

    def test_avg_chars_per_page_calculation(self, basic_pdf: Path):
        """Given: A PDF with known char count
        When: avg_chars_per_page is accessed
        Then: Correct average is returned
        """
        stats = analyze_single_pdf(basic_pdf)

        expected = stats.total_chars / stats.page_count
        assert stats.avg_chars_per_page == expected


class TestAnalyzeCollection:
    """Tests for analyze_collection function."""

    def test_analyze_collection_returns_stats(self, test_pdfs: dict[str, Path]):
        """Given: Multiple PDF files
        When: analyze_collection is called
        Then: CollectionStats object is returned
        """
        pdf_list = list(test_pdfs.values())
        stats = analyze_collection(pdf_list)

        assert isinstance(stats, CollectionStats)

    def test_collection_file_count_matches(self, test_pdfs: dict[str, Path]):
        """Given: Multiple PDF files
        When: analyze_collection is called
        Then: file_count matches input count
        """
        pdf_list = list(test_pdfs.values())
        stats = analyze_collection(pdf_list)

        assert stats.file_count == len(pdf_list)

    def test_collection_total_pages_positive(self, test_pdfs: dict[str, Path]):
        """Given: Multiple PDF files
        When: analyze_collection is called
        Then: total_pages is positive
        """
        pdf_list = list(test_pdfs.values())
        stats = analyze_collection(pdf_list)

        assert stats.total_pages > 0

    def test_collection_has_page_size_distribution(self, test_pdfs: dict[str, Path]):
        """Given: Multiple PDF files
        When: analyze_collection is called
        Then: page_size_distribution is populated
        """
        pdf_list = list(test_pdfs.values())
        stats = analyze_collection(pdf_list)

        assert isinstance(stats.page_size_distribution, dict)
        assert len(stats.page_size_distribution) > 0

    def test_collection_stats_have_required_keys(self, test_pdfs: dict[str, Path]):
        """Given: Multiple PDF files
        When: analyze_collection is called
        Then: Stats dicts have min, max, avg, median keys
        """
        pdf_list = list(test_pdfs.values())
        stats = analyze_collection(pdf_list)

        required_keys = {"min", "max", "avg", "median"}

        assert set(stats.chars_stats.keys()) == required_keys
        assert set(stats.lines_stats.keys()) == required_keys
        assert set(stats.images_stats.keys()) == required_keys
        assert set(stats.tables_stats.keys()) == required_keys

    def test_collection_handles_progress_callback(self, test_pdfs: dict[str, Path]):
        """Given: Multiple PDF files and a progress callback
        When: analyze_collection is called
        Then: Callback is invoked for each file
        """
        pdf_list = list(test_pdfs.values())
        progress_calls = []

        def on_progress(current, total, path):
            progress_calls.append((current, total, path))

        analyze_collection(pdf_list, on_progress=on_progress)

        assert len(progress_calls) == len(pdf_list)
        assert progress_calls[-1][0] == len(pdf_list)  # Last call is final

    def test_collection_handles_empty_list(self):
        """Given: Empty list of files
        When: analyze_collection is called
        Then: CollectionStats with zeros is returned
        """
        stats = analyze_collection([])

        assert stats.file_count == 0
        assert stats.total_pages == 0

    def test_collection_handles_nonexistent_file(self, basic_pdf: Path, tmp_path: Path):
        """Given: Mix of valid and nonexistent files
        When: analyze_collection is called
        Then: Errors are recorded, valid files are processed
        """
        nonexistent = tmp_path / "nonexistent.pdf"
        pdf_list = [basic_pdf, nonexistent]

        stats = analyze_collection(pdf_list)

        assert stats.file_count == 1  # Only valid file
        assert len(stats.errors) == 1  # One error


class TestStatsCommand:
    """Tests for the 'stats' CLI command."""

    def test_stats_command_runs_successfully(self, test_pdfs: dict[str, Path]):
        """Given: Multiple PDF files
        When: stats command is executed
        Then: Exit code should be 0
        """
        runner = CliRunner()
        pdf_paths = [str(p) for p in test_pdfs.values()]
        result = runner.invoke(cli, ["stats"] + pdf_paths)

        assert result.exit_code == 0

    def test_stats_command_shows_file_count(self, test_pdfs: dict[str, Path]):
        """Given: Multiple PDF files
        When: stats command is executed
        Then: Output shows file count
        """
        runner = CliRunner()
        pdf_paths = [str(p) for p in test_pdfs.values()]
        result = runner.invoke(cli, ["stats"] + pdf_paths)

        assert result.exit_code == 0
        assert "file" in result.output.lower()

    def test_stats_command_shows_page_distribution(self, test_pdfs: dict[str, Path]):
        """Given: Multiple PDF files
        When: stats command is executed
        Then: Output shows page size distribution
        """
        runner = CliRunner()
        pdf_paths = [str(p) for p in test_pdfs.values()]
        result = runner.invoke(cli, ["stats"] + pdf_paths)

        assert result.exit_code == 0
        assert "Distribution" in result.output or "Size" in result.output

    def test_stats_command_shows_content_stats(self, test_pdfs: dict[str, Path]):
        """Given: Multiple PDF files
        When: stats command is executed
        Then: Output shows content statistics
        """
        runner = CliRunner()
        pdf_paths = [str(p) for p in test_pdfs.values()]
        result = runner.invoke(cli, ["stats"] + pdf_paths)

        assert result.exit_code == 0
        assert "Characters" in result.output or "Chars" in result.output

    def test_stats_command_limit_option(self, test_pdfs: dict[str, Path]):
        """Given: Multiple PDF files
        When: stats --limit 2 is executed
        Then: Only 2 files are analyzed
        """
        runner = CliRunner()
        pdf_paths = [str(p) for p in test_pdfs.values()]
        result = runner.invoke(cli, ["stats", "--limit", "2"] + pdf_paths)

        assert result.exit_code == 0
        assert "2 file" in result.output

    def test_stats_command_no_files_fails(self):
        """Given: No PDF files
        When: stats command is executed
        Then: Exit code should be non-zero
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["stats"])

        assert result.exit_code != 0

    def test_stats_help_shows_options(self):
        """Given: stats command
        When: --help is passed
        Then: Output shows available options
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["stats", "--help"])

        assert result.exit_code == 0
        assert "--limit" in result.output
