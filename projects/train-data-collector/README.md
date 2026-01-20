# Train Data Collector

증권사 종목분석 리포트 PDF 수집기

## 목표

네이버 금융(https://finance.naver.com/research/company_list.naver)에서 증권사 종목분석 리포트 PDF를 스크래핑하여 훈련용 데이터를 수집합니다.

이 프로젝트는 1주차 프로젝트의 일환으로, 재무제표 인식 시스템(Table Recognition)을 위한 학습 데이터를 확보하는 것이 목적입니다.

## 주요 기능

- 네이버 금융 리서치 페이지에서 종목분석 리포트 목록 수집
- 각 리포트의 PDF 파일 다운로드
- 메타데이터 관리 (증권사, 종목, 날짜 등)
- URL 및 MD5 해시 기반 중복 제거
- 증권사별 균등 분배 수집 전략

## 기술 스택

- Python 3.14
- 패키지 관리: uv
- HTTP 클라이언트: httpx
- HTML 파싱: BeautifulSoup4 + lxml

## 설치

```bash
cd projects/train-data-collector
uv sync
```

## 실행

### 기본 실행 (500개 PDF 수집)

```bash
uv run train-data-collector
```

### CLI 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--target` | 500 | 수집할 총 PDF 파일 수 |
| `--min-brokers` | 8 | 최소 증권사 수 |
| `--min-per-broker` | 5 | 증권사별 최소 수집 수 |
| `--delay-min` | 5.0 | 다운로드 간 최소 대기 시간(초) |
| `--delay-max` | 10.0 | 다운로드 간 최대 대기 시간(초) |
| `--data-dir` | ./data | PDF 저장 디렉토리 (현재 작업 디렉토리 기준) |
| `-v, --verbose` | false | 상세 로그 출력 |

### 사용 예시

```bash
# 테스트용 소량 수집
uv run train-data-collector --target 20 --min-brokers 3

# 상세 로그와 함께 실행
uv run train-data-collector --target 100 -v

# 커스텀 저장 경로
uv run train-data-collector --data-dir ./my_data

# 다운로드 간격 조정 (rate limiting)
uv run train-data-collector --delay-min 3 --delay-max 7
```

## 데이터 구조

```
data/
├── metadata.json              # 수집된 리포트 메타데이터
├── 한화투자증권/
│   ├── 2026-01-19_01.pdf
│   ├── 2026-01-19_02.pdf
│   └── 2026-01-18_01.pdf
├── 미래에셋증권/
│   └── 2026-01-19_01.pdf
└── ...
```

### metadata.json 구조

```json
{
  "reports": {
    "https://...pdf": {
      "pdf_url": "https://...",
      "broker": "한화투자증권",
      "stock_name": "삼성전자",
      "title": "리포트 제목",
      "date": "2026-01-19",
      "local_path": "한화투자증권/2026-01-19_01.pdf",
      "file_hash": "md5:abc123...",
      "downloaded_at": "2026-01-19T15:30:00"
    }
  },
  "hashes": {
    "md5:abc123...": "https://...pdf"
  }
}
```

## 중복 제거

스크래퍼는 두 단계의 중복 검사를 수행합니다:

1. **URL 중복 검사** (다운로드 전): 이미 수집된 PDF URL은 스킵
2. **컨텐츠 중복 검사** (다운로드 후): MD5 해시가 동일한 파일은 스킵

이를 통해 동일한 리포트가 다른 URL로 제공되는 경우도 중복을 방지합니다.

## 테스트

```bash
# 개발 의존성 설치
uv sync --extra dev

# 단위 테스트 실행
uv run pytest tests/ -v --ignore=tests/test_parser_e2e.py

# E2E 테스트 포함 (네트워크 필요)
uv run pytest tests/ -v
```
