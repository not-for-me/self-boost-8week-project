"""ASCII visualization for PDF page layout."""

from dataclasses import dataclass

from pdf_analyzer.analyzer import PageAnalysis, TableInfo


@dataclass
class VisualConfig:
    """Configuration for ASCII visualization."""

    width: int = 60  # Terminal width for visualization
    height: int = 40  # Terminal height for visualization
    show_text: bool = True
    show_tables: bool = True
    show_images: bool = True


class ASCIIVisualizer:
    """Visualize PDF page layout using ASCII art."""

    # Characters for different elements
    CHAR_EMPTY = " "
    CHAR_TEXT = "\u2591"  # Light shade - regular text
    CHAR_TABLE_TEXT = "\u2592"  # Medium shade - text inside table
    CHAR_TABLE_CORNER = "\u256c"  # Double cross
    CHAR_TABLE_H = "\u2500"  # Light horizontal
    CHAR_TABLE_V = "\u2502"  # Light vertical
    CHAR_IMAGE = "\u2588"  # Full block - solid for images

    def __init__(self, config: VisualConfig | None = None):
        """Initialize visualizer with config.

        Args:
            config: Visualization configuration. Uses defaults if None.
        """
        self.config = config or VisualConfig()

    def visualize_page(
        self,
        analysis: PageAnalysis,
        tables: list[TableInfo] | None = None,
    ) -> str:
        """Create ASCII visualization of a page.

        Args:
            analysis: Page analysis data.
            tables: Optional list of detected tables.

        Returns:
            Multi-line string with ASCII visualization.
        """
        # Calculate scale factors
        scale_x = self.config.width / analysis.width
        scale_y = self.config.height / analysis.height

        # Initialize grid
        grid = [
            [self.CHAR_EMPTY for _ in range(self.config.width)]
            for _ in range(self.config.height)
        ]

        # Draw elements in order (back to front)
        if self.config.show_text:
            self._draw_text_regions(grid, analysis, scale_x, scale_y)

        if self.config.show_tables and tables:
            self._draw_tables(grid, tables, scale_x, scale_y, analysis.height)

        if self.config.show_images:
            self._draw_images(grid, analysis, scale_x, scale_y)

        # Build output string
        return self._render_grid(grid, analysis)

    def _draw_text_regions(
        self,
        grid: list[list[str]],
        analysis: PageAnalysis,
        scale_x: float,
        scale_y: float,
    ) -> None:
        """Draw text block regions on grid."""
        page_height = analysis.height

        for block in analysis.text_blocks:
            x0 = int(block.bbox.x0 * scale_x)
            x1 = int(block.bbox.x1 * scale_x)
            # Convert PDF coordinates (y increases upward) to screen coordinates
            # (y increases downward): screen_y = page_height - pdf_y
            y0 = int((page_height - block.bbox.y1) * scale_y)
            y1 = int((page_height - block.bbox.y0) * scale_y)

            # Clamp to grid bounds
            x0 = max(0, min(x0, self.config.width - 1))
            x1 = max(0, min(x1, self.config.width - 1))
            y0 = max(0, min(y0, self.config.height - 1))
            y1 = max(0, min(y1, self.config.height - 1))

            # Choose character based on in_table flag
            char = self.CHAR_TABLE_TEXT if block.in_table else self.CHAR_TEXT

            # Fill text block area
            for y in range(y0, y1 + 1):
                for x in range(x0, x1 + 1):
                    grid[y][x] = char

    def _draw_tables(
        self,
        grid: list[list[str]],
        tables: list[TableInfo],
        scale_x: float,
        scale_y: float,
        page_height: float,
    ) -> None:
        """Draw table boundaries on grid."""
        for table in tables:
            x0 = int(table.x0 * scale_x)
            x1 = int(table.x1 * scale_x)
            # Convert PDF coordinates to screen coordinates
            y0 = int((page_height - table.bottom) * scale_y)
            y1 = int((page_height - table.top) * scale_y)

            # Clamp to grid bounds
            x0 = max(0, min(x0, self.config.width - 1))
            x1 = max(0, min(x1, self.config.width - 1))
            y0 = max(0, min(y0, self.config.height - 1))
            y1 = max(0, min(y1, self.config.height - 1))

            # Draw table border
            for x in range(x0, x1 + 1):
                if 0 <= y0 < self.config.height:
                    grid[y0][x] = self.CHAR_TABLE_H
                if 0 <= y1 < self.config.height:
                    grid[y1][x] = self.CHAR_TABLE_H

            for y in range(y0, y1 + 1):
                if 0 <= x0 < self.config.width:
                    grid[y][x0] = self.CHAR_TABLE_V
                if 0 <= x1 < self.config.width:
                    grid[y][x1] = self.CHAR_TABLE_V

            # Draw corners
            if 0 <= y0 < self.config.height and 0 <= x0 < self.config.width:
                grid[y0][x0] = self.CHAR_TABLE_CORNER
            if 0 <= y0 < self.config.height and 0 <= x1 < self.config.width:
                grid[y0][x1] = self.CHAR_TABLE_CORNER
            if 0 <= y1 < self.config.height and 0 <= x0 < self.config.width:
                grid[y1][x0] = self.CHAR_TABLE_CORNER
            if 0 <= y1 < self.config.height and 0 <= x1 < self.config.width:
                grid[y1][x1] = self.CHAR_TABLE_CORNER

    def _draw_images(
        self,
        grid: list[list[str]],
        analysis: PageAnalysis,
        scale_x: float,
        scale_y: float,
    ) -> None:
        """Draw image placeholders on grid."""
        page_height = analysis.height

        for img in analysis.images:
            x0 = int(img.x0 * scale_x)
            x1 = int(img.x1 * scale_x)
            # Convert PDF coordinates to screen coordinates
            y0 = int((page_height - img.bottom) * scale_y)
            y1 = int((page_height - img.top) * scale_y)

            # Clamp to grid bounds
            x0 = max(0, min(x0, self.config.width - 1))
            x1 = max(0, min(x1, self.config.width - 1))
            y0 = max(0, min(y0, self.config.height - 1))
            y1 = max(0, min(y1, self.config.height - 1))

            # Fill image area
            for y in range(y0, y1 + 1):
                for x in range(x0, x1 + 1):
                    grid[y][x] = self.CHAR_IMAGE

    def _render_grid(self, grid: list[list[str]], analysis: PageAnalysis) -> str:
        """Render grid to string with border and legend."""
        lines = []

        # Header
        header = f"Page {analysis.page_number} ({analysis.width:.0f} x {analysis.height:.0f} pt)"
        lines.append(f"{'=' * self.config.width}")
        lines.append(header.center(self.config.width))
        lines.append(f"{'=' * self.config.width}")

        # Top border
        lines.append("+" + "-" * self.config.width + "+")

        # Grid content
        for row in grid:
            lines.append("|" + "".join(row) + "|")

        # Bottom border
        lines.append("+" + "-" * self.config.width + "+")

        # Legend
        lines.append("")
        lines.append("Legend:")
        lines.append(
            f"  {self.CHAR_TEXT} = Text    "
            f"{self.CHAR_TABLE_TEXT} = Table Text    "
            f"{self.CHAR_TABLE_H}{self.CHAR_TABLE_V} = Table    "
            f"{self.CHAR_IMAGE} = Image"
        )

        return "\n".join(lines)


def create_simple_visual(
    analysis: PageAnalysis,
    tables: list[TableInfo] | None = None,
    width: int = 60,
    height: int = 30,
) -> str:
    """Create a simple ASCII visualization.

    Args:
        analysis: Page analysis data.
        tables: Optional list of detected tables.
        width: Terminal width.
        height: Terminal height.

    Returns:
        ASCII visualization string.
    """
    config = VisualConfig(width=width, height=height)
    visualizer = ASCIIVisualizer(config)
    return visualizer.visualize_page(analysis, tables)
