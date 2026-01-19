# TECH_SPEC: 네이버 금융 종목분석 리포트 스크래퍼

## 1. 개요

### 1.1 목적
네이버 금융 리서치 페이지에서 증권사 종목분석 리포트 PDF를 수집하여 Table Recognition 모델 학습용 데이터를 확보한다.

### 1.2 목표
- **총 수집 목표**: 500개 PDF 파일
- **최소 증권사 수**: 8개 이상
- **증권사별 최소 리포트**: 5개 이상
- **다양성 확보**: 증권사별 리포트 양식 차이를 반영하여 균등 분배

### 1.3 데이터 소스
- URL: `https://finance.naver.com/research/company_list.naver`
- 페이지네이션 지원: `?page=N` 파라미터

## 2. 시스템 아키텍처

```
train-data-collector/
├── src/
│   ├── __init__.py
│   ├── scraper.py          # 메인 스크래퍼 로직
│   ├── downloader.py       # PDF 다운로드 담당
│   ├── parser.py           # HTML 파싱 (리포트 목록 추출)
│   └── config.py           # 설정 상수
├── tests/
│   ├── __init__.py
│   ├── test_parser.py
│   ├── test_downloader.py
│   └── test_scraper.py
├── docs/
│   └── TECH_SPEC_scraper.md
├── main.py                 # 실행 진입점
└── pyproject.toml
```

### 2.1 데이터 저장 구조

```
projects/
├── train-data-collector/   # 프로젝트 폴더
└── data/                   # 데이터 저장 폴더 (프로젝트 상위)
    ├── 삼성증권/
    │   ├── 2025-01-15_01.pdf
    │   ├── 2025-01-15_02.pdf
    │   └── 2025-01-14_01.pdf
    ├── 미래에셋증권/
    │   ├── 2025-01-15_01.pdf
    │   └── ...
    └── ...
```

## 3. 핵심 컴포넌트

### 3.1 Parser (`src/parser.py`)

네이버 금융 리서치 페이지에서 리포트 정보를 추출한다.

#### 추출 대상 정보
| 필드 | 설명 | 예시 |
|------|------|------|
| `title` | 리포트 제목 | "삼성전자 - 실적 전망" |
| `broker` | 증권사명 | "삼성증권" |
| `stock_name` | 종목명 | "삼성전자" |
| `date` | 작성일 | "2025.01.15" |
| `pdf_url` | PDF 다운로드 URL | "https://..." |

#### 인터페이스
```python
@dataclass
class ReportInfo:
    title: str
    broker: str
    stock_name: str
    date: str          # 원본 포맷 (예: "25.01.15")
    pdf_url: str

    def get_formatted_date(self) -> str:
        """yyyy-mm-dd 포맷으로 변환"""
        ...

def parse_report_list(html: str) -> list[ReportInfo]:
    """HTML에서 리포트 목록 파싱"""
    ...

def get_total_pages(html: str) -> int:
    """총 페이지 수 추출"""
    ...
```

### 3.2 Downloader (`src/downloader.py`)

PDF 파일 다운로드 및 저장을 담당한다.

#### Rate Limiting 정책
- 다운로드 간 **5~10초 랜덤 딜레이** (jitter)
- User-Agent 헤더 설정 (브라우저 모방)
- 실패 시 최대 3회 재시도 (exponential backoff)

#### 인터페이스
```python
class PDFDownloader:
    def __init__(self, base_dir: Path, delay_range: tuple[float, float] = (5.0, 10.0)):
        ...

    def download(self, report: ReportInfo) -> Path | None:
        """
        PDF 다운로드 후 저장 경로 반환.
        실패 시 None 반환.
        """
        ...

    def _generate_filename(self, report: ReportInfo, existing_files: list[str]) -> str:
        """
        파일명 생성: {date}_{seq}.pdf
        같은 날짜에 여러 파일이 있으면 seq 증가 (01, 02, ...)
        """
        ...

    def _wait_with_jitter(self) -> None:
        """랜덤 딜레이 적용"""
        ...
```

### 3.3 Scraper (`src/scraper.py`)

전체 스크래핑 프로세스를 조율하는 메인 컨트롤러.

#### 수집 전략
1. **Phase 1 - 증권사 목록 수집**: 첫 N 페이지를 스캔하여 활성 증권사 목록 파악
2. **Phase 2 - 균등 분배 수집**: 각 증권사별로 목표 수량만큼 순환하며 수집

#### 균등 분배 알고리즘
```
목표: 500개, 증권사 8개 이상
기본 할당: 500 / 8 = 62.5 → 증권사당 약 63개
최소 보장: 5개 이상

수집 순서:
1. 모든 증권사에서 5개씩 수집 (최소 보장)
2. 남은 목표량을 라운드 로빈 방식으로 분배
3. 특정 증권사 리포트가 소진되면 다른 증권사에서 추가 수집
```

#### 인터페이스
```python
@dataclass
class CollectionConfig:
    total_target: int = 500
    min_brokers: int = 8
    min_per_broker: int = 5
    delay_range: tuple[float, float] = (5.0, 10.0)

@dataclass
class CollectionStats:
    total_downloaded: int
    by_broker: dict[str, int]
    failed: int
    skipped: int  # 중복 등으로 스킵

class ReportScraper:
    def __init__(self, config: CollectionConfig, data_dir: Path):
        ...

    def run(self) -> CollectionStats:
        """전체 수집 프로세스 실행"""
        ...

    def _fetch_page(self, page: int) -> str:
        """페이지 HTML 가져오기"""
        ...

    def _should_continue(self, stats: CollectionStats) -> bool:
        """수집 계속 여부 판단"""
        ...
```

### 3.4 Config (`src/config.py`)

```python
# URLs
BASE_URL = "https://finance.naver.com/research/company_list.naver"

# HTTP Headers
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}

# Rate Limiting
DEFAULT_DELAY_RANGE = (5.0, 10.0)  # seconds
MAX_RETRIES = 3
RETRY_BACKOFF = 2.0  # exponential backoff multiplier

# Collection Targets
DEFAULT_TOTAL_TARGET = 500
DEFAULT_MIN_BROKERS = 8
DEFAULT_MIN_PER_BROKER = 5
```

## 4. 데이터 흐름

```
┌─────────────────┐
│  main.py        │
│  (entrypoint)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Scraper        │
│                 │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌───────┐  ┌──────────┐
│Parser │  │Downloader│
│       │  │          │
└───────┘  └──────────┘
    │            │
    ▼            ▼
[리포트 목록]  [PDF 저장]
                 │
                 ▼
         ../data/{증권사}/
         {date}_{seq}.pdf
```

## 5. 에러 처리

### 5.1 네트워크 에러
- **Connection Error**: 재시도 (최대 3회, exponential backoff)
- **HTTP 4xx**: 로그 기록 후 스킵
- **HTTP 5xx**: 재시도 후 실패 시 스킵
- **Timeout**: 30초 타임아웃, 재시도

### 5.2 파싱 에러
- HTML 구조 변경 감지 시 경고 로그
- 필수 필드 누락 시 해당 리포트 스킵

### 5.3 파일 시스템 에러
- 디스크 공간 부족: 즉시 중단, 현재까지 통계 출력
- 권한 에러: 즉시 중단

## 6. 로깅

```python
# 로그 레벨별 출력
INFO:  수집 진행 상황 (10개마다)
INFO:  증권사별 현황 요약
WARNING: 스킵된 리포트 (파싱 실패, 중복 등)
ERROR: 다운로드 실패, 재시도 소진
DEBUG: 상세 HTTP 요청/응답 정보
```

### 출력 예시
```
[INFO] 수집 시작: 목표 500개, 최소 8개 증권사
[INFO] 페이지 1 스캔 완료: 15개 증권사 발견
[INFO] [10/500] 삼성증권: 2025-01-15_01.pdf 다운로드 완료
[INFO] [20/500] 미래에셋증권: 2025-01-15_01.pdf 다운로드 완료
...
[INFO] === 수집 완료 ===
[INFO] 총 다운로드: 500개
[INFO] 증권사별 현황:
       - 삼성증권: 65개
       - 미래에셋증권: 63개
       - ...
[INFO] 실패: 3개, 스킵: 12개
```

## 7. 테스트 케이스

### 7.1 Parser 테스트 (`tests/test_parser.py`)

```python
def test_parse_report_list_extracts_all_fields():
    """Given: 유효한 HTML, When: 파싱, Then: 모든 필드 추출"""

def test_parse_report_list_handles_empty_page():
    """Given: 빈 페이지, When: 파싱, Then: 빈 리스트 반환"""

def test_get_formatted_date_converts_correctly():
    """Given: "25.01.15", When: 변환, Then: "2025-01-15" """

def test_get_total_pages_extracts_pagination():
    """Given: 페이지네이션 HTML, When: 추출, Then: 정확한 총 페이지 수"""
```

### 7.2 Downloader 테스트 (`tests/test_downloader.py`)

```python
def test_generate_filename_creates_sequential_numbers():
    """Given: 같은 날짜 파일 존재, When: 파일명 생성, Then: seq 증가"""

def test_download_saves_pdf_to_correct_path():
    """Given: 유효한 URL, When: 다운로드, Then: 올바른 경로에 저장"""

def test_download_applies_jitter_delay():
    """Given: 다운로더, When: 다운로드 2회, Then: 5-10초 간격"""
```

### 7.3 Scraper 테스트 (`tests/test_scraper.py`)

```python
def test_run_collects_minimum_brokers():
    """Given: 설정(min_brokers=8), When: 실행, Then: 8개 이상 증권사"""

def test_run_distributes_evenly():
    """Given: 목표 500개, When: 실행, Then: 증권사별 균등 분배"""

def test_should_continue_stops_at_target():
    """Given: 목표 도달, When: 체크, Then: False 반환"""
```

## 8. 의존성

```toml
[project]
dependencies = [
    "httpx>=0.27.0",      # HTTP 클라이언트 (async 지원)
    "beautifulsoup4>=4.12.0",  # HTML 파싱
    "lxml>=5.0.0",        # 빠른 HTML/XML 파서
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "respx>=0.21.0",      # httpx mocking
]
```

## 9. 실행 방법

```bash
# 기본 실행 (500개 목표)
cd projects/train-data-collector
uv run python main.py

# 옵션 지정 실행
uv run python main.py --target 100 --min-brokers 5

# 테스트 실행
uv run pytest tests/ -v
```

## 10. 제약 사항 및 고려 사항

### 10.1 법적/윤리적 고려
- 개인적 학습/연구 목적으로만 사용
- robots.txt 준수 여부 확인 필요
- 과도한 요청으로 서버 부하 유발 금지 (rate limiting 필수)

### 10.2 기술적 제약
- 네이버 금융 페이지 구조 변경 시 파서 수정 필요
- PDF URL이 동적 생성될 경우 추가 처리 필요
- 세션/쿠키 기반 접근 제한 가능성

### 10.3 데이터 품질
- 일부 PDF가 스캔 이미지일 수 있음 (OCR 필요 가능성)
- 파일 크기가 비정상적으로 크거나 작은 경우 필터링 고려
