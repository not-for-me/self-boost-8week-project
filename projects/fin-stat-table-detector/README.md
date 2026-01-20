# fin-stat-table-detector

PDF 증권사 리포트에서 재무제표 테이블을 자동으로 탐지하고, Label Studio 형식으로 내보내는 도구입니다.

## 주요 기능

- **ML 기반 탐지**: Docling(IBM Research)의 AI 레이아웃 모델로 선 없는 표도 정확하게 탐지
- **OCR 지원**: 이미지 기반 PDF에서도 텍스트 추출 가능 (증권사 리포트에 특화)
- **재무제표 자동 분류**: 손익계산서, 재무상태표, 현금흐름표, 투자지표 자동 분류
- **IoU 기반 중복 제거**: 겹치는 영역 자동 제거
- **Label Studio 내보내기**: 탐지 결과를 Label Studio 호환 JSON 형식으로 내보내기
- **병렬 처리**: 대량 PDF 배치 처리 시 멀티프로세싱 지원
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

> **Note**: 첫 실행 시 Docling 모델 다운로드에 약 2-3분이 소요됩니다.

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

### 병렬 처리

대량의 PDF를 멀티프로세싱으로 빠르게 처리:

```bash
# 병렬 처리 활성화 (기본 워커 수: CPU 코어 수)
fin-stat-detect detect ./data/ --parallel

# 워커 수 지정
fin-stat-detect detect ./data/ --parallel --workers 4
```

출력 형식 (패키지 인스톨러 스타일):
```
Using detectors: docling
Workers: 4

Processing 44 files with 4 workers...

✓ 2025-12-10_01.pdf (6 pages, 2 tables)
✓ 2025-12-10_02.pdf (7 pages, 2 tables)
◐ 2025-12-10_03.pdf
  2025-12-11_01.pdf
  ...

[44/44]

                 Detection Summary
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━┓
┃ PDF               ┃ Pages ┃ Tables ┃ Categories  ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━┩
│ 2025-12-10_01.pdf │     6 │      2 │ valuation:2 │
...
└───────────────────┴───────┴────────┴─────────────┘

Elapsed time: 123.45s
```

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
| `--dpi` | | 이미지 해상도 | `150` |
| `--dry-run` | | 처리 대상만 표시 | `False` |
| `--summary-only` | `-s` | 요약만 출력 (이미지 생성 안 함) | `False` |
| `--parallel` | `-p` | 병렬 처리 활성화 | `False` |
| `--workers` | `-w` | 워커 프로세스 수 | CPU 코어 수 |

### 사용 예시

```bash
# 기본 사용
fin-stat-detect detect report.pdf

# 출력 경로 지정
fin-stat-detect detect report.pdf -o output/labels.json -i output/images/

# 고해상도 이미지 생성
fin-stat-detect detect report.pdf --dpi 300

# 병렬 처리 + 요약만 출력
fin-stat-detect detect ./data/ --parallel --workers 4 --summary-only
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
| `valuation` | 투자지표 (EPS, PER, ROE 등) |
| `performance` | 실적 추이 (YoY, QoQ 등) |

## 프로젝트 구조

```
src/fin_stat_table_detector/
├── models.py              # BBox, TableCandidate, FinancialTable 데이터 모델
├── ensemble.py            # EnsembleDetector (중복 제거 + 분류)
├── detectors/
│   ├── base.py            # AbstractDetector 인터페이스
│   └── docling_det.py     # Docling ML 기반 탐지기 (OCR 내장)
├── classifiers/
│   ├── constants.py       # 재무제표 키워드 상수
│   └── financial.py       # 재무제표 분류기
├── exporters/
│   ├── converters.py      # 좌표 변환 유틸리티
│   └── label_studio.py    # Label Studio JSON 내보내기
├── cli/
│   ├── main.py            # CLI 진입점
│   └── commands/
│       └── detect.py      # detect 명령어 (병렬 처리 지원)
└── utils/
    ├── spatial_index.py   # 공간 인덱스 (Interval Tree 기반)
    └── union_find.py      # Union-Find 자료구조
```

## Python API 사용

CLI 대신 Python 코드에서 직접 사용할 수도 있습니다.

```python
from fin_stat_table_detector import EnsembleDetector
from fin_stat_table_detector.detectors import DoclingDetector
from fin_stat_table_detector.exporters import LabelStudioExporter, PageDimensions

# 탐지기 설정 (OCR 기본 활성화)
detector = DoclingDetector(force_ocr=True)
ensemble = EnsembleDetector([detector])

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

### OCR 비활성화

텍스트 기반 PDF만 처리하는 경우 OCR을 비활성화하여 처리 속도를 높일 수 있습니다:

```python
detector = DoclingDetector(force_ocr=False)
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
