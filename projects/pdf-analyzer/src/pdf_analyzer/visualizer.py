"""ASCII visualization for PDF page layout."""

from dataclasses import dataclass

from pdf_analyzer.analyzer import PageAnalysis, TableInfo


@dataclass
class VisualConfig:
    """Configuration for ASCII visualization."""

    width: int = 60  # Terminal width for visualization
    height: int = 40  # Terminal height for visualization
    show_text: bool = True
    show_lines: bool = True
    show_tables: bool = True
    show_images: bool = True


class ASCIIVisualizer:
    """Visualize PDF page layout using ASCII art."""

    # Characters for different elements
    CHAR_EMPTY = " "
    CHAR_TEXT = "\u2591"  # Light shade (░) - lighter than image
    CHAR_LINE_H = "\u2550"  # Double horizontal
    CHAR_LINE_V = "\u2551"  # Double vertical
    CHAR_TABLE_CORNER = "\u256c"  # Double cross
    CHAR_TABLE_H = "\u2500"  # Light horizontal
    CHAR_TABLE_V = "\u2502"  # Light vertical
    CHAR_IMAGE = "\u2588"  # Full block (█) - solid for images

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

        if self.config.show_lines:
            self._draw_lines(grid, analysis, scale_x, scale_y)

        if self.config.show_tables and tables:
            self._draw_tables(grid, tables, scale_x, scale_y)

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
        """Draw text regions on grid."""
        for char in analysis.chars:
            x = int(char.x0 * scale_x)
            y = int(char.top * scale_y)

            if 0 <= x < self.config.width and 0 <= y < self.config.height:
                grid[y][x] = self.CHAR_TEXT

    def _draw_lines(
        self,
        grid: list[list[str]],
        analysis: PageAnalysis,
        scale_x: float,
        scale_y: float,
    ) -> None:
        """Draw line objects on grid."""
        for line in analysis.lines:
            x0 = int(line.x0 * scale_x)
            y0 = int(line.top * scale_y)
            x1 = int(line.x1 * scale_x)
            y1 = int(line.bottom * scale_y)

            # Clamp to grid bounds
            x0 = max(0, min(x0, self.config.width - 1))
            x1 = max(0, min(x1, self.config.width - 1))
            y0 = max(0, min(y0, self.config.height - 1))
            y1 = max(0, min(y1, self.config.height - 1))

            if line.is_horizontal:
                # Draw horizontal line
                for x in range(min(x0, x1), max(x0, x1) + 1):
                    if 0 <= x < self.config.width:
                        grid[y0][x] = self.CHAR_LINE_H
            elif line.is_vertical:
                # Draw vertical line
                for y in range(min(y0, y1), max(y0, y1) + 1):
                    if 0 <= y < self.config.height:
                        grid[y][x0] = self.CHAR_LINE_V

    def _draw_tables(
        self,
        grid: list[list[str]],
        tables: list[TableInfo],
        scale_x: float,
        scale_y: float,
    ) -> None:
        """Draw table boundaries on grid."""
        for table in tables:
            x0 = int(table.x0 * scale_x)
            y0 = int(table.top * scale_y)
            x1 = int(table.x1 * scale_x)
            y1 = int(table.bottom * scale_y)

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
        for img in analysis.images:
            x0 = int(img.x0 * scale_x)
            y0 = int(img.top * scale_y)
            x1 = int(img.x1 * scale_x)
            y1 = int(img.bottom * scale_y)

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
        lines.append(f"  {self.CHAR_TEXT} = Text    {self.CHAR_LINE_H}/{self.CHAR_LINE_V} = Lines    {self.CHAR_TABLE_H}{self.CHAR_TABLE_V} = Table    {self.CHAR_IMAGE} = Image")

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
