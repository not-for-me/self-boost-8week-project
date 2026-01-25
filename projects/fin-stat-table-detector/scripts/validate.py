"""PDF 테이블 탐지 결과 검증 스크립트.

EnsembleDetector의 detect_all_tables 결과를 시각화하여
bbox가 올바르게 탐지되었는지 확인합니다.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PIL import Image, ImageDraw
from rich.console import Console

from fin_stat_table_detector.detectors import DoclingDetector
from fin_stat_table_detector.ensemble import EnsembleDetector
from fin_stat_table_detector.models import TableCandidate
from fin_stat_table_detector.utils.pdf_utils import convert_pdf_to_images


def visualize_tables_on_pdf(
    pdf_path: Path,
    tables: list[TableCandidate],
    output_dir: Path,
    pages: list[int],
    dpi: int = 150,
) -> list[Path]:
    """PDF 페이지에 감지된 테이블 bbox를 시각화.

    Args:
        pdf_path: 원본 PDF 파일 경로.
        tables: 탐지된 테이블 후보 리스트.
        output_dir: 시각화 결과 저장 디렉토리.
        dpi: 이미지 변환 해상도.

    Returns:
        생성된 시각화 이미지 경로 리스트.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # PDF → 이미지 변환
    page_results = convert_pdf_to_images(pdf_path, output_dir, dpi=dpi)

    output_paths = []
    colors = [
        (255, 0, 0),      # Red
        (0, 128, 255),    # Blue
        (0, 200, 0),      # Green
        (255, 128, 0),    # Orange
        (128, 0, 255),    # Purple
        (255, 0, 128),    # Pink
    ]

    for page_num, image_path, dims in page_results:
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)

        # 해당 페이지의 테이블들
        page_tables = [t for t in tables if t.page == page_num]

        # PDF 좌표 → 이미지 좌표 스케일
        scale_x = dims.image_width / dims.pdf_width
        scale_y = dims.image_height / dims.pdf_height

        for i, table in enumerate(page_tables):
            # 좌표 변환
            x0 = table.bbox.x0 * scale_x
            y0 = table.bbox.y0 * scale_y
            x1 = table.bbox.x1 * scale_x
            y1 = table.bbox.y1 * scale_y

            # 색상 선택 (순환)
            color = colors[i % len(colors)]

            # bbox 그리기 (두께 3)
            draw.rectangle([x0, y0, x1, y1], outline=color, width=3)

            # 라벨 텍스트
            label = f"Table {i + 1} ({table.detector})"

            # 텍스트 배경 (가독성 향상)
            text_bbox = draw.textbbox((x0, y0 - 20), label)
            draw.rectangle(text_bbox, fill=(255, 255, 255, 200))
            draw.text((x0, y0 - 20), label, fill=color)

        # 페이지 정보 표시
        info_text = f"Page {page_num} | Tables: {len(page_tables)}"
        draw.rectangle([0, 0, 250, 25], fill=(0, 0, 0))
        draw.text((5, 5), info_text, fill=(255, 255, 255))

        # 결과 저장 (debug_ 접두사)
        debug_path = output_dir / f"debug_page_{page_num:03d}.png"
        img.save(debug_path)
        output_paths.append(debug_path)

        # 원본 이미지 삭제 (debug 이미지만 유지)
        # if image_path != debug_path:
        image_path.unlink(missing_ok=True)
        if page_num not in pages:
            debug_path.unlink(missing_ok=True)

    return output_paths


def main():
    console = Console()

    # 설정
    sample_pdf = Path("../../data/iM증권/2025-12-09_01.pdf")
    output_dir = Path("./debug_output")
    pages = [14,15]

    if not sample_pdf.exists():
        console.print(f"[red]PDF not found: {sample_pdf}[/red]")
        return

    console.print(f"[cyan]Processing: {sample_pdf}[/cyan]")

    # 테이블 탐지
    ensemble = EnsembleDetector(detectors=[DoclingDetector()])
    table_candidates = ensemble.detect_all_tables(sample_pdf, pages)

    console.print(f"\n[green]Detected {len(table_candidates)} table candidates[/green]")

    # 결과 출력
    for i, table in enumerate(table_candidates):
        console.print(
            f"  Table {i + 1}: page={table.page}, "
            f"bbox=({table.bbox.x0:.1f}, {table.bbox.y0:.1f}, "
            f"{table.bbox.x1:.1f}, {table.bbox.y1:.1f}), "
            f"detector={table.detector}"
        )

    # 시각화
    console.print(f"\n[cyan]Generating visualizations...[/cyan]")
    output_paths = visualize_tables_on_pdf(
        sample_pdf, table_candidates, output_dir, pages, dpi=150
    )

    console.print(f"\n[green]Saved {len(output_paths)} debug images:[/green]")
    for path in output_paths:
        console.print(f"  - {path}")


if __name__ == "__main__":
    main()
