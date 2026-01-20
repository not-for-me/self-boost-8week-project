"""Tests for ASCII visualization functionality."""

from pathlib import Path

from click.testing import CliRunner

from pdf_analyzer.cli import cli
from pdf_analyzer.analyzer import PDFAnalyzer
from pdf_analyzer.visualizer import ASCIIVisualizer, VisualConfig, create_simple_visual


class TestASCIIVisualizer:
    """Tests for ASCIIVisualizer class."""

    def test_visualize_page_returns_string(self, basic_pdf: Path):
        """Given: A PDF page analysis
        When: visualize_page is called
        Then: A non-empty string is returned
        """
        analyzer = PDFAnalyzer(basic_pdf)
        analysis = analyzer.analyze_page(1)

        visualizer = ASCIIVisualizer()
        result = visualize_page = visualizer.visualize_page(analysis)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_visualize_page_contains_page_info(self, basic_pdf: Path):
        """Given: A PDF page analysis
        When: visualize_page is called
        Then: Output contains page number and dimensions
        """
        analyzer = PDFAnalyzer(basic_pdf)
        analysis = analyzer.analyze_page(1)

        visualizer = ASCIIVisualizer()
        result = visualizer.visualize_page(analysis)

        assert "Page 1" in result
        assert "595" in result  # A4 width

    def test_visualize_page_contains_legend(self, basic_pdf: Path):
        """Given: A PDF page analysis
        When: visualize_page is called
        Then: Output contains legend
        """
        analyzer = PDFAnalyzer(basic_pdf)
        analysis = analyzer.analyze_page(1)

        visualizer = ASCIIVisualizer()
        result = visualizer.visualize_page(analysis)

        assert "Legend" in result

    def test_custom_config_changes_dimensions(self, basic_pdf: Path):
        """Given: A custom VisualConfig with specific dimensions
        When: visualize_page is called
        Then: Output respects the configured dimensions
        """
        analyzer = PDFAnalyzer(basic_pdf)
        analysis = analyzer.analyze_page(1)

        config = VisualConfig(width=40, height=20)
        visualizer = ASCIIVisualizer(config)
        result = visualizer.visualize_page(analysis)

        lines = result.split("\n")
        # Find the grid lines (between borders)
        grid_lines = [l for l in lines if l.startswith("|") and l.endswith("|")]

        # Grid height should match config
        assert len(grid_lines) == 20

    def test_visualize_with_tables(self, table_pdf: Path):
        """Given: A PDF with tables
        When: visualize_page is called with tables
        Then: Output includes table markers
        """
        analyzer = PDFAnalyzer(table_pdf)
        analysis = analyzer.analyze_page(1)
        tables = analyzer.extract_tables(page_number=1)

        visualizer = ASCIIVisualizer()
        result = visualizer.visualize_page(analysis, tables=tables)

        # Should contain table corner character
        assert "\u256c" in result or "\u2500" in result or "\u2502" in result


class TestCreateSimpleVisual:
    """Tests for create_simple_visual helper function."""

    def test_create_simple_visual_returns_string(self, basic_pdf: Path):
        """Given: A PDF page analysis
        When: create_simple_visual is called
        Then: A string is returned
        """
        analyzer = PDFAnalyzer(basic_pdf)
        analysis = analyzer.analyze_page(1)

        result = create_simple_visual(analysis)

        assert isinstance(result, str)

    def test_create_simple_visual_custom_size(self, basic_pdf: Path):
        """Given: Custom width and height
        When: create_simple_visual is called
        Then: Output respects the specified dimensions
        """
        analyzer = PDFAnalyzer(basic_pdf)
        analysis = analyzer.analyze_page(1)

        result = create_simple_visual(analysis, width=50, height=25)

        lines = result.split("\n")
        grid_lines = [l for l in lines if l.startswith("|") and l.endswith("|")]

        assert len(grid_lines) == 25


class TestVisualCommand:
    """Tests for the 'visual' CLI command."""

    def test_visual_command_runs_successfully(self, basic_pdf: Path):
        """Given: A valid PDF file
        When: visual command is executed
        Then: Exit code should be 0
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["visual", str(basic_pdf)])

        assert result.exit_code == 0

    def test_visual_command_shows_page_info(self, basic_pdf: Path):
        """Given: A valid PDF file
        When: visual command is executed
        Then: Output contains page information
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["visual", str(basic_pdf)])

        assert result.exit_code == 0
        assert "Page 1" in result.output

    def test_visual_command_page_option(self, multipage_pdf: Path):
        """Given: A multi-page PDF
        When: visual --page 2 is executed
        Then: Output shows page 2
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["visual", str(multipage_pdf), "--page", "2"])

        assert result.exit_code == 0
        assert "Page 2" in result.output

    def test_visual_command_with_tables_option(self, table_pdf: Path):
        """Given: A PDF with tables
        When: visual --with-tables is executed
        Then: Exit code should be 0
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["visual", str(table_pdf), "--with-tables"])

        assert result.exit_code == 0

    def test_visual_command_custom_dimensions(self, basic_pdf: Path):
        """Given: A valid PDF file
        When: visual --width 40 --height 20 is executed
        Then: Exit code should be 0
        """
        runner = CliRunner()
        result = runner.invoke(
            cli, ["visual", str(basic_pdf), "--width", "40", "--height", "20"]
        )

        assert result.exit_code == 0

    def test_visual_command_invalid_page_fails(self, basic_pdf: Path):
        """Given: A single-page PDF
        When: visual --page 99 is executed
        Then: Exit code should be non-zero
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["visual", str(basic_pdf), "--page", "99"])

        assert result.exit_code != 0
        assert "Error" in result.output

    def test_visual_help_shows_options(self):
        """Given: visual command
        When: --help is passed
        Then: Output shows available options
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["visual", "--help"])

        assert result.exit_code == 0
        assert "--page" in result.output
        assert "--width" in result.output
        assert "--height" in result.output
        assert "--with-tables" in result.output
