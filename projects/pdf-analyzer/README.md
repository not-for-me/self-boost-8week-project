# PDF Analyzer

PDF 파일의 내부 구조를 분석하는 CLI 도구

## 목표

PDF 포맷에 익숙하지 않은 사용자가 PDF 파일의 "under the hood"를 이해할 수 있도록 돕습니다.

## 설치

```bash
cd projects/pdf-analyzer
uv sync
```

## 사용법

### `info` - 문서 정보 확인

```bash
uv run python main.py info sample.pdf
```

출력 예시:
```
╭───────────────────────────── PDF Document Info ──────────────────────────────╮
│ sample.pdf                                                                   │
╰──────────────────────────────────────────────────────────────────────────────╯
  File     sample.pdf
  Size     2.0 KB
  Pages    1

Page Summary
  Page  Size (pt)  Chars  Lines  Rects  Images
     1  595 x 842    375      2      1       0
 Total               375      2      1       0
```

### `page` - 페이지 상세 분석

```bash
# 페이지 요약
uv run python main.py page sample.pdf

# 특정 페이지 분석
uv run python main.py page sample.pdf --page 2

# 문자 정보 상세 보기
uv run python main.py page sample.pdf -e chars

# 선 객체 분석
uv run python main.py page sample.pdf -e lines

# 이미지 정보
uv run python main.py page sample.pdf -e images

# 출력 개수 제한
uv run python main.py page sample.pdf -e chars --limit 50
```

### `tables` - 테이블 감지 및 분석

```bash
# 전체 문서의 테이블 분석
uv run python main.py tables sample.pdf

# 특정 페이지의 테이블만 분석
uv run python main.py tables sample.pdf --page 3

# 테이블 요약만 보기 (어느 페이지에 몇 개)
uv run python main.py tables sample.pdf --summary

# 셀 내용 숨기기
uv run python main.py tables sample.pdf --no-content

# 열 너비 조정
uv run python main.py tables sample.pdf --col-width 20
```

출력 예시:
```
╭────────────────────────────── Tables Detected ───────────────────────────────╮
│ 1 table(s) found on 1 page(s)                                                │
╰──────────────────────────────────────────────────────────────────────────────╯

Page 1: 1 table(s)

Table 1 (4 rows x 4 cols)
Location: (72.0, 150.0) - (432.0, 250.0) | Size: 360.0 x 100.0 pt
 Category         2023   2024   2025E
 Revenue          258.9  279.6  298.0
 Operating Pro..  6.6    8.5    12.0
 Net Income       15.5   18.2   22.0
```

### `visual` - ASCII 시각화

```bash
# 페이지 레이아웃 시각화
uv run python main.py visual sample.pdf

# 특정 페이지 시각화
uv run python main.py visual sample.pdf --page 2

# 크기 조정
uv run python main.py visual sample.pdf --width 80 --height 40

# 테이블 경계 포함
uv run python main.py visual sample.pdf --with-tables
```

출력 예시:
```
============================================================
                   Page 1 (595 x 842 pt)
============================================================
+------------------------------------------------------------+
|       ██ █ █████ ██ ███ ██ █ ██ █                          |
|       ══════════════════════════════════════════════       |
|      ║██████████████████████████████████████               |
|      ║██████████████████████████████                       |
+------------------------------------------------------------+

Legend:
  █ = Text    ═/║ = Lines    ─│ = Table    ▓ = Image
```

### `stats` - 다중 파일 통계

```bash
# 여러 파일 통계
uv run python main.py stats *.pdf

# 하위 폴더 포함
uv run python main.py stats ../data/**/*.pdf

# 분석 파일 수 제한
uv run python main.py stats ../data/**/*.pdf --limit 100
```

출력 예시:
```
╭───────────────────────── PDF Collection Statistics ──────────────────────────╮
│ 100 file(s) analyzed, 1,523 total pages                                      │
╰──────────────────────────────────────────────────────────────────────────────╯

Page Size Distribution
 Size         Count  Percentage
 A4 Portrait   1420       93.2%
 A4 Landscape   103        6.8%

Content Statistics (per page)
 Metric       Min    Max    Avg  Median
 Characters   156  8,234  2,456   2,100
 Lines          0    245     68      52
```

## CLI 옵션

### `info` 명령어

| 인자 | 설명 |
|------|------|
| `PDF_FILE` | 분석할 PDF 파일 경로 |

### `page` 명령어

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--page, -p` | 1 | 분석할 페이지 번호 (1부터 시작) |
| `--element, -e` | (요약) | 표시할 요소 (chars, lines, rects, images) |
| `--limit, -l` | 20 | 표시할 최대 항목 수 |

### `tables` 명령어

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--page, -p` | (전체) | 특정 페이지만 분석 |
| `--summary, -s` | false | 요약만 표시 (테이블 개수) |
| `--no-content` | false | 셀 내용 숨기기 |
| `--col-width, -w` | 15 | 열 최대 너비 |

### `visual` 명령어

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--page, -p` | 1 | 시각화할 페이지 번호 |
| `--width, -w` | 60 | 시각화 너비 (문자) |
| `--height, -h` | 30 | 시각화 높이 (문자) |
| `--with-tables, -t` | false | 테이블 경계 표시 |

### `stats` 명령어

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--limit, -l` | (전체) | 분석할 최대 파일 수 |

## PDF 요소 설명

| 요소 | 설명 |
|------|------|
| **Chars** | 개별 문자와 좌표, 폰트 정보 |
| **Lines** | 선 객체 (테이블 경계, 구분선 등) |
| **Rects** | 사각형 객체 (배경색, 테이블 셀 등) |
| **Images** | 임베디드 이미지 |

## 좌표계

- PDF 좌표계는 **포인트(pt)** 단위 (1pt = 1/72 inch)
- pdfplumber는 **왼쪽 상단 기준** 좌표 사용
- `x0`: 왼쪽 x 좌표
- `top`: 위쪽 y 좌표

## 테스트

```bash
uv run pytest tests/ -v
```

## 기술 스택

- **pdfplumber**: PDF 파싱
- **click**: CLI 프레임워크
- **rich**: 터미널 출력 포맷팅
