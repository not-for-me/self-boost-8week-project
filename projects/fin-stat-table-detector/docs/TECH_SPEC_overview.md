# TECH_SPEC: Financial Statement Table Detector - Overview

## 1. 프로젝트 개요

### 1.1 목적

증권사 PDF 리포트에서 **재무제표 테이블의 위치(page, bbox)**를 반환하는 모듈 구현

### 1.2 배경

- 최종 목표: 소형 LLM 기반 재무제표 QA 시스템 구축
- 본 모듈의 역할: PDF에서 재무제표 영역을 탐지하는 첫 번째 단계
- 문제점: 증권사 리포트는 이미지 기반 PDF가 많아 텍스트 추출이 어려움
- 해결책: Docling ML 기반 탐지기 + OCR로 이미지 기반 PDF 지원

### 1.3 핵심 설계 원칙

1. **ML 기반 탐지**: Docling으로 선 없는 표도 정확하게 탐지
2. **OCR 지원**: 이미지 기반 PDF에서도 텍스트 추출 가능
3. **재무제표 특화 분류**: 모든 표가 아닌 재무제표만 필터링
4. **병렬 처리**: 대량 PDF 배치 처리 시 성능 최적화

---

## 2. 시스템 아키텍처

### 2.1 모듈 구조

```
projects/fin-stat-table-detector/
├── pyproject.toml
├── README.md
├── docs/
│   ├── TECH_SPEC_overview.md      # 본 문서
│   ├── TECH_SPEC_models.md        # 데이터 모델 스펙
│   ├── TECH_SPEC_detectors.md     # 탐지기 스펙
│   ├── TECH_SPEC_classifier.md    # 분류기 스펙
│   └── TECH_SPEC_ensemble.md      # 앙상블 및 병합 스펙
├── src/
│   └── fin_stat_table_detector/
│       ├── __init__.py
│       ├── models.py              # BBox, TableCandidate, FinancialTable
│       ├── detectors/
│       │   ├── __init__.py
│       │   ├── base.py            # AbstractDetector 인터페이스
│       │   └── docling_det.py     # DoclingDetector (ML 기반 + OCR)
│       ├── classifiers/
│       │   ├── __init__.py
│       │   ├── constants.py       # 재무제표 키워드 상수
│       │   └── financial.py       # FinancialTableClassifier
│       ├── exporters/
│       │   ├── converters.py      # 좌표 변환 유틸리티
│       │   └── label_studio.py    # Label Studio JSON 내보내기
│       ├── cli/
│       │   ├── main.py            # CLI 진입점
│       │   └── commands/
│       │       └── detect.py      # detect 명령어
│       └── utils/
│           ├── union_find.py      # UnionFind 자료구조
│           └── spatial_index.py   # SpatialIndex (Interval Tree 기반)
└── tests/
    └── ...
```

### 2.2 데이터 흐름

```
┌─────────────┐
│   PDF 파일   │
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────────┐
│           EnsembleDetector               │
│  ┌─────────────────────────────────────┐ │
│  │         1. Docling 탐지기 실행       │ │
│  │  ┌────────────────────────────────┐ │ │
│  │  │   DoclingDetector (ML + OCR)   │ │ │
│  │  │   - force_full_page_ocr=True   │ │ │
│  │  │   - 이미지 기반 PDF 지원        │ │ │
│  │  └────────────────┬───────────────┘ │ │
│  │                   ▼                 │ │
│  │         TableCandidate[]            │ │
│  └─────────────────────────────────────┘ │
│  ┌─────────────────────────────────────┐ │
│  │      2. 중복 제거 (IoU 기반)         │ │
│  │  Union-Find + Spatial Index         │ │
│  └─────────────────────────────────────┘ │
│  ┌─────────────────────────────────────┐ │
│  │   3. 재무제표 분류                   │ │
│  │  FinancialTableClassifier           │ │
│  └─────────────────────────────────────┘ │
└──────────────────────┬───────────────────┘
                       │
                       ▼
              ┌────────────────┐
              │ FinancialTable[] │
              │ (page, bbox,    │
              │  category,      │
              │  confidence)    │
              └────────────────┘
```

---

## 3. Docling 탐지기

### 3.1 Docling 소개

[Docling](https://docling-project.github.io/docling/)은 IBM Research에서 개발한 AI 기반 문서 파싱 도구입니다.

**장점**:
- ML 레이아웃 모델(YOLO/DETR 계열)로 선 없는 표도 탐지
- 테이블 구조 인식(Table Structure Recognition)까지 내장
- pandas DataFrame으로 직접 export 가능
- OCR 내장으로 이미지 기반 PDF 지원

**단점**:
- 첫 실행 시 모델 다운로드 (~2.5분)
- 처리 속도가 rule-based 대비 느림
- GPU 없으면 대량 처리 시 병목

### 3.2 OCR 지원

이미지 기반 PDF(텍스트가 이미지로 렌더링된 PDF)를 처리하기 위해 `force_full_page_ocr=True` 옵션을 기본으로 사용합니다.

```python
from docling.datamodel.pipeline_options import OcrAutoOptions, PdfPipelineOptions

pipeline_options = PdfPipelineOptions(
    do_ocr=True,
    ocr_options=OcrAutoOptions(force_full_page_ocr=True),
)
```

---

## 4. 의존성

```toml
[project]
name = "fin-stat-table-detector"
version = "0.1.0"
requires-python = ">=3.13,<3.14"
dependencies = [
    "click>=8.0.0",
    "docling>=2.0.0",
    "intervaltree>=3.1.0",
    "opencv-contrib-python-headless>=4.0.0",
    "pdf2image>=1.16.0",
    "pypdf>=5.0.0",
    "rich>=13.0.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=4.0.0",
]
```

**시스템 의존성**:
```bash
# macOS
brew install poppler

# Ubuntu/Debian
sudo apt install poppler-utils
```

**설치**:
```bash
uv sync
```

---

## 5. CLI 사용법

### 5.1 기본 사용

```python
from fin_stat_table_detector import EnsembleDetector
from fin_stat_table_detector.detectors import DoclingDetector

# 탐지기 초기화
detector = EnsembleDetector([
    DoclingDetector(force_ocr=True),  # OCR 활성화 (기본값)
])

# 재무제표 탐지
results = detector.detect_financial_tables("report.pdf")

for table in results:
    print(f"Page {table.page}: {table.category}")
    print(f"  위치: ({table.bbox.x0}, {table.bbox.y0}) - ({table.bbox.x1}, {table.bbox.y1})")
    print(f"  신뢰도: {table.confidence:.2f}")
    print(f"  매칭 키워드: {table.matched_keywords}")
```

### 5.2 CLI 명령어

```bash
# 단일 PDF 처리
fin-stat-detect detect report.pdf

# 디렉토리 배치 처리
fin-stat-detect detect ./data/

# 병렬 처리 (4 workers)
fin-stat-detect detect ./data/ --parallel --workers 4

# 요약만 출력 (이미지 생성 없음)
fin-stat-detect detect report.pdf --summary-only

# 처리 대상 미리보기
fin-stat-detect detect ./data/ --dry-run
```

### 5.3 CLI 옵션

| 옵션 | 단축 | 설명 | 기본값 |
|------|------|------|--------|
| `--output` | `-o` | 출력 JSON 파일 경로 | `<input>_labels.json` |
| `--images-dir` | `-i` | 이미지 저장 디렉토리 | `./images/` |
| `--dpi` | | 이미지 해상도 | `150` |
| `--dry-run` | | 처리 대상만 표시 | `False` |
| `--summary-only` | `-s` | 요약만 출력 (이미지 생성 안 함) | `False` |
| `--parallel` | `-p` | 병렬 처리 활성화 | `False` |
| `--workers` | `-w` | 워커 프로세스 수 | CPU 코어 수 |

### 5.4 병렬 처리

대량의 PDF를 처리할 때 `--parallel` 옵션을 사용하면 여러 파일을 동시에 처리할 수 있습니다.

```bash
fin-stat-detect detect ./data/ --parallel --workers 4 --summary-only
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

---

## 6. 구현 순서

1. **Phase 1**: 데이터 모델 구현 (`models.py`)
2. **Phase 2**: 유틸리티 구현 (`union_find.py`, `spatial_index.py`)
3. **Phase 3-5**: DoclingDetector 구현 (ML 기반 + OCR)
4. **Phase 6**: FinancialTableClassifier 구현
5. **Phase 7**: EnsembleDetector 구현 (통합 + 중복 제거)
6. **Phase 8**: CLI 구현 (detect 명령어, 병렬 처리)
7. **Phase 9**: Label Studio 내보내기 구현

---

## 7. 테스트 데이터

기존 수집된 PDF는 `train-data-collector` 프로젝트에서 수집된 파일 사용:
- 경로: `projects/data/`
- 증권사: 미래에셋증권, 한화투자증권, 삼성증권, iM증권 등
