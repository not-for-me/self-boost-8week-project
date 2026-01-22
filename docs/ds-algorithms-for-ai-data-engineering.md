# AI/LLM 데이터 엔지니어링을 위한 자료구조 및 알고리즘

> 백엔드/데이터 엔지니어링 경험자가 AI/LLM 데이터 파이프라인으로 전환할 때 필요한 핵심 자료구조와 알고리즘 정리

---

## 🔴 꼭 알아야 할 것 (Must-Know)

### 1. Hash Tables & Bloom Filters — 대규모 중복 제거

**왜 중요한가:** LLM 학습 데이터는 수십억 개의 문서를 다루는데, 중복 데이터는 모델 품질을 심각하게 저하시킨다. 전체 데이터를 메모리에 올릴 수 없으므로 확률적 자료구조가 필수.

**실제 용례:**
- **Exact deduplication**: MinHash + LSH(Locality-Sensitive Hashing)로 유사 문서 클러스터링
- **Near-duplicate detection**: SimHash로 문서 fingerprint 생성 후 hamming distance 비교
- **URL/문서 ID 중복 체크**: Bloom filter로 메모리 효율적인 membership test (C4 데이터셋 구축 시 실제 사용)

**메모리 효율 비교:**
```
10억 개 URL 중복 체크
- Hash set: ~40GB 메모리
- Bloom filter (1% FPR): ~1.2GB 메모리
```

**학습 리소스:**
- [ ] Bloom Filter 구현 및 False Positive Rate 분석
- [ ] MinHash 알고리즘과 Jaccard Similarity
- [ ] LSH (Locality-Sensitive Hashing) 이해

---

### 2. Trie & Suffix Arrays — 토크나이저 구현

**왜 중요한가:** BPE, WordPiece, Unigram 등 모든 서브워드 토크나이저의 핵심 자료구조. 한국어 처리 시 토크나이저 커스터마이징에 필수.

**실제 용례:**
- **BPE 학습**: 가장 빈번한 바이트 쌍을 찾기 위해 suffix array로 효율적인 substring 빈도 계산
- **토큰 매칭**: Trie로 longest prefix match 수행 (HuggingFace tokenizers 내부 구현)
- **vocabulary 구축**: 한국어 형태소 + 서브워드 하이브리드 토크나이저 설계

**WordPiece 토크나이징 의사코드:**
```python
def tokenize(word, vocab_trie):
    tokens = []
    while word:
        # Trie에서 가장 긴 매칭 prefix 찾기
        longest = vocab_trie.longest_prefix(word)
        tokens.append(longest)
        word = word[len(longest):]
    return tokens
```

**학습 리소스:**
- [ ] Trie 기본 구현 (insert, search, prefix match)
- [ ] Suffix Array 구축 알고리즘
- [ ] BPE/WordPiece에서의 실제 활용

---

### 3. Heap (Priority Queue) — 샘플링 & Top-K

**왜 중요한가:** 데이터 품질 필터링, 모델 출력의 top-k 샘플링, 스트리밍 데이터에서 상위 N개 추출 등 어디서나 사용.

**실제 용례:**
- **Reservoir sampling with priority**: 품질 점수 기반으로 대규모 데이터에서 대표 샘플 추출
- **Beam search 구현**: 번역/생성 모델의 디코딩 (각 스텝에서 top-k 후보 유지)
- **데이터 품질 상위 N% 필터링**: perplexity 기준 정렬 없이 streaming으로 처리

**학습 리소스:**
- [ ] Min-heap / Max-heap 구현
- [ ] Streaming Top-K 알고리즘
- [ ] Weighted Reservoir Sampling

---

### 4. Inverted Index — 검색 & RAG 파이프라인

**왜 중요한가:** RAG(Retrieval-Augmented Generation) 시스템의 sparse retrieval 구성 요소. BM25 같은 전통적 검색이 vector search와 함께 hybrid로 많이 사용됨.

**실제 용례:**
- **BM25 구현**: token → document_ids 매핑으로 빠른 키워드 검색
- **Negative sampling**: 학습 데이터의 hard negative 구축 시 효율적인 후보 검색
- **메타데이터 필터링**: 문서 속성(날짜, 출처, 언어) 기반 필터와 결합

**학습 리소스:**
- [ ] Inverted Index 기본 구조
- [ ] TF-IDF와 BM25 구현
- [ ] Posting list compression 기법

---

## 🟡 알아두면 좋은 것 (Nice-to-Have)

### 5. Graph Algorithms (BFS/DFS, PageRank) — 데이터 품질 & 지식 그래프

**왜 중요한가:** 웹 크롤링 데이터의 품질 평가, knowledge graph 구축, 데이터 계보(lineage) 추적에 사용.

**실제 용례:**
- **도메인 품질 점수**: PageRank 변형으로 신뢰할 수 있는 출처 식별 (Common Crawl 필터링)
- **Knowledge graph traversal**: entity 관계 추출 후 multi-hop reasoning 데이터 생성
- **데이터 의존성 DAG**: Airflow 같은 파이프라인에서 태스크 스케줄링

**학습 리소스:**
- [ ] BFS/DFS 복습 및 그래프 표현
- [ ] PageRank 알고리즘 이해
- [ ] Topological Sort (DAG 스케줄링)

---

### 6. Tree Structures (B-Tree, KD-Tree, Ball Tree) — 벡터 검색 인덱싱

**왜 중요한가:** 임베딩 벡터 검색의 근간. FAISS, Annoy 같은 라이브러리가 내부적으로 사용.

**실제 용례:**
- **ANN(Approximate Nearest Neighbor)**: KD-Tree 기반 검색 (저차원), Ball Tree (고차원)
- **HNSW 이해**: hierarchical navigable small world graph는 tree 아이디어의 확장
- **클러스터링**: K-means의 효율적 구현에 tree 기반 가속

**학습 리소스:**
- [ ] KD-Tree 구축 및 검색
- [ ] Ball Tree와 고차원 데이터
- [ ] HNSW 논문 읽기

---

### 7. Dynamic Programming — 시퀀스 정렬 & 평가 메트릭

**왜 중요한가:** 텍스트 유사도 측정, 데이터 증강, 평가 메트릭 계산에서 핵심.

**실제 용례:**
- **Edit distance**: 오타 보정, 데이터 정제 시 유사 문자열 클러스터링
- **LCS(Longest Common Subsequence)**: ROUGE 점수 계산의 기반
- **Sequence alignment**: 번역 데이터의 문장 정렬

**학습 리소스:**
- [ ] Edit Distance (Levenshtein) 구현
- [ ] LCS 알고리즘
- [ ] ROUGE 메트릭 계산 로직

---

### 8. Disjoint Set (Union-Find) — 대규모 클러스터링

**왜 중요한가:** 수십억 개 문서의 near-duplicate 클러스터를 효율적으로 병합할 때 필수.

**실제 용례:**
- **문서 클러스터 병합**: MinHash로 유사 쌍 찾은 후, Union-Find로 transitive closure 계산
- **Entity resolution**: 같은 entity를 가리키는 다른 mention들을 하나로 통합

**학습 리소스:**
- [ ] Union-Find with path compression
- [ ] Rank-based union 최적화
- [ ] 대규모 클러스터링 적용 사례

---

## 🟢 상황에 따라 (Context-Dependent)

### 9. Sorting & External Sort — 대규모 데이터 전처리

TB 단위 텍스트 정렬은 여전히 도전적. Shuffle 단계나 데이터 샤딩에서 중요.

**학습 리소스:**
- [ ] External merge sort
- [ ] Distributed sorting (MapReduce 패턴)

---

### 10. Compression (Huffman, LZ77) — 효율적 저장

토크나이저의 vocabulary가 본질적으로 compression과 연결. 대규모 코퍼스 저장 시 비용 절감에 직결.

**학습 리소스:**
- [ ] Huffman coding 이해
- [ ] BPE와 compression의 관계

---

### 11. Streaming Algorithms (Count-Min Sketch, HyperLogLog)

**실제 용례:**
- **토큰 빈도 추정**: 전체 코퍼스를 메모리에 올리지 않고 단어 빈도 계산
- **Cardinality estimation**: unique token 수 추정

**학습 리소스:**
- [ ] Count-Min Sketch 구현
- [ ] HyperLogLog 원리

---

## 📋 학습 우선순위 (Document AI + 재무 데이터 기준)

| 순서 | 주제 | 이유 | 상태 |
|------|------|------|------|
| 1 | Trie + Suffix Array | 한국어 토크나이저 커스터마이징에 직접 필요 | ⬜ |
| 2 | Bloom Filter + MinHash | PDF 중복 제거, 데이터 품질 관리의 기본 | ⬜ |
| 3 | Inverted Index | RAG 파이프라인 구축 시 sparse retrieval | ⬜ |
| 4 | Heap + Reservoir Sampling | 품질 기반 데이터 샘플링 | ⬜ |
| 5 | DP (Edit Distance) | 테이블 셀 매칭, OCR 후처리 | ⬜ |

---

## 참고 자료

### 논문
- "Deduplicating Training Data Makes Language Models Better" (Lee et al., 2022)
- "The RefinedWeb Dataset for Falcon LLM" (Penedo et al., 2023)
- "BPE-Dropout: Simple and Effective Subword Regularization" (Provilkov et al., 2020)

### 도서
- Introduction to Algorithms (CLRS) - 기본 자료구조 복습
- Mining of Massive Datasets (Leskovec et al.) - LSH, Streaming 알고리즘
- Speech and Language Processing (Jurafsky & Martin) - NLP 관점의 알고리즘

### 실습 자료
- HuggingFace tokenizers 라이브러리 소스 코드
- FAISS 라이브러리 문서 및 튜토리얼
- datasketch 라이브러리 (MinHash, LSH 구현)
