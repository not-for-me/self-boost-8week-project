"""Unit tests for the HTML parser module."""

import pytest

from src.parser import (
    ReportInfo,
    get_total_pages,
    get_unique_brokers,
    parse_report_list,
)


# =============================================================================
# Fixtures: Sample HTML data
# =============================================================================


SAMPLE_REPORT_ROW = """
<tr>
 <td style="padding-left:10">
  <a class="stock_item" href="/item/main.naver?code=051910" title="LG화학">
   LG화학
  </a>
 </td>
 <td>
  <a href="company_read.naver?nid=89281&amp;page=1">
   상반기까지 부진 지속 전망
  </a>
 </td>
 <td>
  한화투자증권
 </td>
 <td class="file">
  <a href="https://stock.pstatic.net/stock-research/company/16/20260119_company_822088000.pdf" target="_blank">
   <img align="absmiddle" alt="pdf" src="https://ssl.pstatic.net/imgstock/images5/down.gif"/>
  </a>
 </td>
 <td class="date" style="padding-left:5px">
  26.01.19
 </td>
 <td class="date">
  1348
 </td>
</tr>
"""


SAMPLE_TABLE_HTML = f"""
<html>
<body>
<table class="type_1">
<tr>
 <th>종목명</th>
 <th>제목</th>
 <th style="text-align:left">증권사</th>
 <th>첨부</th>
 <th>작성일</th>
 <th>조회수</th>
</tr>
<tr>
 <td class="blank_07" colspan="6"></td>
</tr>
<tr>
 <td style="padding-left:10">
  <a class="stock_item" href="/item/main.naver?code=051910" title="LG화학">LG화학</a>
 </td>
 <td>
  <a href="company_read.naver?nid=89281&amp;page=1">상반기까지 부진 지속 전망</a>
 </td>
 <td>한화투자증권</td>
 <td class="file">
  <a href="https://stock.pstatic.net/stock-research/company/16/20260119_company_822088000.pdf" target="_blank">
   <img alt="pdf" src="down.gif"/>
  </a>
 </td>
 <td class="date" style="padding-left:5px">26.01.19</td>
 <td class="date">1348</td>
</tr>
<tr>
 <td style="padding-left:10">
  <a class="stock_item" href="/item/main.naver?code=096770" title="SK이노베이션">SK이노베이션</a>
 </td>
 <td>
  <a href="company_read.naver?nid=89280&amp;page=1">정유화학 개선 긍정적</a>
 </td>
 <td>미래에셋증권</td>
 <td class="file">
  <a href="https://stock.pstatic.net/stock-research/company/16/20260118_company_80648000.pdf" target="_blank">
   <img alt="pdf" src="down.gif"/>
  </a>
 </td>
 <td class="date" style="padding-left:5px">26.01.18</td>
 <td class="date">931</td>
</tr>
<tr>
 <td class="blank_08" colspan="6"></td>
</tr>
</table>
</body>
</html>
"""


SAMPLE_PAGINATION_HTML = """
<html>
<body>
<table align="center" class="Nnavi" summary="페이지 네비게이션 리스트">
 <caption>페이지 네비게이션</caption>
 <tr>
  <td class="on">
   <a href="/research/company_list.naver?&amp;page=1">1</a>
  </td>
  <td>
   <a href="/research/company_list.naver?&amp;page=2">2</a>
  </td>
  <td class="pgR">
   <a href="/research/company_list.naver?&amp;page=11">다음</a>
  </td>
  <td class="pgRR">
   <a href="/research/company_list.naver?&amp;page=2711">맨뒤</a>
  </td>
 </tr>
</table>
</body>
</html>
"""


EMPTY_TABLE_HTML = """
<html>
<body>
<table class="type_1">
<tr>
 <th>종목명</th>
 <th>제목</th>
 <th>증권사</th>
 <th>첨부</th>
 <th>작성일</th>
 <th>조회수</th>
</tr>
</table>
</body>
</html>
"""


NO_TABLE_HTML = """
<html>
<body>
<p>No reports found.</p>
</body>
</html>
"""


# =============================================================================
# Tests: ReportInfo
# =============================================================================


class TestReportInfoGetFormattedDate:
    """Tests for ReportInfo.get_formatted_date() method."""

    def test_converts_two_digit_year_correctly(self):
        """Given: date="25.01.15", When: get_formatted_date(), Then: "2025-01-15"."""
        # Arrange
        report = ReportInfo(
            title="Test",
            broker="Test증권",
            stock_name="테스트",
            date="25.01.15",
            pdf_url="https://example.com/test.pdf",
        )

        # Act
        result = report.get_formatted_date()

        # Assert
        assert result == "2025-01-15"

    def test_handles_single_digit_month_and_day(self):
        """Given: date="26.1.5", When: get_formatted_date(), Then: zero-padded format."""
        # Arrange
        report = ReportInfo(
            title="Test",
            broker="Test증권",
            stock_name="테스트",
            date="26.1.5",
            pdf_url="https://example.com/test.pdf",
        )

        # Act
        result = report.get_formatted_date()

        # Assert
        assert result == "2026-01-05"

    def test_returns_original_if_invalid_format(self):
        """Given: invalid date format, When: get_formatted_date(), Then: return original."""
        # Arrange
        report = ReportInfo(
            title="Test",
            broker="Test증권",
            stock_name="테스트",
            date="invalid-date",
            pdf_url="https://example.com/test.pdf",
        )

        # Act
        result = report.get_formatted_date()

        # Assert
        assert result == "invalid-date"


# =============================================================================
# Tests: parse_report_list
# =============================================================================


class TestParseReportList:
    """Tests for parse_report_list() function."""

    def test_extracts_all_fields_from_valid_html(self):
        """Given: valid HTML with reports, When: parse, Then: all fields extracted."""
        # Arrange & Act
        reports = parse_report_list(SAMPLE_TABLE_HTML)

        # Assert
        assert len(reports) == 2

        first_report = reports[0]
        assert first_report.stock_name == "LG화학"
        assert first_report.title == "상반기까지 부진 지속 전망"
        assert first_report.broker == "한화투자증권"
        assert first_report.date == "26.01.19"
        assert "822088000.pdf" in first_report.pdf_url

    def test_extracts_multiple_reports(self):
        """Given: HTML with multiple reports, When: parse, Then: all reports extracted."""
        # Arrange & Act
        reports = parse_report_list(SAMPLE_TABLE_HTML)

        # Assert
        assert len(reports) == 2
        assert reports[0].broker == "한화투자증권"
        assert reports[1].broker == "미래에셋증권"

    def test_returns_empty_list_for_empty_table(self):
        """Given: HTML with empty table, When: parse, Then: empty list returned."""
        # Arrange & Act
        reports = parse_report_list(EMPTY_TABLE_HTML)

        # Assert
        assert reports == []

    def test_returns_empty_list_when_no_table(self):
        """Given: HTML without table, When: parse, Then: empty list returned."""
        # Arrange & Act
        reports = parse_report_list(NO_TABLE_HTML)

        # Assert
        assert reports == []

    def test_skips_blank_rows(self):
        """Given: HTML with blank rows, When: parse, Then: blank rows skipped."""
        # Arrange & Act
        reports = parse_report_list(SAMPLE_TABLE_HTML)

        # Assert
        # Sample HTML has blank_07 and blank_08 rows, but we should only get 2 reports
        assert len(reports) == 2

    def test_skips_header_row(self):
        """Given: HTML with header row, When: parse, Then: header skipped."""
        # Arrange & Act
        reports = parse_report_list(SAMPLE_TABLE_HTML)

        # Assert
        # No report should have "종목명" as stock_name (header value)
        stock_names = [r.stock_name for r in reports]
        assert "종목명" not in stock_names


# =============================================================================
# Tests: get_total_pages
# =============================================================================


class TestGetTotalPages:
    """Tests for get_total_pages() function."""

    def test_extracts_total_pages_from_pagination(self):
        """Given: HTML with pagination, When: get_total_pages, Then: correct count."""
        # Arrange & Act
        total = get_total_pages(SAMPLE_PAGINATION_HTML)

        # Assert
        assert total == 2711

    def test_returns_one_when_no_pagination(self):
        """Given: HTML without pagination, When: get_total_pages, Then: 1 returned."""
        # Arrange & Act
        total = get_total_pages(SAMPLE_TABLE_HTML)

        # Assert
        assert total == 1

    def test_returns_one_for_empty_html(self):
        """Given: empty HTML, When: get_total_pages, Then: 1 returned."""
        # Arrange & Act
        total = get_total_pages("<html></html>")

        # Assert
        assert total == 1


# =============================================================================
# Tests: get_unique_brokers
# =============================================================================


class TestGetUniqueBrokers:
    """Tests for get_unique_brokers() function."""

    def test_extracts_unique_broker_names(self):
        """Given: reports with different brokers, When: get_unique_brokers, Then: unique set."""
        # Arrange
        reports = [
            ReportInfo("t1", "한화투자증권", "LG화학", "26.01.19", "url1.pdf"),
            ReportInfo("t2", "미래에셋증권", "SK이노", "26.01.19", "url2.pdf"),
            ReportInfo("t3", "한화투자증권", "삼성전자", "26.01.18", "url3.pdf"),
        ]

        # Act
        brokers = get_unique_brokers(reports)

        # Assert
        assert brokers == {"한화투자증권", "미래에셋증권"}

    def test_returns_empty_set_for_empty_list(self):
        """Given: empty report list, When: get_unique_brokers, Then: empty set."""
        # Arrange & Act
        brokers = get_unique_brokers([])

        # Assert
        assert brokers == set()
