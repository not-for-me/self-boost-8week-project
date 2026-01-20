# fin-stat-table-detector

PDF 증권사 리포트에서 재무제표 테이블을 자동으로 탐지하고, Label Studio 형식으로 내보내는 도구입니다.

## 주요 기능

- **다중 탐지기 앙상블**: pdfplumber, Camelot(lattice/stream), Docling 등 여러 탐지기를 조합하여 정확도 향상
- **재무제표 자동 분류**: 손익계산서, 재무상태표, 현금흐름표 등 재무제표 유형 자동 분류
- **IoU 기반 중복 제거**: 여러 탐지기 결과를 병합할 때 겹치는 영역 자동 제거
- **Label Studio 내보내기**: 탐지 결과를 Label Studio 호환 JSON 형식으로 내보내기
- **CLI 지원**: 단일 파일 또는 디렉토리 배치 처리

## 설치

### 시스템 의존성

PDF를 이미지로 변환하기 위해 `poppler`가 필요합니다.

```bash
# macOS
brew install poppler

# Ubuntu/Debian
sudo apt install poppler-utils
```

### 패키지 설치

```bash
cd projects/fin-stat-table-detector
uv sync
```

Docling(ML 기반 탐지기)을 사용하려면:

```bash
uv sync --extra ml
```

## CLI 사용법

### 기본 명령어

```bash
# 도움말 보기
fin-stat-detect --help
fin-stat-detect detect --help
```

### 단일 PDF 처리

```bash
fin-stat-detect detect report.pdf
```

결과:
- `report_labels.json`: Label Studio 호환 JSON 파일
- `./images/`: 각 페이지를 이미지로 변환한 파일들

### 디렉토리 배치 처리

```bash
fin-stat-detect detect ./data/
```

`./data/` 디렉토리 내 모든 PDF 파일을 재귀적으로 처리합니다.

### 증권사 필터링

특정 증권사 리포트만 처리:

```bash
fin-stat-detect detect ./data/ --firm "한화투자증권"
```

파일명에 "한화투자증권"이 포함된 PDF만 처리합니다.

### 처리 대상 미리보기 (Dry Run)

실제 처리 없이 대상 파일 목록만 확인:

```bash
fin-stat-detect detect ./data/ --dry-run
```

### 요약만 출력 (이미지 생성 없음)

이미지를 생성하지 않고 탐지 결과 요약만 출력:

```bash
fin-stat-detect detect report.pdf --summary-only
```

### 전체 옵션

| 옵션 | 단축 | 설명 | 기본값 |
|------|------|------|--------|
| `--output` | `-o` | 출력 JSON 파일 경로 | `<input>_labels.json` |
| `--images-dir` | `-i` | 이미지 저장 디렉토리 | `./images/` |
| `--firm` | `-f` | 증권사 이름 필터 (파일명 매칭) | 전체 |
| `--detectors` | `-d` | 사용할 탐지기 (쉼표 구분) | `pdfplumber,camelot_lattice` |
| `--dpi` | | 이미지 해상도 | `150` |
| `--dry-run` | | 처리 대상만 표시 | `False` |
| `--summary-only` | `-s` | 요약만 출력 (이미지 생성 안 함) | `False` |

### 사용 예시

```bash
# 기본 사용
fin-stat-detect detect report.pdf

# 출력 경로 지정
fin-stat-detect detect report.pdf -o output/labels.json -i output/images/

# 고해상도 이미지 생성
fin-stat-detect detect report.pdf --dpi 300

# 특정 탐지기만 사용
fin-stat-detect detect report.pdf --detectors pdfplumber

# 모든 탐지기 사용
fin-stat-detect detect report.pdf --detectors "pdfplumber,camelot_lattice,camelot_stream"

# 증권사 필터 + 배치 처리
fin-stat-detect detect ./reports/ --firm "삼성증권" -o samsung_labels.json
```

## 출력 형식

### Label Studio JSON

```json
[
  {
    "data": {
      "image": "./images/report_page_001.jpg"
    },
    "predictions": [
      {
        "model_version": "ensemble-v1",
        "result": [
          {
            "id": "abc12345",
            "type": "rectanglelabels",
            "from_name": "label",
            "to_name": "image",
            "value": {
              "x": 10.5,
              "y": 15.2,
              "width": 80.0,
              "height": 30.0,
              "rotation": 0,
              "rectanglelabels": ["income_statement"]
            }
          }
        ]
      }
    ]
  }
]
```

### 재무제표 카테고리

| 카테고리 | 설명 |
|----------|------|
| `income_statement` | 손익계산서 |
| `balance_sheet` | 재무상태표 |
| `cash_flow` | 현금흐름표 |
| `equity_statement` | 자본변동표 |

## 프로젝트 구조

```
src/fin_stat_table_detector/
├── models.py              # BBox, TableCandidate, FinancialTable 데이터 모델
├── ensemble.py            # EnsembleDetector (다중 탐지기 앙상블)
├── detectors/
│   ├── base.py            # AbstractDetector 인터페이스
│   ├── pdfplumber_det.py  # pdfplumber 기반 탐지기
│   ├── camelot_det.py     # Camelot 기반 탐지기
│   └── docling_det.py     # Docling ML 기반 탐지기
├── classifiers/
│   ├── constants.py       # 재무제표 키워드 상수
│   └── financial.py       # 재무제표 분류기
├── exporters/
│   ├── converters.py      # 좌표 변환 유틸리티
│   └── label_studio.py    # Label Studio JSON 내보내기
├── cli/
│   ├── main.py            # CLI 진입점
│   └── commands/
│       └── detect.py      # detect 명령어
└── utils/
    ├── spatial_index.py   # 공간 인덱스 (R-tree)
    └── union_find.py      # Union-Find 자료구조
```

## Python API 사용

CLI 대신 Python 코드에서 직접 사용할 수도 있습니다.

```python
from fin_stat_table_detector import EnsembleDetector, BBox, FinancialTable
from fin_stat_table_detector.detectors import PdfplumberDetector, CamelotDetector
from fin_stat_table_detector.exporters import LabelStudioExporter, PageDimensions

# 탐지기 설정
detectors = [
    PdfplumberDetector(),
    CamelotDetector(flavor="lattice"),
]
ensemble = EnsembleDetector(detectors)

# 재무제표 탐지
tables = ensemble.detect_financial_tables("report.pdf")

for table in tables:
    print(f"Page {table.page}: {table.category} (confidence: {table.confidence:.2f})")
    print(f"  Keywords: {table.matched_keywords}")
    print(f"  BBox: ({table.bbox.x0}, {table.bbox.y0}, {table.bbox.x1}, {table.bbox.y1})")

# Label Studio 형식으로 내보내기
exporter = LabelStudioExporter()
dims = PageDimensions(pdf_width=612, pdf_height=792, image_width=1224, image_height=1584)
exporter.add_page_results("/images/page_001.jpg", tables, dims)
exporter.save("output.json")
```

## 테스트

```bash
# 전체 테스트 실행
uv run pytest tests/ -v

# 특정 모듈 테스트
uv run pytest tests/test_cli.py -v
uv run pytest tests/test_converters.py -v
uv run pytest tests/test_label_studio_exporter.py -v
```

## 라이선스

MIT License
