"""HTML parser for Naver Finance research reports."""

from dataclasses import dataclass
from bs4 import BeautifulSoup, Tag


@dataclass
class ReportInfo:
    """Parsed report information from Naver Finance."""

    title: str
    broker: str
    stock_name: str
    date: str  # Original format (e.g., "25.01.15")
    pdf_url: str

    def get_formatted_date(self) -> str:
        """Convert date to yyyy-mm-dd format.

        Input format: "YY.MM.DD" (e.g., "25.01.15")
        Output format: "YYYY-MM-DD" (e.g., "2025-01-15")
        """
        parts = self.date.split(".")
        if len(parts) != 3:
            return self.date

        year, month, day = parts
        year = year.strip()
        month = month.strip()
        day = day.strip()

        # Convert 2-digit year to 4-digit
        if len(year) == 2:
            year_int = int(year)
            # Assume years 00-99 map to 2000-2099
            year = f"20{year:0>2}"

        return f"{year}-{month:0>2}-{day:0>2}"


def parse_report_list(html: str) -> list[ReportInfo]:
    """Parse report list from HTML.

    Args:
        html: Raw HTML string from Naver Finance research page.

    Returns:
        List of ReportInfo objects extracted from the page.
    """
    soup = BeautifulSoup(html, "lxml")

    table = soup.find("table", class_="type_1")
    if not table:
        return []

    reports: list[ReportInfo] = []
    rows = table.find_all("tr")

    for row in rows:
        # Skip header and blank rows
        if row.find("th"):
            continue
        if row.find("td", class_="blank_07") or row.find("td", class_="blank_08"):
            continue

        report = _parse_report_row(row)
        if report:
            reports.append(report)

    return reports


def _parse_report_row(row: Tag) -> ReportInfo | None:
    """Parse a single report row.

    Args:
        row: BeautifulSoup Tag representing a table row.

    Returns:
        ReportInfo if parsing succeeds, None otherwise.
    """
    cells = row.find_all("td")
    if len(cells) < 5:
        return None

    # Stock name: first cell contains <a class="stock_item">
    stock_link = cells[0].find("a", class_="stock_item")
    if not stock_link:
        return None
    stock_name = stock_link.get_text(strip=True)

    # Title: second cell contains <a href="company_read.naver?...">
    title_link = cells[1].find("a")
    if not title_link:
        return None
    title = title_link.get_text(strip=True)

    # Broker: third cell (direct text)
    broker = cells[2].get_text(strip=True)
    if not broker:
        return None

    # PDF URL: fourth cell with class="file" contains <a href="...pdf">
    pdf_cell = cells[3]
    pdf_link = pdf_cell.find("a")
    if not pdf_link:
        return None
    pdf_url = pdf_link.get("href", "")
    if not pdf_url or not pdf_url.endswith(".pdf"):
        return None

    # Date: fifth cell with class="date"
    date_cell = cells[4]
    date = date_cell.get_text(strip=True)
    if not date:
        return None

    return ReportInfo(
        title=title,
        broker=broker,
        stock_name=stock_name,
        date=date,
        pdf_url=pdf_url,
    )


def get_total_pages(html: str) -> int:
    """Extract total number of pages from pagination.

    Args:
        html: Raw HTML string from Naver Finance research page.

    Returns:
        Total number of pages. Returns 1 if pagination not found.
    """
    soup = BeautifulSoup(html, "lxml")

    # Find pagination table
    paging = soup.find("table", class_="Nnavi")
    if not paging:
        return 1

    # Find the "맨뒤" (last page) link
    last_page_cell = paging.find("td", class_="pgRR")
    if not last_page_cell:
        return 1

    last_page_link = last_page_cell.find("a")
    if not last_page_link:
        return 1

    href = last_page_link.get("href", "")
    # Extract page number from URL like "/research/company_list.naver?&page=2711"
    if "page=" in href:
        try:
            page_str = href.split("page=")[-1].split("&")[0]
            return int(page_str)
        except ValueError:
            return 1

    return 1


def get_unique_brokers(reports: list[ReportInfo]) -> set[str]:
    """Extract unique broker names from reports.

    Args:
        reports: List of ReportInfo objects.

    Returns:
        Set of unique broker names.
    """
    return {report.broker for report in reports}
