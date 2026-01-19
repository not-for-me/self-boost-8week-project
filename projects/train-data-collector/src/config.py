"""Configuration constants for the train-data-collector."""

# URLs
BASE_URL = "https://finance.naver.com/research/company_list.naver"

# HTTP Headers
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}

# Rate Limiting
DEFAULT_DELAY_RANGE = (5.0, 10.0)  # seconds
MAX_RETRIES = 3
RETRY_BACKOFF = 2.0  # exponential backoff multiplier
REQUEST_TIMEOUT = 30.0  # seconds

# Collection Targets
DEFAULT_TOTAL_TARGET = 500
DEFAULT_MIN_BROKERS = 8
DEFAULT_MIN_PER_BROKER = 5
