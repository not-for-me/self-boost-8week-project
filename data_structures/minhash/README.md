# MinHash & LSH (Locality-Sensitive Hashing)

> 대규모 데이터에서 유사한 문서를 효율적으로 찾는 확률적 알고리즘

---

## 1. 개념

### 문제: Near-Duplicate Detection

LLM 학습 데이터에서 **거의 비슷한 문서**를 찾아야 합니다.

```
예: 다음 두 문서는 "중복"인가?
- "오늘 날씨가 맑습니다. 기온은 25도입니다."
- "오늘 날씨가 맑습니다. 기온은 26도입니다."

→ 완전 동일은 아니지만 "Near-duplicate"로 처리해야 할 수 있음
```

### Naive 접근의 문제

```
N개 문서 쌍 비교 = N × (N-1) / 2

N = 10억 문서
→ 5 × 10^17 비교 필요 (불가능!)
```

### 해결책: MinHash + LSH

1. **MinHash**: 문서를 고정 크기 signature로 압축 (Jaccard 유사도 보존)
2. **LSH**: 유사한 signature끼리 같은 bucket에 모음 (후보 쌍만 비교)

---

## 2. Jaccard Similarity (자카드 유사도)

두 집합의 유사도를 측정하는 지표:

```
J(A, B) = |A ∩ B| / |A ∪ B|
```

### 예시

```python
A = {"오늘", "날씨", "맑음", "기온", "25도"}
B = {"오늘", "날씨", "맑음", "기온", "26도"}

교집합 = {"오늘", "날씨", "맑음", "기온"}  # 4개
합집합 = {"오늘", "날씨", "맑음", "기온", "25도", "26도"}  # 6개

J(A, B) = 4/6 ≈ 0.67
```

### 문서에서의 적용: Shingling

문서를 n-gram(shingle) 집합으로 변환:

```python
text = "오늘 날씨가 맑습니다"

# 2-gram (character level)
shingles = {"오늘", "늘 ", " 날", "날씨", "씨가", "가 ", " 맑", "맑습", "습니", "니다"}

# 3-gram (word level)
words = text.split()  # ["오늘", "날씨가", "맑습니다"]
shingles = {("오늘", "날씨가", "맑습니다")}  # 단어 3-gram
```

---

## 3. MinHash 알고리즘

### 핵심 아이디어

**정리**: 랜덤 순열에서 두 집합의 최소 해시값이 같을 확률 = Jaccard 유사도

```
P(min_hash(A) == min_hash(B)) = J(A, B)
```

### 동작 원리

1. **여러 개의 해시 함수** (h1, h2, ..., hk) 준비
2. 각 해시 함수에 대해 집합 원소들의 **최소 해시값** 계산
3. k개의 최소값 = **MinHash Signature** (고정 크기 벡터)

```
집합 A = {a, b, c}
집합 B = {b, c, d}

h1: h1(a)=3, h1(b)=1, h1(c)=5, h1(d)=2
h2: h2(a)=1, h2(b)=4, h2(c)=2, h2(d)=3

MinHash_h1(A) = min(3, 1, 5) = 1
MinHash_h1(B) = min(1, 5, 2) = 1  ✓ 같음

MinHash_h2(A) = min(1, 4, 2) = 1
MinHash_h2(B) = min(4, 2, 3) = 2  ✗ 다름

Signature(A) = [1, 1]
Signature(B) = [1, 2]

추정 유사도 = 같은 비율 = 1/2 = 0.5
실제 유사도 = |{b,c}| / |{a,b,c,d}| = 2/4 = 0.5 ✓
```

### Signature 크기와 정확도

```
k = signature 크기 (해시 함수 개수)

추정 오차의 표준편차 ≈ 1/√k

예:
k = 100 → 오차 ~10%
k = 400 → 오차 ~5%
```

---

## 4. LSH (Locality-Sensitive Hashing)

### 문제

MinHash signature가 있어도, 모든 쌍을 비교하면 여전히 O(N²)

### 해결: Banding Technique

Signature를 **b개의 band**로 나누고, 각 band에서 해시가 같으면 **후보 쌍**으로 선정

```
Signature (k=12): [3, 5, 2, 8, 1, 4, 7, 9, 0, 6, 2, 8]

b=4 bands, r=3 rows per band:

Band 1: [3, 5, 2]  → hash("3,5,2") → bucket A
Band 2: [8, 1, 4]  → hash("8,1,4") → bucket B
Band 3: [7, 9, 0]  → hash("7,9,0") → bucket C
Band 4: [6, 2, 8]  → hash("6,2,8") → bucket D

같은 bucket에 들어간 문서 쌍만 비교!
```

### 확률 분석

두 문서의 Jaccard 유사도가 s일 때, 후보 쌍으로 선정될 확률:

```
P(후보) = 1 - (1 - s^r)^b

r = rows per band
b = number of bands
```

### S-Curve 특성

```
b=20, r=5 (signature 크기 = 100)

s=0.2 → P ≈ 0.006 (거의 무시)
s=0.5 → P ≈ 0.47
s=0.8 → P ≈ 0.9996 (거의 확실)

"threshold" ≈ (1/b)^(1/r) ≈ 0.55
```

유사도가 threshold 근처에서 급격히 변하는 S-curve 형성

---

## 5. 구현

### MinHash 기본 구현

```python
import hashlib
from typing import Set, List

class MinHash:
    """
    MinHash Signature 생성기

    Parameters:
        num_perm: 순열(해시 함수) 개수 = signature 크기
    """

    def __init__(self, num_perm: int = 128):
        self.num_perm = num_perm
        self._init_hash_params()

    def _init_hash_params(self):
        """해시 함수 파라미터 초기화 (ax + b mod p)"""
        import random
        random.seed(42)  # 재현성을 위해 고정

        # 큰 소수
        self._prime = (1 << 61) - 1

        # 랜덤 a, b 생성
        self._a = [random.randint(1, self._prime - 1)
                   for _ in range(self.num_perm)]
        self._b = [random.randint(0, self._prime - 1)
                   for _ in range(self.num_perm)]

    def _hash(self, value: int, i: int) -> int:
        """i번째 해시 함수"""
        return (self._a[i] * value + self._b[i]) % self._prime

    def signature(self, shingles: Set[str]) -> List[int]:
        """
        집합에서 MinHash signature 생성

        Args:
            shingles: 문서의 shingle 집합

        Returns:
            길이 num_perm의 signature
        """
        if not shingles:
            return [0] * self.num_perm

        # 각 shingle을 정수로 변환
        hashed_shingles = [
            int(hashlib.md5(s.encode()).hexdigest(), 16)
            for s in shingles
        ]

        # 각 해시 함수에 대해 최소값 계산
        sig = []
        for i in range(self.num_perm):
            min_hash = min(self._hash(h, i) for h in hashed_shingles)
            sig.append(min_hash)

        return sig

    @staticmethod
    def similarity(sig1: List[int], sig2: List[int]) -> float:
        """두 signature 간 추정 Jaccard 유사도"""
        if len(sig1) != len(sig2):
            raise ValueError("Signatures must have same length")

        matches = sum(1 for a, b in zip(sig1, sig2) if a == b)
        return matches / len(sig1)
```

### LSH Index 구현

```python
from collections import defaultdict
from typing import Dict, List, Tuple

class LSHIndex:
    """
    LSH (Locality-Sensitive Hashing) 인덱스

    Parameters:
        num_perm: MinHash signature 크기
        num_bands: band 개수
    """

    def __init__(self, num_perm: int = 128, num_bands: int = 16):
        if num_perm % num_bands != 0:
            raise ValueError("num_perm must be divisible by num_bands")

        self.num_perm = num_perm
        self.num_bands = num_bands
        self.rows_per_band = num_perm // num_bands

        self.minhash = MinHash(num_perm)
        self.buckets: List[Dict[int, List[str]]] = [
            defaultdict(list) for _ in range(num_bands)
        ]
        self.signatures: Dict[str, List[int]] = {}

    def _band_hash(self, band: List[int]) -> int:
        """band를 단일 해시값으로 변환"""
        return hash(tuple(band))

    def add(self, doc_id: str, shingles: Set[str]) -> None:
        """문서를 인덱스에 추가"""
        sig = self.minhash.signature(shingles)
        self.signatures[doc_id] = sig

        # 각 band를 해당 bucket에 추가
        for b in range(self.num_bands):
            start = b * self.rows_per_band
            end = start + self.rows_per_band
            band = sig[start:end]
            band_hash = self._band_hash(band)
            self.buckets[b][band_hash].append(doc_id)

    def query(self, shingles: Set[str]) -> List[Tuple[str, float]]:
        """
        유사한 문서 후보 검색

        Returns:
            (doc_id, estimated_similarity) 리스트
        """
        sig = self.minhash.signature(shingles)
        candidates = set()

        # 각 band에서 후보 수집
        for b in range(self.num_bands):
            start = b * self.rows_per_band
            end = start + self.rows_per_band
            band = sig[start:end]
            band_hash = self._band_hash(band)

            for doc_id in self.buckets[b][band_hash]:
                candidates.add(doc_id)

        # 후보들과 유사도 계산
        results = []
        for doc_id in candidates:
            sim = MinHash.similarity(sig, self.signatures[doc_id])
            results.append((doc_id, sim))

        return sorted(results, key=lambda x: -x[1])

    def find_similar_pairs(self, threshold: float = 0.5) -> List[Tuple[str, str, float]]:
        """
        인덱스 내 유사한 문서 쌍 찾기

        Returns:
            (doc_id1, doc_id2, similarity) 리스트
        """
        # 후보 쌍 수집
        candidate_pairs = set()

        for b in range(self.num_bands):
            for bucket_docs in self.buckets[b].values():
                if len(bucket_docs) > 1:
                    for i in range(len(bucket_docs)):
                        for j in range(i + 1, len(bucket_docs)):
                            pair = tuple(sorted([bucket_docs[i], bucket_docs[j]]))
                            candidate_pairs.add(pair)

        # 유사도 계산 및 필터링
        results = []
        for doc1, doc2 in candidate_pairs:
            sim = MinHash.similarity(
                self.signatures[doc1],
                self.signatures[doc2]
            )
            if sim >= threshold:
                results.append((doc1, doc2, sim))

        return sorted(results, key=lambda x: -x[2])
```

---

## 6. 실전 활용

### 문서 중복 제거 파이프라인

```python
def create_shingles(text: str, k: int = 5) -> Set[str]:
    """텍스트에서 k-gram shingle 생성"""
    text = text.lower().strip()
    return {text[i:i+k] for i in range(len(text) - k + 1)}


def deduplicate_documents(documents: List[dict],
                          threshold: float = 0.8) -> List[dict]:
    """
    문서 중복 제거

    Args:
        documents: [{"id": ..., "content": ...}, ...]
        threshold: 유사도 임계값

    Returns:
        중복 제거된 문서 리스트
    """
    # LSH 인덱스 구축
    lsh = LSHIndex(num_perm=128, num_bands=16)

    for doc in documents:
        shingles = create_shingles(doc["content"])
        lsh.add(doc["id"], shingles)

    # 중복 쌍 찾기
    similar_pairs = lsh.find_similar_pairs(threshold)

    # Union-Find로 클러스터링
    clusters = {}  # doc_id -> cluster_id
    for doc in documents:
        clusters[doc["id"]] = doc["id"]

    def find(x):
        if clusters[x] != x:
            clusters[x] = find(clusters[x])
        return clusters[x]

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            clusters[px] = py

    for doc1, doc2, sim in similar_pairs:
        union(doc1, doc2)

    # 각 클러스터에서 대표 문서만 선택
    seen_clusters = set()
    unique_docs = []

    for doc in documents:
        cluster = find(doc["id"])
        if cluster not in seen_clusters:
            seen_clusters.add(cluster)
            unique_docs.append(doc)

    return unique_docs
```

### 실제 데이터 품질 관리

```python
class DocumentDeduplicator:
    """대규모 문서 중복 제거기"""

    def __init__(self, num_perm: int = 256, num_bands: int = 32,
                 threshold: float = 0.8):
        self.lsh = LSHIndex(num_perm, num_bands)
        self.threshold = threshold
        self.processed = 0
        self.duplicates = 0

    def is_duplicate(self, doc_id: str, content: str) -> bool:
        """
        새 문서가 기존 문서와 중복인지 확인

        True를 반환하면 해당 문서는 스킵해야 함
        """
        shingles = create_shingles(content)

        # 유사한 문서 검색
        candidates = self.lsh.query(shingles)

        for existing_id, sim in candidates:
            if sim >= self.threshold:
                self.duplicates += 1
                return True

        # 중복이 아니면 인덱스에 추가
        self.lsh.add(doc_id, shingles)
        self.processed += 1
        return False

    def stats(self) -> dict:
        return {
            "processed": self.processed,
            "duplicates_found": self.duplicates,
            "dedup_ratio": self.duplicates / max(1, self.processed + self.duplicates)
        }
```

---

## 7. 파라미터 튜닝

### Signature 크기 (num_perm)

```
클수록: 정확도 ↑, 메모리 ↑, 속도 ↓
작을수록: 정확도 ↓, 메모리 ↓, 속도 ↑

권장:
- 빠른 필터링: 64~128
- 높은 정확도: 256~512
```

### Band 설정 (num_bands, rows_per_band)

```python
def calculate_threshold(b: int, r: int) -> float:
    """대략적인 similarity threshold 계산"""
    return (1/b) ** (1/r)

# 예시
print(calculate_threshold(b=16, r=8))   # ~0.55
print(calculate_threshold(b=32, r=4))   # ~0.42
print(calculate_threshold(b=8, r=16))   # ~0.72
```

### 추천 설정

| 사용 사례 | num_perm | num_bands | threshold |
|----------|----------|-----------|-----------|
| 빠른 필터링 | 128 | 32 | ~0.4 |
| 균형 | 128 | 16 | ~0.55 |
| 높은 정밀도 | 256 | 16 | ~0.65 |

---

## 8. 주의사항

### 1. Shingle 크기 선택

```python
# 너무 작으면: 모든 문서가 유사해 보임
create_shingles("hello world", k=2)  # 작은 shingle

# 너무 크면: 약간의 차이도 다르게 인식
create_shingles("hello world", k=20)  # 큰 shingle

# 권장: 영문 5-10, 한글 3-5
```

### 2. 텍스트 전처리

```python
def preprocess_for_minhash(text: str) -> str:
    """MinHash 전 전처리"""
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)  # 연속 공백 제거
    text = re.sub(r'[^\w\s]', '', text)  # 특수문자 제거
    return text.strip()
```

### 3. False Positive/Negative 트레이드오프

- **False Positive**: 다른 문서를 같다고 판단 → threshold 높이기
- **False Negative**: 같은 문서를 다르다고 판단 → num_bands 늘리기

---

## 참고 자료

- [Mining of Massive Datasets - Ch.3 Finding Similar Items](http://www.mmds.org/)
- Paper: "Min-Wise Independent Permutations" (Broder et al., 1998)
- [datasketch 라이브러리](https://github.com/ekzhu/datasketch)
- [Deduplicating Training Data Makes Language Models Better](https://arxiv.org/abs/2107.06499)
