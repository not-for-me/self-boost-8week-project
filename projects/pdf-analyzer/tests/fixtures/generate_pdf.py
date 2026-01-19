"""Test PDF generator using reportlab."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle


def create_basic_pdf(output_path: Path) -> None:
    """Create a basic PDF with text, lines, and a simple shape.

    Contains:
    - Title text
    - Body text (multiple lines)
    - Horizontal and vertical lines
    - A rectangle
    """
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4

    # Title
    c.setFont("Helvetica-Bold", 24)
    c.drawString(72, height - 72, "Sample PDF Document")

    # Subtitle
    c.setFont("Helvetica", 14)
    c.drawString(72, height - 100, "This is a test document for PDF Analyzer")

    # Horizontal line under title
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.line(72, height - 110, width - 72, height - 110)

    # Body text
    c.setFont("Helvetica", 12)
    y_position = height - 150
    body_lines = [
        "PDF (Portable Document Format) is a file format developed by Adobe.",
        "It captures document text, fonts, images, and layout.",
        "This sample contains various PDF elements for testing.",
        "",
        "Elements in this document:",
        "- Text with different fonts and sizes",
        "- Horizontal and vertical lines",
        "- A colored rectangle",
    ]
    for line in body_lines:
        c.drawString(72, y_position, line)
        y_position -= 18

    # Vertical line
    c.setStrokeColor(colors.gray)
    c.setLineWidth(0.5)
    c.line(60, height - 130, 60, y_position + 10)

    # Rectangle
    c.setFillColor(colors.lightblue)
    c.setStrokeColor(colors.darkblue)
    c.setLineWidth(2)
    c.rect(72, y_position - 80, 200, 60, fill=1)

    # Text inside rectangle
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(82, y_position - 45, "This is a colored rectangle")

    c.save()


def create_multipage_pdf(output_path: Path, num_pages: int = 3) -> None:
    """Create a multi-page PDF.

    Each page has:
    - Page number
    - Different content to distinguish pages
    """
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4

    for page_num in range(1, num_pages + 1):
        # Page header
        c.setFont("Helvetica-Bold", 18)
        c.drawString(72, height - 72, f"Page {page_num} of {num_pages}")

        # Horizontal line
        c.setStrokeColor(colors.black)
        c.line(72, height - 85, width - 72, height - 85)

        # Page-specific content
        c.setFont("Helvetica", 12)
        c.drawString(72, height - 120, f"This is the content of page {page_num}.")

        # Add varying number of text lines per page
        y_position = height - 150
        for i in range(page_num * 5):
            c.drawString(72, y_position, f"Line {i + 1} on page {page_num}")
            y_position -= 15

        if page_num < num_pages:
            c.showPage()

    c.save()


def create_table_pdf(output_path: Path) -> None:
    """Create a PDF with a table structure using lines.

    Contains:
    - Title
    - A table drawn with lines (simulating financial data)
    """
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4

    # Title
    c.setFont("Helvetica-Bold", 18)
    c.drawString(72, height - 72, "Financial Summary Table")

    # Table data
    table_data = [
        ["Category", "2023", "2024", "2025E"],
        ["Revenue", "258.9", "279.6", "298.0"],
        ["Operating Profit", "6.6", "8.5", "12.0"],
        ["Net Income", "15.5", "18.2", "22.0"],
    ]

    # Table dimensions
    table_x = 72
    table_y = height - 250
    col_widths = [120, 80, 80, 80]
    row_height = 25
    num_rows = len(table_data)
    num_cols = len(table_data[0])

    # Draw table lines
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)

    # Horizontal lines
    for i in range(num_rows + 1):
        y = table_y + i * row_height
        x_end = table_x + sum(col_widths)
        c.line(table_x, y, x_end, y)

    # Vertical lines
    x = table_x
    for i in range(num_cols + 1):
        y_start = table_y
        y_end = table_y + num_rows * row_height
        c.line(x, y_start, x, y_end)
        if i < num_cols:
            x += col_widths[i]

    # Fill in table text
    c.setFont("Helvetica", 10)
    for row_idx, row in enumerate(reversed(table_data)):
        y = table_y + row_idx * row_height + 8
        x = table_x + 5
        for col_idx, cell in enumerate(row):
            # Bold for header row
            if row_idx == num_rows - 1:
                c.setFont("Helvetica-Bold", 10)
            else:
                c.setFont("Helvetica", 10)
            c.drawString(x, y, cell)
            x += col_widths[col_idx]

    c.save()


def create_empty_page_pdf(output_path: Path) -> None:
    """Create a PDF with an empty page in the middle.

    Page 1: Content
    Page 2: Empty
    Page 3: Content
    """
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4

    # Page 1
    c.setFont("Helvetica-Bold", 18)
    c.drawString(72, height - 72, "Page 1 - With Content")
    c.setFont("Helvetica", 12)
    c.drawString(72, height - 100, "This page has some text content.")
    c.showPage()

    # Page 2 - Empty (just create and move to next)
    c.showPage()

    # Page 3
    c.setFont("Helvetica-Bold", 18)
    c.drawString(72, height - 72, "Page 3 - With Content")
    c.setFont("Helvetica", 12)
    c.drawString(72, height - 100, "Page 2 was intentionally left empty.")

    c.save()


def create_korean_text_pdf(output_path: Path) -> None:
    """Create a PDF with Korean text (using available fonts).

    Note: This uses built-in fonts, so Korean may not render properly.
    For actual Korean text, CJK fonts would need to be registered.
    """
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4

    # Title in English (Korean fonts not available by default)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(72, height - 72, "Document with Mixed Content")

    # English text
    c.setFont("Helvetica", 12)
    c.drawString(72, height - 110, "This document simulates a securities report.")
    c.drawString(72, height - 130, "Stock: Samsung Electronics")
    c.drawString(72, height - 150, "Broker: Test Securities")

    # Simulated table header
    c.setFont("Helvetica-Bold", 12)
    c.drawString(72, height - 200, "Financial Highlights")

    # Simple data
    c.setFont("Helvetica", 11)
    data_lines = [
        "Revenue:        258.9 trillion KRW",
        "Operating:       6.6 trillion KRW",
        "Net Income:     15.5 trillion KRW",
    ]
    y = height - 230
    for line in data_lines:
        c.drawString(72, y, line)
        y -= 20

    c.save()


def generate_all_test_pdfs(fixtures_dir: Path) -> dict[str, Path]:
    """Generate all test PDF files.

    Returns:
        Dictionary mapping PDF name to its path.
    """
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    pdfs = {
        "basic": fixtures_dir / "basic.pdf",
        "multipage": fixtures_dir / "multipage.pdf",
        "table": fixtures_dir / "table.pdf",
        "empty_page": fixtures_dir / "empty_page.pdf",
        "korean": fixtures_dir / "korean.pdf",
    }

    create_basic_pdf(pdfs["basic"])
    create_multipage_pdf(pdfs["multipage"])
    create_table_pdf(pdfs["table"])
    create_empty_page_pdf(pdfs["empty_page"])
    create_korean_text_pdf(pdfs["korean"])

    return pdfs


if __name__ == "__main__":
    # Generate PDFs when run directly
    fixtures_dir = Path(__file__).parent
    pdfs = generate_all_test_pdfs(fixtures_dir)
    print("Generated test PDFs:")
    for name, path in pdfs.items():
        print(f"  {name}: {path}")
