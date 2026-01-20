"""Constants for financial table classification.

Financial statement patterns and temporal regex patterns used for
classifying tables as financial statements.
"""

# Financial statement keyword patterns for each category
FINANCIAL_STATEMENT_PATTERNS: dict[str, dict] = {
    # 손익계산서 (Income Statement)
    "income_statement": {
        "keywords": [
            "매출액",
            "매출원가",
            "매출총이익",
            "영업이익",
            "영업외손익",
            "세전이익",
            "법인세",
            "당기순이익",
            "지배주주순이익",
            "순이익",
        ],
        "weight": 1.0,
        "min_matches": 2,
    },
    # 재무상태표 (Balance Sheet)
    "balance_sheet": {
        "keywords": [
            "자산총계",
            "부채총계",
            "자본총계",
            "유동자산",
            "비유동자산",
            "유동부채",
            "비유동부채",
            "이익잉여금",
            "자본금",
        ],
        "weight": 1.0,
        "min_matches": 2,
    },
    # 현금흐름표 (Cash Flow)
    "cash_flow": {
        "keywords": [
            "영업활동",
            "투자활동",
            "재무활동",
            "현금흐름",
            "현금증감",
            "FCF",
            "CAPEX",
        ],
        "weight": 1.0,
        "min_matches": 2,
    },
    # 투자지표 (Valuation Metrics)
    "valuation": {
        "keywords": [
            "EPS",
            "BPS",
            "PER",
            "PBR",
            "ROE",
            "ROA",
            "EBITDA",
            "EV/EBITDA",
            "배당수익률",
            "DPS",
        ],
        "weight": 0.8,  # 단독으로는 재무제표가 아닐 수 있음
        "min_matches": 3,
    },
    # 실적 추이 (Performance Trend) - 보조 지표
    "performance": {
        "keywords": [
            "YoY",
            "QoQ",
            "전년비",
            "성장률",
            "증감률",
            "전분기비",
        ],
        "weight": 0.5,
        "min_matches": 2,
    },
}

# Temporal patterns for detecting year/quarter columns
TEMPORAL_PATTERNS: list[str] = [
    r"20\d{2}[EFef]?",  # 2024, 2025E, 2025F, 2025e
    r"[1-4][Qq]\d{2}",  # 1Q24, 3Q25, 1q24
    r"\d{1,2}[분반]기",  # 1분기, 2분기, 상반기
    r"FY\d{2,4}",  # FY24, FY2024
    r"\d{4}년",  # 2024년
]
