# Suffix Array

> BPE 학습의 핵심 자료구조 - 반복 패턴 탐지에 최적화

---

## 1. 개념

**Suffix Array**는 문자열의 모든 suffix를 사전순으로 정렬한 인덱스 배열이다.

```
문자열: "banana$" ($ = 종료 문자)

모든 suffix:
0: banana$
1: anana$
2: nana$
3: ana$
4: na$
5: a$
6: $

사전순 정렬 후:
6: $
5: a$
3: ana$
1: anana$
0: banana$
4: na$
2: nana$

Suffix Array: [6, 5, 3, 1, 0, 4, 2]
```

### 핵심 직관: "유사한 것끼리 모으기"

| Rank (i) | SA[i] | Suffix | 비고 |
|:---:|:---:|:---|:---|
| 0 | 6 | `$` | |
| 1 | 5 | `a$` | |
| 2 | 3 | `ana$` | `a`로 시작하는 것들이 이웃 |
| 3 | 1 | `anana$` | `ana`와 `anana`가 이웃함 |
| 4 | 0 | `banana$` | |
| 5 | 4 | `na$` | `na`로 시작하는 것들이 이웃 |
| 6 | 2 | `nana$` | `na`와 `nana`가 이웃함 |

- 사전순으로 정렬하면 **공통된 접두사를 가진 문자열들이 서로 이웃**하게 배치됨
- O(N²)의 모든 쌍 비교를 피하고, O(N)의 이웃 비교만으로 패턴을 찾을 수 있음

---

## 2. 왜 토크나이저에 중요한가?

**BPE (Byte Pair Encoding)의 핵심**: 텍스트 내에서 **"가장 자주 등장하는 문자열 패턴(Subword)"**을 찾아내어 토큰화

**학습 과정에서의 문제:**
1. 코퍼스에서 **가장 빈번한 문자 쌍**을 찾아야 함
2. Naive하게 하면 O(코퍼스 크기 × vocab 크기) 반복 → **O(N²)** 비교
3. Suffix Array + LCP로 **O(N)** 만에 모든 반복 substring 탐지 가능

```
"abracadabra"에서 substring 빈도:
1. Suffix Array 구축 → 유사한 것끼리 이웃하게 정렬
2. LCP Array로 인접 suffix 간 공통 prefix 길이 계산
3. LCP 값이 높은 구간 = 자주 반복되는 패턴
   → BPE가 병합할 후보
```

---

## 3. LCP Array

**LCP (Longest Common Prefix)**: 정렬된 상태에서 **자신(i)과 바로 위 이웃(i-1)** 사이의 공통된 접두사 길이

```
Suffix Array 상에서:
  Rank 2: ana$
  Rank 3: anana$   ← LCP[3] = 3 ("ana"가 공통)
```

### SA와 Rank의 관계 (역함수)

```
SA[등수] = 원래_위치   → "정렬 후 i등인 접미사는 원래 어디에 있었나?"
Rank[원래_위치] = 등수 → "원래 위치 i에서 시작하는 접미사는 정렬 후 몇 등인가?"
```

**BPE 적용:** LCP 값이 높게 유지되는 구간 = **빈번하게 등장하는 긴 패턴**

---

## 4. 시간/공간 복잡도

| 연산 | 단순 구현 | 최적 알고리즘 |
|------|----------|-------------|
| SA 구축 | O(n² log n) | O(n) (SA-IS, DC3) |
| LCP 구축 (Kasai) | O(n) | O(n) |
| 패턴 검색 | O(m + log n) | O(m + log n) |

**공간복잡도:** O(n)

---

## 5. 구현

### Suffix Array 구축 (단순 버전)

```python
def build_suffix_array_naive(text: str) -> list[int]:
    """
    Suffix Array를 단순 정렬로 구축.
    O(n² log n) - 교육용, 실제로는 O(n) 알고리즘 사용
    """
    n = len(text)
    # (suffix 시작 인덱스, suffix 문자열) 쌍 생성
    suffixes = [(i, text[i:]) for i in range(n)]
    # suffix 문자열 기준 정렬
    suffixes.sort(key=lambda x: x[1])
    # 정렬된 인덱스만 추출
    return [idx for idx, _ in suffixes]
```

### LCP Array 구축 (Kasai's Algorithm)

```python
def build_lcp_array(text: str, suffix_array: list[int]) -> list[int]:
    """
    LCP Array 구축 - Kasai's Algorithm: O(n)

    최적화 원리: "이미 센 것은 다시 세지 않는다"
    - banana와 bandana가 앞 3글자(ban)가 같다면,
    - 맨 앞글자를 뗀 anana와 andana는 최소 2글자(an)는 무조건 같음
    - k를 0부터 다시 세지 않고, k-1부터 비교 시작
    """
    n = len(text)
    rank = [0] * n  # rank[i] = suffix i의 SA에서의 위치
    lcp = [0] * n

    # SA의 역함수인 Rank 배열 구축
    for i, suffix_idx in enumerate(suffix_array):
        rank[suffix_idx] = i

    k = 0
    for i in range(n):
        if rank[i] == 0:
            k = 0
            continue

        j = suffix_array[rank[i] - 1]  # 내 윗집 (SA에서 바로 앞)

        # 공통 prefix 계산
        while i + k < n and j + k < n and text[i + k] == text[j + k]:
            k += 1

        lcp[rank[i]] = k

        # 핵심 최적화: 앞글자 하나 뗐으니 길이를 1만 줄이고 비교 재개
        if k > 0:
            k -= 1

    return lcp
```

### 반복 Substring 탐지

```python
def find_repeated_substrings(text: str, min_length: int = 2) -> dict[str, int]:
    """
    Suffix Array + LCP를 활용한 반복 substring 탐지.
    BPE 학습의 기초가 되는 연산.

    원리:
    - SA가 정렬되어 있으므로, 같은 prefix를 가진 suffix들이 인접
    - LCP[i]가 k이면, SA[i-1]과 SA[i]가 길이 k의 공통 prefix 공유
    - 연속으로 LCP >= k인 구간의 길이 + 1 = 해당 prefix의 출현 횟수
    """
    sa = build_suffix_array_naive(text)
    lcp = build_lcp_array(text, sa)
    n = len(text)

    repeated = {}

    for length in range(min_length, n):
        i = 1
        while i < n:
            if lcp[i] >= length:
                # LCP >= length인 연속 구간의 시작
                start = i - 1
                while i < n and lcp[i] >= length:
                    i += 1
                end = i - 1

                count = end - start + 1  # 구간 내 suffix 수 = 출현 횟수
                substr = text[sa[start]:sa[start] + length]

                if substr not in repeated:
                    repeated[substr] = count
            else:
                i += 1

    return dict(sorted(repeated.items(), key=lambda x: (-x[1], -len(x[0]))))
```

---

## 6. BPE 학습에서의 활용

```python
class SimpleBPE:
    """단순화된 BPE 학습기"""

    def __init__(self):
        self.merges = []
        self.vocab = set()

    def train(self, corpus: list[str], num_merges: int = 10):
        """BPE 학습: 가장 빈번한 쌍을 반복적으로 병합"""
        # 단어를 문자 리스트로 변환
        words = []
        for text in corpus:
            for word in text.split():
                words.append(list(word) + ['</w>'])

        # 초기 vocabulary
        self.vocab = set(char for word in words for char in word)

        for i in range(num_merges):
            # 가장 빈번한 쌍 찾기
            pairs = {}
            for word in words:
                for j in range(len(word) - 1):
                    pair = (word[j], word[j + 1])
                    pairs[pair] = pairs.get(pair, 0) + 1

            if not pairs:
                break

            best_pair = max(pairs, key=pairs.get)
            if pairs[best_pair] < 2:
                break

            print(f"Merge: {best_pair[0]} + {best_pair[1]} → {best_pair[0] + best_pair[1]}")

            self.merges.append(best_pair)
            self.vocab.add(best_pair[0] + best_pair[1])

            # 코퍼스에 병합 적용
            words = self._apply_merge(words, best_pair)

        return self.merges

    def _apply_merge(self, words, pair):
        """병합 규칙을 코퍼스에 적용"""
        new_words = []
        for word in words:
            new_word = []
            i = 0
            while i < len(word):
                if (i < len(word) - 1 and
                    word[i] == pair[0] and
                    word[i + 1] == pair[1]):
                    new_word.append(pair[0] + pair[1])
                    i += 2
                else:
                    new_word.append(word[i])
                    i += 1
            new_words.append(new_word)
        return new_words
```

### 사용 예시

```python
corpus = [
    "low lower lowest",
    "new newer newest",
    "low low low new new"
]

bpe = SimpleBPE()
bpe.train(corpus, num_merges=10)

# 출력:
# Merge: l + o → lo
# Merge: lo + w → low
# Merge: e + r → er
# Merge: n + e → ne
# Merge: ne + w → new
# ...
```

---

## 7. 고급 알고리즘

### SA-IS (Suffix Array - Induced Sorting)

O(n) 시간에 Suffix Array 구축:
- 문자를 L-type, S-type으로 분류
- LMS (Leftmost S-type) suffix만 먼저 정렬
- 나머지는 induced sorting으로 채움

```python
# 실제 사용시 라이브러리 활용 권장
# pip install pydivsufsort
from pydivsufsort import divsufsort

text = "banana$"
sa = divsufsort(text.encode())  # O(n)
```

### Longest Repeated Substring

```python
def longest_repeated_substring(text: str) -> str:
    """LCP array의 최대값이 가장 긴 반복 substring"""
    sa = build_suffix_array_naive(text)
    lcp = build_lcp_array(text, sa)

    max_lcp = 0
    max_idx = 0

    for i in range(1, len(lcp)):
        if lcp[i] > max_lcp:
            max_lcp = lcp[i]
            max_idx = i

    if max_lcp == 0:
        return ""

    return text[sa[max_idx]:sa[max_idx] + max_lcp]


# 예시
text = "abracadabra"
print(longest_repeated_substring(text))  # "abra"
```

---

## 8. 실전 활용

### 문서 유사도 탐지

Suffix Array로 공통 substring 빠르게 탐지:

```python
def find_common_substrings(text1: str, text2: str, min_len: int = 10):
    """두 텍스트의 공통 substring 찾기"""
    # 두 텍스트를 구분자로 연결
    combined = text1 + "#" + text2 + "$"
    n1 = len(text1)

    sa = build_suffix_array_naive(combined)
    lcp = build_lcp_array(combined, sa)

    common = []
    for i in range(1, len(sa)):
        if lcp[i] >= min_len:
            # 두 suffix가 서로 다른 텍스트에서 왔는지 확인
            pos1 = sa[i - 1]
            pos2 = sa[i]
            if (pos1 < n1) != (pos2 < n1):  # XOR
                substr = combined[sa[i]:sa[i] + lcp[i]]
                if "#" not in substr and "$" not in substr:
                    common.append(substr)

    return common
```

---

## 참고 자료

**논문:**
- "Neural Machine Translation of Rare Words with Subword Units" (Sennrich et al., 2016) - BPE
- "SentencePiece: A simple and language independent subword tokenizer" (Kudo & Richardson, 2018)

**도서:**
- "Introduction to Algorithms" (CLRS) - Suffix Array 기초
- "Algorithms on Strings, Trees, and Sequences" (Gusfield) - 문자열 알고리즘 심화

**코드:**
- SentencePiece: https://github.com/google/sentencepiece

**백준 연습:**
- #9248: Suffix Array
- #9249: 최장 공통 부분 문자열
- #11479: 서로 다른 부분 문자열의 개수 2
