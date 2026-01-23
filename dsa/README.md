# Data Structures & Algorithms for AI/ML Engineering

> AI/LLM 데이터 파이프라인 구축에 필요한 핵심 자료구조와 알고리즘 학습 자료

---

## 학습 현황

| 주제 | 설명 | 상태 | 자료 |
|------|------|:----:|------|
| [Trie](./trie/) | 토크나이저의 longest prefix match | ✅ | [README](./trie/README.md) |
| [Suffix Array](./suffix_array/) | 효율적인 substring 빈도 계산 | ✅ | [README](./suffix_array/README.md) |
| [Bloom Filter](./bloom_filter/) | 메모리 효율적 중복 체크 | ✅ | [README](./bloom_filter/README.md) |
| [MinHash](./minhash/) | 문서 유사도 및 near-duplicate 탐지 | ✅ | [README](./minhash/README.md) |
| Heap / Priority Queue | Top-K 샘플링, Beam Search | ⬜ | - |
| Inverted Index | RAG의 sparse retrieval (BM25) | ⬜ | - |
| Union-Find | 대규모 클러스터 병합 | ⬜ | - |
| LSH | Locality-Sensitive Hashing | ⬜ | - |

---

## 개요

이 디렉토리는 AI/ML 데이터 엔지니어링에서 자주 사용되는 자료구조와 알고리즘을 직접 구현하고 학습한 내용을 정리합니다.

### 왜 이 자료구조들이 중요한가?

1. **대규모 데이터 처리**: LLM 학습 데이터는 수십억 개의 문서를 다루므로 메모리 효율적인 자료구조가 필수
2. **토크나이저 이해**: BPE, WordPiece 등 서브워드 토크나이저의 내부 동작 원리 파악
3. **RAG 파이프라인**: 검색 증강 생성 시스템의 retrieval 컴포넌트 구현
4. **데이터 품질 관리**: 중복 제거, 유사 문서 탐지, 품질 필터링

---

## 학습 로드맵

### Phase 1: 토크나이저 기초 (Tokenizer Fundamentals)

서브워드 토크나이징의 핵심 자료구조

| 자료구조 | 용도 | 실제 사례 |
|----------|------|-----------|
| **Trie** | Longest prefix match | HuggingFace tokenizers 내부 구현 |
| **Suffix Array** | Substring 빈도 계산 | BPE 학습 시 바이트 쌍 빈도 측정 |

### Phase 2: 중복 제거 (Deduplication)

대규모 코퍼스의 중복 데이터 탐지 및 제거

| 자료구조 | 용도 | 실제 사례 |
|----------|------|-----------|
| **Bloom Filter** | Exact deduplication | C4 데이터셋 URL 중복 체크 |
| **MinHash** | Near-duplicate detection | 유사 문서 클러스터링 |
| **LSH** | 유사 문서 빠른 검색 | MinHash와 함께 사용 |
| **Union-Find** | 클러스터 병합 | Transitive closure 계산 |

### Phase 3: 검색 & 샘플링 (Retrieval & Sampling)

RAG 파이프라인 및 데이터 샘플링

| 자료구조 | 용도 | 실제 사례 |
|----------|------|-----------|
| **Inverted Index** | Sparse retrieval | BM25 기반 키워드 검색 |
| **Heap** | Top-K 추출 | Beam search, 품질 기반 필터링 |
| **Reservoir Sampling** | 스트리밍 샘플링 | 대규모 데이터 대표 샘플 추출 |

### Phase 4: 고급 주제 (Advanced Topics)

상황에 따라 필요한 알고리즘

| 알고리즘 | 용도 | 실제 사례 |
|----------|------|-----------|
| **Edit Distance** | 텍스트 유사도 | OCR 후처리, 오타 보정 |
| **LCS** | 시퀀스 정렬 | ROUGE 점수 계산 |
| **PageRank** | 품질 점수 | 웹 크롤링 데이터 필터링 |
| **Count-Min Sketch** | 빈도 추정 | 스트리밍 토큰 빈도 계산 |

---

## 메모리 효율 비교

실제 대규모 시스템에서의 메모리 사용량 비교

```
10억 개 URL 중복 체크:
├── Hash Set:           ~40GB 메모리
├── Bloom Filter (1%):  ~1.2GB 메모리
└── 절감율:             ~97%

10억 개 문서 유사도 비교:
├── 모든 쌍 비교:       O(n²) = 불가능
├── MinHash + LSH:      O(n) 근사
└── 비교 횟수 절감:     99.9%+
```

---

## 디렉토리 구조

```
dsa/
├── README.md              # 이 파일
├── bloom_filter/          # Bloom Filter 구현 및 학습 노트
│   ├── README.md
│   └── bloom_filter.py
├── minhash/               # MinHash 구현 및 학습 노트
│   ├── README.md
│   └── minhash.py
├── suffix_array/          # Suffix Array 구현 및 학습 노트
│   ├── README.md
│   └── suffix_array.py
├── trie/                  # Trie 구현 및 학습 노트
│   ├── README.md
│   └── trie.py
└── [future topics]/       # 추가 예정
```

각 폴더에는:
- `README.md`: 개념 설명, 시간/공간 복잡도, 실제 활용 사례
- `*.py`: Python 구현 코드

---

## 참고 자료

### 논문
- "Deduplicating Training Data Makes Language Models Better" (Lee et al., 2022)
- "The RefinedWeb Dataset for Falcon LLM" (Penedo et al., 2023)
- "BPE-Dropout: Simple and Effective Subword Regularization" (Provilkov et al., 2020)

### 도서
- Introduction to Algorithms (CLRS)
- Mining of Massive Datasets (Leskovec et al.) - LSH, Streaming 알고리즘
- Speech and Language Processing (Jurafsky & Martin) - NLP 관점

### 라이브러리
- [HuggingFace tokenizers](https://github.com/huggingface/tokenizers) - 토크나이저 구현
- [datasketch](https://github.com/ekzhu/datasketch) - MinHash, LSH
- [FAISS](https://github.com/facebookresearch/faiss) - 벡터 검색
