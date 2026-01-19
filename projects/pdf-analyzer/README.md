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
