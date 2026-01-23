# Bloom Filter

> 확률적 자료구조로 대규모 데이터의 멤버십 테스트를 메모리 효율적으로 수행

---

## 1. 개념

**Bloom Filter**는 어떤 원소가 집합에 **"확실히 없다"** 또는 **"아마 있다"**를 판단하는 확률적 자료구조입니다.

### 핵심 특성


| 특성 | 설명 |
|------|------|
| **False Positive** | "있다"고 했는데 실제로 없을 수 있음 (확률 조절 가능) |
| **False Negative** | **절대 없음** - "없다"고 하면 확실히 없음 |
| **메모리 효율** | 실제 데이터 저장 없이 비트 배열만 사용 |
| **삭제 불가** | 기본 Bloom Filter는 원소 삭제 불가 |



| 예측 | 실제 있음 | 실제 없음 |
|------|----------|----------|
| "있다" | ✓ True Positive | ⚠️ False Positive (가능) |
| "없다" | ❌ False Negative (**불가능**) | ✓ True Negative |



### 왜 LLM 데이터 엔지니어링에 중요한가?

```
10억 개 URL 중복 체크 비교:
- Hash Set: ~40GB 메모리 (URL당 ~40바이트)
- Bloom Filter (1% FPR): ~1.2GB 메모리 (원소당 ~10비트)
```

**실제 사용 사례:**
- **C4 데이터셋**: 웹 크롤링 시 이미 처리한 URL 중복 체크
- **RefinedWeb**: 문서 fingerprint 중복 탐지
- **데이터 파이프라인**: 스트리밍 환경에서 seen/unseen 판단

---

## 2. 동작 원리

### 구조

```
Bloom Filter = 비트 배열 (m bits) + k개의 해시 함수

┌─────────────────────────────────────────────────┐
│ 0 │ 0 │ 1 │ 0 │ 1 │ 0 │ 0 │ 1 │ 0 │ 0 │ 1 │ 0 │
└─────────────────────────────────────────────────┘
  0   1   2   3   4   5   6   7   8   9  10  11

m = 12 (비트 배열 크기)
k = 3 (해시 함수 개수)
```

### 삽입 (Add)

원소 `x`를 삽입할 때:
1. k개의 해시 함수로 k개의 위치 계산: `h1(x), h2(x), ..., hk(x)`
2. 해당 위치의 비트를 모두 1로 설정

```python
def add(self, item):
    for seed in range(self.num_hashes):
        index = hash(item, seed) % self.size
        self.bit_array[index] = 1
```

**예시: "apple" 삽입 (k=3)**
```
h1("apple") = 2
h2("apple") = 4
h3("apple") = 7

Before: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
After:  [0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 0, 0]
              ↑     ↑        ↑
```

### 조회 (Contains)

원소 `x`가 있는지 확인할 때:
1. k개의 해시 함수로 k개의 위치 계산
2. **모든** 위치의 비트가 1이면 → "아마 있다" (Maybe)
3. **하나라도** 0이면 → "확실히 없다" (Definitely No)

```python
def contains(self, item):
    for seed in range(self.num_hashes):
        index = hash(item, seed) % self.size
        if self.bit_array[index] == 0:
            return False  # 확실히 없음
    return True  # 아마 있음 (False Positive 가능)
```

### False Positive가 발생하는 이유

```
"apple" 삽입 → 위치 2, 4, 7 = 1
"banana" 삽입 → 위치 4, 7, 10 = 1

현재 상태: [0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0]

"cherry" 조회 → h1=2, h2=4, h3=10
모든 위치가 1 → "있다"고 응답 (하지만 실제로 없음 = False Positive)
```

---

## 3. 수학적 분석

### False Positive Rate (FPR)

```
FPR ≈ (1 - e^(-kn/m))^k

n = 삽입된 원소 수
m = 비트 배열 크기
k = 해시 함수 개수
```

### 최적의 해시 함수 개수

주어진 `m`과 `n`에서 FPR을 최소화하는 `k`:

```
k_optimal = (m/n) × ln(2) ≈ 0.693 × (m/n)
```

### 목표 FPR을 위한 비트 수

원하는 FPR `p`를 달성하기 위한 비트 배열 크기:

```
m = -n × ln(p) / (ln(2))^2 ≈ -1.44 × n × log2(p)
```

### 실용적인 가이드라인

| FPR | 원소당 비트 수 | 해시 함수 수 |
|-----|--------------|-------------|
| 1% | 9.6 bits | 7 |
| 0.1% | 14.4 bits | 10 |
| 0.01% | 19.2 bits | 13 |

---

## 4. 구현

### 기본 구현

```python
import hashlib
from typing import Any

class BloomFilter:
    """
    Bloom Filter 구현

    Parameters:
        expected_items: 예상 삽입 원소 수
        false_positive_rate: 목표 False Positive Rate (기본: 1%)
    """

    def __init__(self, expected_items: int, false_positive_rate: float = 0.01):
        # 최적 파라미터 계산
        self.size = self._optimal_size(expected_items, false_positive_rate)
        self.num_hashes = self._optimal_hashes(self.size, expected_items)
        self.bit_array = [0] * self.size
        self.count = 0

    @staticmethod
    def _optimal_size(n: int, p: float) -> int:
        """목표 FPR을 위한 최적 비트 배열 크기"""
        import math
        m = -n * math.log(p) / (math.log(2) ** 2)
        return int(m) + 1

    @staticmethod
    def _optimal_hashes(m: int, n: int) -> int:
        """최적 해시 함수 개수"""
        import math
        k = (m / n) * math.log(2)
        return max(1, int(k))

    def _hash(self, item: Any, seed: int) -> int:
        """시드 기반 해시 함수"""
        h = hashlib.md5(f"{seed}:{item}".encode()).hexdigest()
        return int(h, 16) % self.size

    def add(self, item: Any) -> None:
        """원소 추가"""
        for seed in range(self.num_hashes):
            index = self._hash(item, seed)
            self.bit_array[index] = 1
        self.count += 1

    def contains(self, item: Any) -> bool:
        """원소 존재 여부 확인 (False Positive 가능)"""
        for seed in range(self.num_hashes):
            index = self._hash(item, seed)
            if self.bit_array[index] == 0:
                return False
        return True

    def __contains__(self, item: Any) -> bool:
        return self.contains(item)

    @property
    def estimated_fpr(self) -> float:
        """현재 상태의 추정 FPR"""
        import math
        if self.count == 0:
            return 0.0
        exponent = -self.num_hashes * self.count / self.size
        return (1 - math.exp(exponent)) ** self.num_hashes
```

### 사용 예시

```python
# 1% FPR로 100만 개 URL 처리용 Bloom Filter 생성
bf = BloomFilter(expected_items=1_000_000, false_positive_rate=0.01)

print(f"비트 배열 크기: {bf.size:,} bits ({bf.size // 8 // 1024:.1f} KB)")
print(f"해시 함수 개수: {bf.num_hashes}")

# URL 추가
bf.add("https://example.com/page1")
bf.add("https://example.com/page2")

# 조회
print("page1" in bf)  # True (추가했으므로)
print("page3" in bf)  # False (높은 확률로) 또는 True (낮은 확률로)
```

---

## 5. 실전 활용: URL 중복 제거

### 웹 크롤링 파이프라인

```python
def crawl_with_bloom_filter(urls: list[str], bf: BloomFilter) -> list[str]:
    """
    Bloom Filter를 사용한 중복 URL 필터링

    Returns:
        새로 발견된 URL 목록
    """
    new_urls = []

    for url in urls:
        # 정규화 (trailing slash, www 등 통일)
        normalized = normalize_url(url)

        if normalized not in bf:
            new_urls.append(url)
            bf.add(normalized)

    return new_urls


def normalize_url(url: str) -> str:
    """URL 정규화"""
    url = url.lower().rstrip('/')
    if url.startswith('www.'):
        url = url[4:]
    return url
```

### 문서 ID 중복 체크

```python
class DocumentDeduplicator:
    """문서 중복 제거기"""

    def __init__(self, expected_docs: int = 10_000_000):
        # 0.1% FPR (10M 문서 중 ~10K false positive)
        self.bf = BloomFilter(expected_docs, false_positive_rate=0.001)
        self.processed_count = 0
        self.duplicate_count = 0

    def process(self, doc_id: str, content: str) -> bool:
        """
        문서 처리. 중복이면 False, 새 문서면 True 반환.
        """
        # doc_id 또는 content hash로 체크
        fingerprint = f"{doc_id}:{hash(content)}"

        if fingerprint in self.bf:
            self.duplicate_count += 1
            return False

        self.bf.add(fingerprint)
        self.processed_count += 1
        return True

    def stats(self) -> dict:
        return {
            "processed": self.processed_count,
            "duplicates_skipped": self.duplicate_count,
            "estimated_fpr": self.bf.estimated_fpr,
        }
```

---

## 6. 변형: Counting Bloom Filter

기본 Bloom Filter는 삭제가 불가능합니다. **Counting Bloom Filter**는 비트 대신 카운터를 사용하여 삭제를 지원합니다.

```python
class CountingBloomFilter:
    """삭제 가능한 Counting Bloom Filter"""

    def __init__(self, expected_items: int, false_positive_rate: float = 0.01):
        self.size = BloomFilter._optimal_size(expected_items, false_positive_rate)
        self.num_hashes = BloomFilter._optimal_hashes(self.size, expected_items)
        self.counters = [0] * self.size  # 비트 대신 카운터

    def add(self, item) -> None:
        for seed in range(self.num_hashes):
            index = self._hash(item, seed)
            self.counters[index] += 1

    def remove(self, item) -> None:
        """원소 삭제 (주의: 없는 원소 삭제 시 문제 발생)"""
        for seed in range(self.num_hashes):
            index = self._hash(item, seed)
            if self.counters[index] > 0:
                self.counters[index] -= 1

    def contains(self, item) -> bool:
        for seed in range(self.num_hashes):
            index = self._hash(item, seed)
            if self.counters[index] == 0:
                return False
        return True
```

---

## 7. 성능 비교

### 메모리 사용량

```python
# 1억 개 원소 저장 비교
n = 100_000_000

# Python set (문자열 평균 20바이트 가정)
set_memory = n * 50  # 객체 오버헤드 포함 ~5GB

# Bloom Filter (1% FPR)
bf_bits = n * 9.6
bf_memory = bf_bits / 8  # ~120MB

print(f"Set: {set_memory / 1e9:.1f} GB")
print(f"Bloom Filter: {bf_memory / 1e6:.1f} MB")
print(f"메모리 절약: {set_memory / bf_memory:.0f}x")
```

### 시간 복잡도

| 연산 | Bloom Filter | Hash Set |
|------|-------------|----------|
| Add | O(k) | O(1) 평균 |
| Contains | O(k) | O(1) 평균 |
| Memory | O(m) | O(n) |

k는 보통 7~13으로 상수이므로 실질적으로 O(1)

---

## 8. 주의사항

### False Positive 처리

```python
def safe_lookup(bf: BloomFilter, item: str, storage: dict) -> bool:
    """
    Bloom Filter 조회 후 실제 저장소에서 확인하는 패턴

    1. BF에 없으면 → 확실히 없음 (빠른 경로)
    2. BF에 있으면 → 실제 저장소에서 확인 (느린 경로)
    """
    if item not in bf:
        return False  # 확실히 없음

    # False Positive 가능성 → 실제 확인 필요
    return item in storage
```

### 용량 초과 주의

```python
def check_capacity(bf: BloomFilter, threshold: float = 0.1) -> bool:
    """
    Bloom Filter 용량 초과 경고

    FPR이 임계값을 넘으면 새 필터로 교체 고려
    """
    if bf.estimated_fpr > threshold:
        print(f"Warning: FPR ({bf.estimated_fpr:.2%}) exceeds threshold")
        return False
    return True
```

---

## 참고 자료

- [Bloom Filter - Wikipedia](https://en.wikipedia.org/wiki/Bloom_filter)
- [Redis BLOOM commands](https://redis.io/docs/data-types/probabilistic/bloom-filter/)
- Paper: "Space/Time Trade-offs in Hash Coding with Allowable Errors" (Bloom, 1970)
