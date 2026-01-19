# PDF Analyzer - Technical Specification

## 1. 프로젝트 개요

### 1.1 목적

PDF 파일의 내부 구조를 분석하여 PDF 포맷에 익숙하지 않은 사용자가 "under the hood"를 이해할 수 있도록 돕는 CLI 도구입니다.

### 1.2 배경

- 증권사 리포트 PDF 500개를 훈련 데이터로 수집 완료
- Table Recognition 시스템 개발 전, PDF 데이터의 특성 파악 필요
- PDF 내부 구조(텍스트, 선, 이미지, 테이블 등)에 대한 이해 부족

### 1.3 핵심 가치

1. **교육적**: PDF 포맷을 모르는 사람도 이해할 수 있는 출력
2. **실용적**: 훈련 데이터 특성 파악에 직접 활용 가능
3. **단순함**: 복잡한 설정 없이 바로 사용 가능한 CLI

---

## 2. PDF 구조 기초

### 2.1 PDF의 기본 요소

PDF 파일은 다음과 같은 요소들로 구성됩니다:

| 요소 | 설명 | 예시 |
|------|------|------|
| **Chars** | 개별 문자와 좌표 | 'A' at (72.0, 100.5) |
| **Words** | 문자들의 그룹 | "삼성전자" |
| **Lines** | 선 객체 (테이블 경계 등) | (x0, y0) → (x1, y1) |
| **Rects** | 사각형 객체 | 배경색, 테이블 셀 |
| **Curves** | 곡선 객체 | 차트, 도형 |
| **Images** | 임베디드 이미지 | 로고, 차트 이미지 |

### 2.2 좌표계

- PDF 좌표계는 **왼쪽 하단이 원점 (0, 0)**
- 단위는 **포인트 (1 point = 1/72 inch)**
- pdfplumber는 **왼쪽 상단 기준**으로 변환하여 제공

---

## 3. 기능 명세

### 3.1 명령어 구조

```bash
uv run python main.py <command> [options] <pdf_file>
```

### 3.2 Commands

#### 3.2.1 `info` - 문서 기본 정보

PDF 파일의 메타데이터와 구조 요약을 출력합니다.

```bash
uv run python main.py info sample.pdf
```

**출력 예시:**
```
=== PDF Document Info ===
File: sample.pdf
Pages: 15
Size: 2.3 MB

=== Metadata ===
Title: 삼성전자 기업분석 리포트
Author: 한화투자증권
Creator: Microsoft Word
CreationDate: 2026-01-15
ModDate: 2026-01-15

=== Page Summary ===
Page  Size (pt)      Chars   Words   Lines   Rects   Images
----  -----------    -----   -----   -----   -----   ------
1     595 x 842      1,234   256     45      12      3
2     595 x 842      2,456   512     120     48      1
...
Total               15,678   3,245   890     234     15
```

#### 3.2.2 `page` - 페이지 상세 분석

특정 페이지의 요소들을 상세 분석합니다.

```bash
uv run python main.py page sample.pdf --page 1
uv run python main.py page sample.pdf --page 1 --element chars
uv run python main.py page sample.pdf --page 1 --element lines
uv run python main.py page sample.pdf --page 1 --element images
```

**출력 예시 (chars):**
```
=== Page 1 Characters (first 20) ===
#     Char   X0      Top     Font                Size
----  ----   ------  ------  ------------------  ----
1     '삼'   72.0    50.5    NanumGothic-Bold    24.0
2     '성'   96.0    50.5    NanumGothic-Bold    24.0
3     '전'   120.0   50.5    NanumGothic-Bold    24.0
...

=== Font Usage ===
Font                    Count   Percentage
--------------------    -----   ----------
NanumGothic-Bold        234     18.9%
NanumGothic             892     72.3%
Arial                   108     8.8%
```

**출력 예시 (lines):**
```
=== Page 1 Lines ===
#     X0      Y0      X1      Y1      Width   Color
----  ------  ------  ------  ------  -----   -----
1     72.0    100.0   523.0   100.0   1.0     #000000
2     72.0    200.0   523.0   200.0   0.5     #808080
...

=== Line Statistics ===
Horizontal lines: 45
Vertical lines: 23
Total lines: 68
```

#### 3.2.3 `tables` - 테이블 감지 및 분석

페이지 내 테이블을 감지하고 구조를 분석합니다.

```bash
uv run python main.py tables sample.pdf
uv run python main.py tables sample.pdf --page 3
```

**출력 예시:**
```
=== Tables Detected ===
Page 3: 2 tables found

--- Table 1 (4 rows x 5 cols) ---
Location: (72.0, 150.0) - (523.0, 350.0)
+----------+----------+----------+----------+----------+
| 구분     | 2023     | 2024     | 2025E    | 2026E    |
+----------+----------+----------+----------+----------+
| 매출액   | 258.9    | 279.6    | 298.0    | 320.5    |
| 영업이익 | 6.6      | 8.5      | 12.0     | 15.2     |
| 당기순이익| 15.5    | 18.2     | 22.0     | 28.0     |
+----------+----------+----------+----------+----------+

--- Table 2 (3 rows x 3 cols) ---
...
```

#### 3.2.4 `visual` - 요소 위치 시각화 (ASCII)

페이지 내 요소들의 위치를 ASCII 아트로 시각화합니다.

```bash
uv run python main.py visual sample.pdf --page 1
uv run python main.py visual sample.pdf --page 1 --element lines
```

**출력 예시:**
```
=== Page 1 Layout (595 x 842 pt) ===
Scale: 1 char = ~10 pt

+-----------------------------------------------------------+
|  [IMG]                                        [IMG: logo] |
|                                                           |
|  ████████████████████████████████████████████            |  <- Text block
|  ████████████████████████████                            |
|                                                           |
|  ═══════════════════════════════════════════════════════ |  <- Horizontal line
|                                                           |
|  ┌─────────┬─────────┬─────────┬─────────┐               |  <- Table
|  │         │         │         │         │               |
|  ├─────────┼─────────┼─────────┼─────────┤               |
|  │         │         │         │         │               |
|  └─────────┴─────────┴─────────┴─────────┘               |
|                                                           |
+-----------------------------------------------------------+

Legend: [IMG]=Image  ███=Text  ═│┌┐└┘├┤┬┴┼=Lines/Table
```

#### 3.2.5 `stats` - 통계 분석 (다중 파일)

여러 PDF 파일의 통계를 집계합니다.

```bash
uv run python main.py stats ../data/한화투자증권/*.pdf
uv run python main.py stats ../data/**/*.pdf --limit 100
```

**출력 예시:**
```
=== PDF Collection Statistics ===
Files analyzed: 100
Total pages: 1,523

=== Page Size Distribution ===
A4 Portrait (595x842):  89.2%
A4 Landscape (842x595): 8.1%
Other:                  2.7%

=== Content Statistics ===
                    Min     Max     Avg     Median
-----------------   -----   -----   -----   ------
Chars per page      156     8,234   2,456   2,100
Lines per page      0       245     68      52
Images per page     0       12      2.3     2
Tables per page     0       8       1.2     1

=== Font Usage (Top 10) ===
Font                    Files   Percentage
--------------------    -----   ----------
NanumGothic             98      98.0%
NanumGothic-Bold        95      95.0%
...
```

---

## 4. 기술 스택

### 4.1 핵심 라이브러리

| 라이브러리 | 용도 | 선정 이유 |
|-----------|------|----------|
| **pdfplumber** | PDF 파싱 | 텍스트/선/이미지 좌표 추출에 강점 |
| **click** | CLI 프레임워크 | 직관적인 명령어 정의 |
| **rich** | 터미널 출력 | 테이블, 색상, 프로그레스바 지원 |

### 4.2 의존성

```toml
[project]
dependencies = [
    "pdfplumber>=0.11.0",
    "click>=8.1.0",
    "rich>=13.0.0",
]
```

---

## 5. 프로젝트 구조

```
pdf-analyzer/
├── main.py              # CLI 진입점
├── src/
│   ├── __init__.py
│   ├── analyzer.py      # PDF 분석 핵심 로직
│   ├── formatters.py    # 출력 포맷팅
│   └── visualizer.py    # ASCII 시각화
├── tests/
│   ├── __init__.py
│   ├── test_analyzer.py
│   ├── test_formatters.py
│   └── fixtures/
│       └── sample.pdf   # 테스트용 PDF
├── docs/
│   └── TECH_SPEC_overview.md
├── pyproject.toml
└── README.md
```

---

## 6. 구현 우선순위

### Phase 1: 기본 기능 (MVP)
1. `info` 명령어 - 문서 기본 정보
2. `page` 명령어 - 페이지 요소 분석
3. 기본 테스트 케이스

### Phase 2: 테이블 분석
4. `tables` 명령어 - 테이블 감지 및 출력

### Phase 3: 시각화 및 통계
5. `visual` 명령어 - ASCII 시각화
6. `stats` 명령어 - 다중 파일 통계

---

## 7. 테스트 전략

### 7.1 테스트 대상

- **단위 테스트**: 각 분석 함수의 정확성
- **통합 테스트**: CLI 명령어 동작 검증
- **실제 데이터 테스트**: 수집된 증권사 리포트로 검증

### 7.2 테스트 케이스 예시

```python
def test_info_returns_correct_page_count():
    """Given: 15페이지 PDF 파일
    When: info 명령 실행
    Then: page_count가 15를 반환해야 함
    """

def test_page_chars_includes_coordinates():
    """Given: 텍스트가 포함된 PDF 페이지
    When: page --element chars 실행
    Then: 각 문자에 x0, top 좌표가 포함되어야 함
    """

def test_tables_detects_financial_table():
    """Given: 재무제표가 포함된 증권사 리포트
    When: tables 명령 실행
    Then: 최소 1개 이상의 테이블이 감지되어야 함
    """
```

---

## 8. 결정 사항

### 8.1 테스트 전략 (결정됨)

**단위 테스트와 통합 테스트를 분리하여 두 가지 방식 모두 사용:**

- **단위 테스트**: reportlab으로 직접 생성한 PDF 사용
  - 재현성 보장, 저작권 문제 없음
  - 특정 시나리오 테스트 가능 (빈 페이지, 테이블만 있는 페이지 등)

- **통합/E2E 테스트**: 수집된 증권사 리포트 사용
  - 실제 데이터로 검증
  - `--ignore` 옵션으로 CI에서 제외 가능

### 8.2 JSON 출력 (결정됨)

**MVP에서는 터미널 출력만 지원, 필요시 나중에 추가**

- 현재 목적은 PDF 구조 이해이므로 사람이 읽기 쉬운 출력이 우선
- 파이프라인 연동이 필요해지면 `--format json` 옵션 추가 예정

### 8.3 대용량 처리 (미결정)

- 500개 파일 통계 분석 시 성능 최적화 필요 여부는 구현 후 판단
- 필요시 병렬 처리(multiprocessing) 또는 캐싱 적용

---

## 9. 참고 자료

- [pdfplumber Documentation](https://github.com/jsvine/pdfplumber)
- [PDF Reference Manual (Adobe)](https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/PDF32000_2008.pdf)
- [Click Documentation](https://click.palletsprojects.com/)
