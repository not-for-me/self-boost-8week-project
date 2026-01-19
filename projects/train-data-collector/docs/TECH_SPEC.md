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
│   ├── metadata.py         # 메타데이터 관리 및 중복 제거
│   └── config.py           # 설정 상수
├── tests/
│   ├── __init__.py
│   ├── test_parser.py
│   ├── test_downloader.py
│   ├── test_scraper.py
│   └── test_metadata.py
├── docs/
│   └── TECH_SPEC.md
├── main.py                 # 실행 진입점
└── pyproject.toml
```

### 2.1 데이터 저장 구조

```
projects/
├── train-data-collector/   # 프로젝트 폴더
└── data/                   # 데이터 저장 폴더 (프로젝트 상위)
    ├── metadata.json       # 수집된 리포트 메타데이터
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
@dataclass
class DownloadResult:
    """다운로드 결과."""
    success: bool
    path: Path | None = None
    file_hash: str | None = None
    skipped_reason: str | None = None

class PDFDownloader:
    def __init__(
        self,
        base_dir: Path,
        delay_range: tuple[float, float] = (5.0, 10.0),
        metadata_manager: MetadataManager | None = None,
    ):
        ...

    def download(self, report: ReportInfo) -> DownloadResult:
        """
        PDF 다운로드 후 결과 반환.
        - 성공 시: success=True, path 및 file_hash 포함
        - 실패 시: success=False, skipped_reason 포함
        - 중복 컨텐츠: success=False, skipped_reason="duplicate_content:..."
        """
        ...

    def _generate_filename(self, report: ReportInfo, existing_files: list[str]) -> str:
        """
        파일명 생성: {date}_{seq}.pdf
        기존 파일의 최대 seq를 찾아 다음 번호 사용.
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
    total_downloaded: int = 0
    by_broker: dict[str, int] = field(default_factory=dict)
    failed: int = 0
    skipped_url_duplicate: int = 0      # URL 중복으로 스킵
    skipped_content_duplicate: int = 0  # 컨텐츠 중복으로 스킵

    @property
    def total_skipped(self) -> int:
        """총 스킵 수"""
        return self.skipped_url_duplicate + self.skipped_content_duplicate

class ReportScraper:
    def __init__(self, config: CollectionConfig, data_dir: Path):
        ...

    def run(self) -> CollectionStats:
        """전체 수집 프로세스 실행 (기존 메타데이터 기반 effective target 계산)"""
        ...

    def _fetch_page(self, page: int) -> str:
        """페이지 HTML 가져오기"""
        ...

    def _should_stop(self, stats: CollectionStats, target: int) -> bool:
        """수집 중단 여부 판단"""
        ...

    def _save_metadata_checkpoint(self) -> None:
        """메타데이터 체크포인트 저장 (10개마다)"""
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

### 3.5 Metadata (`src/metadata.py`)

메타데이터 관리 및 중복 제거를 담당한다.

#### 중복 제거 전략
1. **URL 중복 검사** (다운로드 전): 이미 수집된 PDF URL은 스킵
2. **컨텐츠 중복 검사** (다운로드 후): MD5 해시가 동일한 파일은 스킵

#### 인터페이스
```python
@dataclass
class ReportMetadata:
    """다운로드된 리포트 메타데이터."""
    pdf_url: str
    broker: str
    stock_name: str
    title: str
    date: str           # yyyy-mm-dd 포맷
    local_path: str     # 상대 경로 (예: "한화투자증권/2026-01-19_01.pdf")
    file_hash: str      # 포맷: "md5:{hash}"
    downloaded_at: str  # ISO 포맷 타임스탬프

@dataclass
class MetadataStore:
    """메타데이터 저장소."""
    reports: dict[str, ReportMetadata]  # pdf_url -> metadata
    hashes: dict[str, str]              # file_hash -> pdf_url

class MetadataManager:
    def __init__(self, data_dir: Path):
        ...

    def is_duplicate_url(self, pdf_url: str) -> bool:
        """URL이 이미 다운로드되었는지 확인"""
        ...

    def is_duplicate_hash(self, file_hash: str) -> bool:
        """동일한 컨텐츠가 이미 존재하는지 확인"""
        ...

    def add_report(self, pdf_url: str, broker: str, ..., file_hash: str) -> ReportMetadata:
        """새 리포트 메타데이터 추가"""
        ...

    def get_existing_report_by_hash(self, file_hash: str) -> ReportMetadata | None:
        """해시로 기존 리포트 조회"""
        ...

    def save(self) -> None:
        """메타데이터를 metadata.json에 저장"""
        ...

    def get_total_count(self) -> int:
        """총 다운로드된 리포트 수"""
        ...

    def get_stats(self) -> dict[str, int]:
        """증권사별 리포트 수 통계"""
        ...

def calculate_file_hash(content: bytes) -> str:
    """파일 컨텐츠의 MD5 해시 계산. 반환 포맷: 'md5:{hash}'"""
    ...
```

#### metadata.json 구조
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

## 4. 데이터 흐름

```
┌─────────────────┐
│  main.py        │
│  (entrypoint)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Scraper        │◄──────────┐
│                 │           │
└────────┬────────┘           │
         │                    │
    ┌────┼────┐               │
    ▼    │    ▼               │
┌───────┐│ ┌──────────┐  ┌────────────┐
│Parser ││ │Downloader│──│  Metadata  │
│       ││ │          │  │  Manager   │
└───────┘│ └──────────┘  └────────────┘
    │    │       │              │
    ▼    │       ▼              ▼
[리포트  │  [PDF 저장]    [metadata.json]
 목록]   │       │
         │       ▼
         │  ../data/{증권사}/
         │  {date}_{seq}.pdf
         │
         └──[URL 중복 검사]
```

### 4.1 중복 제거 흐름

```
1. 페이지 스캔 시:
   리포트 발견 → MetadataManager.is_duplicate_url() → 중복이면 스킵

2. 다운로드 시:
   PDF 다운로드 → calculate_file_hash() → MetadataManager.is_duplicate_hash()
   → 중복이면 파일 저장하지 않고 스킵
   → 신규면 파일 저장 + 메타데이터 추가

3. 체크포인트:
   10개 다운로드마다 metadata.json 저장 (중단 시 복구 가능)
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
[INFO] 기존 메타데이터 로드: 100개 리포트
[INFO] 수집 시작: 목표 500개 (기존 100개, 추가 400개 필요), 최소 8개 증권사
[INFO] 페이지 1 스캔 완료: 15개 증권사 발견
[INFO] [10/400] 증권사 8개, 실패 0개, 스킵 2개
[INFO] [20/400] 증권사 10개, 실패 1개, 스킵 5개
...
[INFO] ==================================================
[INFO] 수집 완료
[INFO] ==================================================
[INFO] 총 다운로드: 400개
[INFO] 실패: 3개
[INFO] 스킵: 12개 (URL 중복: 8, 내용 중복: 4)
[INFO] 증권사별 현황 (12개):
[INFO]   - 삼성증권: 45개
[INFO]   - 미래에셋증권: 42개
[INFO]   - ...
[INFO] 총 보유 리포트: 500개
[INFO] 메타데이터 저장 완료
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

def test_should_stop_at_target():
    """Given: 목표 도달, When: 체크, Then: True 반환"""

def test_skips_duplicate_urls():
    """Given: 이미 다운로드된 URL, When: 다운로드 시도, Then: 스킵"""
```

### 7.4 Metadata 테스트 (`tests/test_metadata.py`)

```python
def test_add_report_stores_by_url_and_hash():
    """Given: 리포트 메타데이터, When: 추가, Then: URL과 해시로 조회 가능"""

def test_is_duplicate_url_detects_duplicates():
    """Given: 기존 URL, When: 중복 검사, Then: True 반환"""

def test_is_duplicate_hash_detects_duplicates():
    """Given: 기존 해시, When: 중복 검사, Then: True 반환"""

def test_save_creates_metadata_file():
    """Given: 메타데이터, When: 저장, Then: JSON 파일 생성"""

def test_loads_existing_metadata():
    """Given: 기존 메타데이터 파일, When: 초기화, Then: 데이터 로드"""

def test_calculate_file_hash_returns_md5_format():
    """Given: 바이트 컨텐츠, When: 해시 계산, Then: 'md5:...' 포맷"""
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
