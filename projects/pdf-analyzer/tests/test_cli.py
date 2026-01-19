"""Tests for CLI commands."""

from pathlib import Path

from click.testing import CliRunner

from main import cli


class TestInfoCommand:
    """Tests for the 'info' CLI command."""

    def test_info_command_runs_successfully(self, basic_pdf: Path):
        """Given: A valid PDF file
        When: info command is executed
        Then: Exit code should be 0
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["info", str(basic_pdf)])

        assert result.exit_code == 0

    def test_info_command_shows_page_count(self, multipage_pdf: Path):
        """Given: A 3-page PDF file
        When: info command is executed
        Then: Output should contain page count
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["info", str(multipage_pdf)])

        assert result.exit_code == 0
        assert "3" in result.output

    def test_info_command_shows_filename(self, basic_pdf: Path):
        """Given: A PDF file named 'basic.pdf'
        When: info command is executed
        Then: Output should contain the filename
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["info", str(basic_pdf)])

        assert result.exit_code == 0
        assert "basic.pdf" in result.output

    def test_info_command_shows_page_summary(self, basic_pdf: Path):
        """Given: A valid PDF file
        When: info command is executed
        Then: Output should contain page summary headers
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["info", str(basic_pdf)])

        assert result.exit_code == 0
        assert "Page" in result.output
        assert "Chars" in result.output

    def test_info_command_nonexistent_file_fails(self, tmp_path: Path):
        """Given: A non-existent file path
        When: info command is executed
        Then: Exit code should be non-zero
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["info", str(tmp_path / "nonexistent.pdf")])

        assert result.exit_code != 0


class TestPageCommand:
    """Tests for the 'page' CLI command."""

    def test_page_command_runs_successfully(self, basic_pdf: Path):
        """Given: A valid PDF file
        When: page command is executed
        Then: Exit code should be 0
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["page", str(basic_pdf)])

        assert result.exit_code == 0

    def test_page_command_shows_page_number(self, basic_pdf: Path):
        """Given: A valid PDF file
        When: page command is executed for page 1
        Then: Output should mention page 1
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["page", str(basic_pdf), "--page", "1"])

        assert result.exit_code == 0
        assert "Page 1" in result.output

    def test_page_command_shows_characters_option(self, basic_pdf: Path):
        """Given: A PDF file with text
        When: page command is executed with --element chars
        Then: Output should show character details
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["page", str(basic_pdf), "-e", "chars"])

        assert result.exit_code == 0
        assert "Char" in result.output
        assert "X0" in result.output

    def test_page_command_shows_lines_option(self, table_pdf: Path):
        """Given: A PDF file with lines
        When: page command is executed with --element lines
        Then: Output should show line statistics
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["page", str(table_pdf), "-e", "lines"])

        assert result.exit_code == 0
        assert "Horizontal" in result.output
        assert "Vertical" in result.output

    def test_page_command_limit_option(self, basic_pdf: Path):
        """Given: A PDF file with many characters
        When: page command is executed with --limit 5
        Then: Output should show only 5 items
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["page", str(basic_pdf), "-e", "chars", "-l", "5"])

        assert result.exit_code == 0
        assert "showing first 5" in result.output

    def test_page_command_invalid_page_fails(self, basic_pdf: Path):
        """Given: A single-page PDF
        When: page command is executed for page 99
        Then: Exit code should be non-zero and show error
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["page", str(basic_pdf), "--page", "99"])

        assert result.exit_code != 0
        assert "Error" in result.output

    def test_page_command_second_page(self, multipage_pdf: Path):
        """Given: A multi-page PDF
        When: page command is executed for page 2
        Then: Output should show page 2 analysis
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["page", str(multipage_pdf), "-p", "2"])

        assert result.exit_code == 0
        assert "Page 2" in result.output


class TestHelpCommand:
    """Tests for help output."""

    def test_main_help_shows_commands(self):
        """Given: No arguments
        When: --help is passed
        Then: Output should list available commands
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "info" in result.output
        assert "page" in result.output

    def test_info_help_shows_usage(self):
        """Given: info command
        When: --help is passed
        Then: Output should show command usage
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["info", "--help"])

        assert result.exit_code == 0
        assert "PDF_FILE" in result.output

    def test_page_help_shows_options(self):
        """Given: page command
        When: --help is passed
        Then: Output should show available options
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["page", "--help"])

        assert result.exit_code == 0
        assert "--page" in result.output
        assert "--element" in result.output
        assert "--limit" in result.output
