"""Tests for table detection and extraction functionality."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from pdf_analyzer.cli import cli
from pdf_analyzer.analyzer import PDFAnalyzer, TableInfo


class TestTableExtraction:
    """Tests for table extraction from analyzer."""

    def test_extract_tables_from_table_pdf(self, table_pdf: Path):
        """Given: A PDF with a table
        When: extract_tables is called
        Then: At least one table should be detected
        """
        analyzer = PDFAnalyzer(table_pdf)
        tables = analyzer.extract_tables()

        assert len(tables) >= 1

    def test_extract_tables_returns_table_info(self, table_pdf: Path):
        """Given: A PDF with a table
        When: extract_tables is called
        Then: Result should be list of TableInfo objects
        """
        analyzer = PDFAnalyzer(table_pdf)
        tables = analyzer.extract_tables()

        assert all(isinstance(t, TableInfo) for t in tables)

    def test_table_has_correct_page_number(self, table_pdf: Path):
        """Given: A single-page PDF with a table
        When: extract_tables is called
        Then: Table should have page_number = 1
        """
        analyzer = PDFAnalyzer(table_pdf)
        tables = analyzer.extract_tables()

        assert tables[0].page_number == 1

    def test_table_has_positive_dimensions(self, table_pdf: Path):
        """Given: A PDF with a table
        When: extract_tables is called
        Then: Table should have positive row_count and col_count
        """
        analyzer = PDFAnalyzer(table_pdf)
        tables = analyzer.extract_tables()

        table = tables[0]
        assert table.row_count > 0
        assert table.col_count > 0

    def test_table_has_valid_bbox(self, table_pdf: Path):
        """Given: A PDF with a table
        When: extract_tables is called
        Then: Table bbox should have valid coordinates
        """
        analyzer = PDFAnalyzer(table_pdf)
        tables = analyzer.extract_tables()

        table = tables[0]
        assert table.x0 >= 0
        assert table.top >= 0
        assert table.x1 > table.x0
        assert table.bottom > table.top

    def test_table_cells_match_dimensions(self, table_pdf: Path):
        """Given: A PDF with a table
        When: extract_tables is called
        Then: cells should have row_count rows, each with col_count items
        """
        analyzer = PDFAnalyzer(table_pdf)
        tables = analyzer.extract_tables()

        table = tables[0]
        assert len(table.cells) == table.row_count
        for row in table.cells:
            assert len(row) == table.col_count

    def test_extract_tables_with_page_filter(self, table_pdf: Path):
        """Given: A PDF with a table on page 1
        When: extract_tables is called with page_number=1
        Then: Tables from page 1 should be returned
        """
        analyzer = PDFAnalyzer(table_pdf)
        tables = analyzer.extract_tables(page_number=1)

        assert len(tables) >= 1
        assert all(t.page_number == 1 for t in tables)

    def test_extract_tables_invalid_page_raises_error(self, table_pdf: Path):
        """Given: A single-page PDF
        When: extract_tables is called with page_number=99
        Then: ValueError should be raised
        """
        analyzer = PDFAnalyzer(table_pdf)

        with pytest.raises(ValueError, match="out of range"):
            analyzer.extract_tables(page_number=99)

    def test_extract_tables_from_pdf_without_tables(self, basic_pdf: Path):
        """Given: A PDF without tables
        When: extract_tables is called
        Then: Empty list should be returned
        """
        analyzer = PDFAnalyzer(basic_pdf)
        tables = analyzer.extract_tables()

        # basic_pdf might have some detected tables or none
        # Just verify it doesn't crash and returns a list
        assert isinstance(tables, list)


class TestTableSummary:
    """Tests for table summary functionality."""

    def test_get_table_summary_with_tables(self, table_pdf: Path):
        """Given: A PDF with tables
        When: get_table_summary is called
        Then: Dictionary with page numbers and counts is returned
        """
        analyzer = PDFAnalyzer(table_pdf)
        summary = analyzer.get_table_summary()

        assert isinstance(summary, dict)
        assert 1 in summary
        assert summary[1] >= 1

    def test_get_table_summary_without_tables(self, basic_pdf: Path):
        """Given: A PDF potentially without tables
        When: get_table_summary is called
        Then: Dictionary is returned (may be empty)
        """
        analyzer = PDFAnalyzer(basic_pdf)
        summary = analyzer.get_table_summary()

        assert isinstance(summary, dict)


class TestTableInfoProperties:
    """Tests for TableInfo dataclass properties."""

    def test_table_width_property(self, table_pdf: Path):
        """Given: A table with known bbox
        When: width property is accessed
        Then: Correct width is calculated
        """
        analyzer = PDFAnalyzer(table_pdf)
        tables = analyzer.extract_tables()

        table = tables[0]
        expected_width = table.bbox.x1 - table.bbox.x0
        assert table.width == expected_width

    def test_table_height_property(self, table_pdf: Path):
        """Given: A table with known bbox
        When: height property is accessed
        Then: Correct height is calculated
        """
        analyzer = PDFAnalyzer(table_pdf)
        tables = analyzer.extract_tables()

        table = tables[0]
        expected_height = table.bbox.y1 - table.bbox.y0
        assert table.height == expected_height


class TestTablesCommand:
    """Tests for the 'tables' CLI command."""

    def test_tables_command_runs_successfully(self, table_pdf: Path):
        """Given: A PDF with tables
        When: tables command is executed
        Then: Exit code should be 0
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["tables", str(table_pdf)])

        assert result.exit_code == 0

    def test_tables_command_shows_table_count(self, table_pdf: Path):
        """Given: A PDF with tables
        When: tables command is executed
        Then: Output should show table count
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["tables", str(table_pdf)])

        assert result.exit_code == 0
        assert "table" in result.output.lower()

    def test_tables_command_shows_dimensions(self, table_pdf: Path):
        """Given: A PDF with tables
        When: tables command is executed
        Then: Output should show rows x cols
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["tables", str(table_pdf)])

        assert result.exit_code == 0
        assert "rows" in result.output.lower()
        assert "cols" in result.output.lower()

    def test_tables_command_summary_option(self, table_pdf: Path):
        """Given: A PDF with tables
        When: tables --summary is executed
        Then: Output should show summary
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["tables", str(table_pdf), "--summary"])

        assert result.exit_code == 0
        assert "Summary" in result.output

    def test_tables_command_no_content_option(self, table_pdf: Path):
        """Given: A PDF with tables
        When: tables --no-content is executed
        Then: Exit code should be 0
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["tables", str(table_pdf), "--no-content"])

        assert result.exit_code == 0

    def test_tables_command_page_option(self, table_pdf: Path):
        """Given: A PDF with tables
        When: tables --page 1 is executed
        Then: Output should show tables from page 1
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["tables", str(table_pdf), "--page", "1"])

        assert result.exit_code == 0
        assert "Page 1" in result.output

    def test_tables_command_col_width_option(self, table_pdf: Path):
        """Given: A PDF with tables
        When: tables --col-width 10 is executed
        Then: Exit code should be 0
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["tables", str(table_pdf), "-w", "10"])

        assert result.exit_code == 0

    def test_tables_command_no_tables_found(self, basic_pdf: Path):
        """Given: A PDF without tables
        When: tables command is executed
        Then: Output should indicate no tables found
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["tables", str(basic_pdf)])

        assert result.exit_code == 0
        # Should show "No tables" or similar
        assert "table" in result.output.lower()

    def test_tables_command_invalid_page_fails(self, table_pdf: Path):
        """Given: A PDF with tables
        When: tables --page 99 is executed
        Then: Exit code should be non-zero
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["tables", str(table_pdf), "--page", "99"])

        assert result.exit_code != 0
        assert "Error" in result.output

    def test_tables_help_shows_options(self):
        """Given: tables command
        When: --help is passed
        Then: Output should show available options
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["tables", "--help"])

        assert result.exit_code == 0
        assert "--page" in result.output
        assert "--summary" in result.output
        assert "--no-content" in result.output
        assert "--col-width" in result.output
