# Trie & Suffix Array 학습 자료

> 토크나이저 구현의 핵심 자료구조 이해하기

---

## 📚 목차

1. [Part 1: Trie (Prefix Tree)](#part-1-trie-prefix-tree)
2. [Part 2: Suffix Array](#part-2-suffix-array)
3. [Part 3: 토크나이저에서의 활용](#part-3-토크나이저에서의-활용)
4. [Part 4: 실습 과제](#part-4-실습-과제)
5. [Part 5: 심화 학습](#part-5-심화-학습)

---

## Part 1: Trie (Prefix Tree)

### 1.1 개념 이해

**Trie**는 문자열 집합을 저장하는 트리 자료구조로, 각 노드가 문자 하나를 나타낸다.

```
예: {"app", "apple", "apt", "bat"} 저장

        root
       /    \
      a      b
      |      |
      p      a
     / \     |
    p   t    t*
    |
    l
    |
    e*

* = 단어의 끝을 표시
```

**핵심 특성:**
- 공통 prefix를 공유하여 메모리 절약
- 검색/삽입: O(m) where m = 문자열 길이
- Prefix 기반 검색에 최적화

### 1.2 왜 토크나이저에 중요한가?

**WordPiece/BPE 토크나이저의 동작:**
1. Vocabulary에 있는 토큰 중 입력과 매칭되는 **가장 긴 것**을 찾아야 함
2. 이 "longest prefix match"가 Trie의 핵심 연산

```
Vocabulary: {"un", "##able", "##avail", "##available"}
입력: "unavailable"

Trie를 사용한 매칭:
1. "un" 매칭 → 남은 것: "available"
2. "##avail" vs "##available" → 더 긴 "##available" 선택
결과: ["un", "##available"]
```

### 1.3 기본 구현

```python
"""
Trie 기본 구현
- insert: 단어 삽입
- search: 정확히 일치하는 단어 검색
- starts_with: prefix로 시작하는 단어 존재 여부
- longest_prefix: 가장 긴 매칭 prefix 찾기 (토크나이저 핵심!)
"""

class TrieNode:
    def __init__(self):
        self.children: dict[str, 'TrieNode'] = {}
        self.is_end: bool = False
        self.value: str | None = None  # 저장된 전체 단어


class Trie:
    def __init__(self):
        self.root = TrieNode()
    
    def insert(self, word: str) -> None:
        """단어를 Trie에 삽입. O(m)"""
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end = True
        node.value = word
    
    def search(self, word: str) -> bool:
        """정확히 일치하는 단어 검색. O(m)"""
        node = self._traverse(word)
        return node is not None and node.is_end
    
    def starts_with(self, prefix: str) -> bool:
        """prefix로 시작하는 단어 존재 여부. O(m)"""
        return self._traverse(prefix) is not None
    
    def _traverse(self, text: str) -> TrieNode | None:
        """text를 따라 Trie 탐색"""
        node = self.root
        for char in text:
            if char not in node.children:
                return None
            node = node.children[char]
        return node
    
    def longest_prefix(self, text: str) -> str | None:
        """
        text의 prefix 중 Trie에 있는 가장 긴 것 반환.
        토크나이저의 핵심 연산! O(m)
        """
        node = self.root
        longest_match = None
        
        for i, char in enumerate(text):
            if char not in node.children:
                break
            node = node.children[char]
            if node.is_end:
                longest_match = node.value
        
        return longest_match
    
    def all_prefixes(self, text: str) -> list[str]:
        """text의 prefix 중 Trie에 있는 모든 것 반환 (길이순)"""
        node = self.root
        prefixes = []
        
        for char in text:
            if char not in node.children:
                break
            node = node.children[char]
            if node.is_end:
                prefixes.append(node.value)
        
        return prefixes


# === 테스트 ===
if __name__ == "__main__":
    trie = Trie()
    
    # Vocabulary 삽입
    vocab = ["un", "una", "unab", "unable", "unavailable", "under"]
    for word in vocab:
        trie.insert(word)
    
    # 기본 검색 테스트
    print("=== 기본 검색 ===")
    print(f"search('unable'): {trie.search('unable')}")      # True
    print(f"search('unab'): {trie.search('unab')}")          # True
    print(f"search('unava'): {trie.search('unava')}")        # False (중간 prefix)
    
    # Longest prefix 테스트 (토크나이저 핵심)
    print("\n=== Longest Prefix (토크나이저 핵심) ===")
    print(f"longest_prefix('unavailable'): {trie.longest_prefix('unavailable')}")  # unavailable
    print(f"longest_prefix('inability'): {trie.longest_prefix('inability')}")      # None
    print(f"longest_prefix('undertake'): {trie.longest_prefix('undertake')}")      # under
    
    # All prefixes 테스트
    print("\n=== All Prefixes ===")
    print(f"all_prefixes('unavailable'): {trie.all_prefixes('unavailable')}")
    # ['un', 'una', 'unab', 'unavailable']
```

### 1.4 WordPiece 토크나이저 구현

```python
"""
WordPiece 토크나이저 - Trie 기반 구현
BERT 스타일의 서브워드 토크나이저
"""

class WordPieceTokenizer:
    def __init__(self, vocab: list[str], unk_token: str = "[UNK]", 
                 prefix: str = "##", max_word_len: int = 100):
        self.unk_token = unk_token
        self.prefix = prefix
        self.max_word_len = max_word_len
        
        # 두 개의 Trie: 단어 시작용 / continuation용
        self.word_start_trie = Trie()
        self.continuation_trie = Trie()
        
        for token in vocab:
            if token.startswith(prefix):
                self.continuation_trie.insert(token)
            else:
                self.word_start_trie.insert(token)
    
    def tokenize_word(self, word: str) -> list[str]:
        """
        단일 단어를 서브워드 토큰으로 분할
        Greedy longest-match 알고리즘
        """
        if len(word) > self.max_word_len:
            return [self.unk_token]
        
        tokens = []
        start = 0
        
        while start < len(word):
            # 첫 토큰인지 continuation인지에 따라 다른 Trie 사용
            if start == 0:
                trie = self.word_start_trie
                substr = word
            else:
                trie = self.continuation_trie
                substr = self.prefix + word[start:]
            
            # Longest prefix match
            match = trie.longest_prefix(substr)
            
            if match is None:
                # 매칭 실패 → 전체 단어를 UNK로
                return [self.unk_token]
            
            tokens.append(match)
            
            # prefix 길이만큼 제외하고 이동
            if start == 0:
                start += len(match)
            else:
                start += len(match) - len(self.prefix)
        
        return tokens
    
    def tokenize(self, text: str) -> list[str]:
        """
        전체 텍스트 토크나이징
        (단순화: 공백 기준 단어 분할)
        """
        words = text.strip().split()
        tokens = []
        for word in words:
            tokens.extend(self.tokenize_word(word.lower()))
        return tokens


# === 테스트 ===
if __name__ == "__main__":
    # 샘플 vocabulary (실제로는 수만 개)
    vocab = [
        # 일반 토큰 (단어 시작)
        "un", "play", "the", "a", "is",
        # Continuation 토큰 (##으로 시작)
        "##able", "##avail", "##available", "##ing", "##ed", "##er", "##s"
    ]
    
    tokenizer = WordPieceTokenizer(vocab)
    
    print("=== WordPiece Tokenization ===")
    
    test_cases = ["unavailable", "playing", "player", "plays", "the"]
    for word in test_cases:
        result = tokenizer.tokenize_word(word)
        print(f"{word:15} → {result}")
    
    # 출력:
    # unavailable     → ['un', '##available']
    # playing         → ['play', '##ing']
    # player          → ['play', '##er']
    # plays           → ['play', '##s']
    # the             → ['the']
```

---

## Part 2: Suffix Array

### 2.1 개념 이해

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

사전순 정렬:
6: $
5: a$
3: ana$
1: anana$
0: banana$
4: na$
2: nana$

Suffix Array: [6, 5, 3, 1, 0, 4, 2]
```

**핵심 직관: "유사한 것끼리 모으기"**

| Rank (i) | SA[i] (시작 위치) | Suffix (내용) | 비고 |
|:---:|:---:|:---|:---|
| 0 | 6 | `$` | |
| 1 | 5 | `a$` | |
| 2 | 3 | `ana$` | `a`로 시작하는 것들이 이웃 |
| 3 | 1 | `anana$` | `ana`와 `anana`가 이웃함 |
| 4 | 0 | `banana$` | |
| 5 | 4 | `na$` | `na`로 시작하는 것들이 이웃 |
| 6 | 2 | `nana$` | `na`와 `nana`가 이웃함 |

- 문자열이 무작위로 섞여 있으면 비교하기 힘들지만, 사전순으로 정렬하면 **공통된 접두사를 가진 문자열들이 서로 이웃(Adjacent)**하게 배치됨
- **Why?** O(N²)의 모든 쌍 비교를 피하고, O(N)의 이웃 비교만으로 패턴을 찾기 위함

### 2.2 왜 토크나이저에 중요한가?

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

### 2.3 LCP Array 직관: "얼마나 똑같은지 재기"

**LCP (Longest Common Prefix)**: 정렬된 상태에서 **자신(i)과 바로 위 이웃(i-1)** 사이의 공통된 접두사 길이

```
Suffix Array 상에서:
  Rank 2: ana$
  Rank 3: anana$   ← LCP[3] = 3 ("ana"가 공통)
```

- 정렬된 상태에서 바로 윗집하고만 비교해도, 해당 패턴이 얼마나 반복되는지 알 수 있음
- **BPE 적용:** LCP 값이 높게 유지되는 구간 = **빈번하게 등장하는 긴 패턴**

### 2.4 기본 구현

```python
"""
Suffix Array 기본 구현
- 단순 정렬 버전: O(n² log n) - 이해용
- 실제 사용은 라이브러리 (pysuffix, divsufsort 등)
"""

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


def build_lcp_array(text: str, suffix_array: list[int]) -> list[int]:
    """
    LCP (Longest Common Prefix) Array 구축.
    lcp[i] = suffix_array[i]와 suffix_array[i-1]의 공통 prefix 길이

    Kasai's Algorithm: O(n)

    === SA와 Rank의 관계 (역함수) ===
    - SA[등수] = 원래_위치   → "정렬 후 i등인 접미사는 원래 어디에 있었나?"
    - Rank[원래_위치] = 등수 → "원래 위치 i에서 시작하는 접미사는 정렬 후 몇 등인가?"

    왜 Rank가 필요한가?
    Kasai 알고리즘은 원본 문자열 순서(0, 1, 2...)대로 훑으면서 LCP를 계산하기 때문.
    - 현재 내가 처리할 접미사: Text[i:]
    - 나의 등수 확인: Rank[i]
    - 비교 대상(내 윗집) 찾기: SA[Rank[i] - 1]

    === 최적화 원리: "이미 센 것은 다시 세지 않는다" ===
    banana와 bandana가 앞 3글자(ban)가 같다면,
    → 맨 앞글자를 뗀 anana와 andana는 최소 2글자(an)는 무조건 같음
    → k를 0부터 다시 세지 않고, k-1부터 비교 시작
    """
    n = len(text)
    rank = [0] * n  # rank[i] = suffix i의 suffix array에서의 위치
    lcp = [0] * n

    # SA의 역함수인 Rank 배열 구축
    for i, suffix_idx in enumerate(suffix_array):
        rank[suffix_idx] = i

    k = 0  # 현재 LCP 길이
    for i in range(n):
        if rank[i] == 0:
            k = 0
            continue

        j = suffix_array[rank[i] - 1]  # 이전 suffix의 시작 인덱스 (내 윗집)

        # 공통 prefix 계산
        while i + k < n and j + k < n and text[i + k] == text[j + k]:
            k += 1

        lcp[rank[i]] = k

        # 핵심 최적화: 앞글자 하나 뗐으니 길이를 1만 줄이고 비교 재개
        if k > 0:
            k -= 1

    return lcp


def find_repeated_substrings(text: str, min_length: int = 2) -> dict[str, int]:
    """
    Suffix Array + LCP를 활용한 반복 substring 탐지.
    BPE 학습의 기초가 되는 연산.
    """
    sa = build_suffix_array_naive(text)
    lcp = build_lcp_array(text, sa)
    
    repeated = {}
    
    for i in range(1, len(text)):
        if lcp[i] >= min_length:
            # LCP 길이만큼의 공통 prefix가 반복됨
            for length in range(min_length, lcp[i] + 1):
                substr = text[sa[i]:sa[i] + length]
                repeated[substr] = repeated.get(substr, 0) + 1
    
    # 빈도 기준 정렬
    return dict(sorted(repeated.items(), key=lambda x: -x[1]))


# === 테스트 ===
if __name__ == "__main__":
    text = "abracadabra$"
    
    print("=== Suffix Array 구축 ===")
    sa = build_suffix_array_naive(text)
    print(f"Text: {text}")
    print(f"Suffix Array: {sa}")
    print("\n정렬된 suffixes:")
    for i, idx in enumerate(sa):
        print(f"  SA[{i}] = {idx}: {text[idx:]}")
    
    print("\n=== LCP Array ===")
    lcp = build_lcp_array(text, sa)
    print(f"LCP Array: {lcp}")
    print("\nLCP 의미:")
    for i in range(1, len(sa)):
        print(f"  LCP[{i}] = {lcp[i]}: '{text[sa[i-1]:sa[i-1]+lcp[i]]}' "
              f"({text[sa[i-1]:]} vs {text[sa[i]:]})")
    
    print("\n=== 반복 Substring 탐지 (BPE 기초) ===")
    repeated = find_repeated_substrings(text, min_length=2)
    for substr, count in list(repeated.items())[:10]:
        print(f"  '{substr}': {count}회")
```

### 2.4 BPE 학습에서의 활용

```python
"""
BPE (Byte Pair Encoding) 학습 - Suffix Array 활용
가장 빈번한 문자 쌍을 찾아 병합하는 과정
"""

from collections import Counter


def get_pair_frequencies_naive(corpus: list[list[str]]) -> Counter:
    """
    Naive 방식: 모든 단어의 모든 인접 쌍 순회
    O(전체 문자 수) per iteration
    """
    pairs = Counter()
    for word in corpus:
        for i in range(len(word) - 1):
            pairs[(word[i], word[i + 1])] += 1
    return pairs


def get_pair_frequencies_suffix_array(text: str) -> Counter:
    """
    Suffix Array + LCP를 활용한 bigram 빈도 계산

    원리:
    - SA가 정렬되어 있으므로 같은 bigram으로 시작하는 suffix들이 연속
    - LCP[i] >= 2이면 SA[i-1]과 SA[i] 위치의 bigram이 동일
    - 연속 구간의 길이 = 해당 bigram의 출현 횟수

    주의: 단순 bigram 카운팅에는 naive O(n)이 더 효율적!
    SA+LCP는 "임의 길이 패턴"이나 "반복 패턴 탐지"에 강점이 있음
    """
    sa = build_suffix_array_naive(text)
    lcp = build_lcp_array(text, sa)

    pairs = Counter()
    n = len(text)
    i = 0

    while i < n:
        # bigram 추출 가능한 위치인지 확인
        if sa[i] + 1 >= n:
            i += 1
            continue

        bigram = text[sa[i]:sa[i] + 2]
        if ' ' in bigram:
            i += 1
            continue

        # 같은 bigram prefix를 공유하는 연속 구간 카운트
        count = 1
        j = i + 1
        while j < n and lcp[j] >= 2:
            if sa[j] + 1 < n and text[sa[j]:sa[j] + 2] == bigram:
                count += 1
            j += 1

        pairs[(bigram[0], bigram[1])] = count
        i = j  # 다음 그룹으로 건너뛰기

    return pairs


def get_pair_frequencies_naive_simple(text: str) -> Counter:
    """
    Naive 방식: 텍스트를 한 번 순회하며 모든 bigram 카운트
    O(n) - 단순 bigram 카운팅에는 이게 최선!
    """
    pairs = Counter()
    for i in range(len(text) - 1):
        if text[i] != ' ' and text[i + 1] != ' ':
            pairs[(text[i], text[i + 1])] += 1
    return pairs


class SimpleBPE:
    """
    단순화된 BPE 학습기
    실제 구현은 HuggingFace tokenizers 참고
    """
    
    def __init__(self):
        self.merges = []  # 학습된 병합 규칙
        self.vocab = set()
    
    def train(self, corpus: list[str], num_merges: int = 10):
        """
        BPE 학습: 가장 빈번한 쌍을 반복적으로 병합
        """
        # 단어를 문자 리스트로 변환 (단어 끝 표시 포함)
        words = []
        for text in corpus:
            for word in text.split():
                words.append(list(word) + ['</w>'])
        
        # 초기 vocabulary: 모든 문자
        self.vocab = set(char for word in words for char in word)
        
        for i in range(num_merges):
            # 가장 빈번한 쌍 찾기
            pairs = get_pair_frequencies_naive(words)
            if not pairs:
                break
            
            best_pair = pairs.most_common(1)[0][0]
            print(f"Merge {i + 1}: {best_pair} (빈도: {pairs[best_pair]})")
            
            # 병합 실행
            new_token = ''.join(best_pair)
            self.merges.append(best_pair)
            self.vocab.add(new_token)
            
            # 코퍼스 업데이트
            words = self._apply_merge(words, best_pair)
        
        return self.merges
    
    def _apply_merge(self, words: list[list[str]], 
                     pair: tuple[str, str]) -> list[list[str]]:
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
    
    def tokenize(self, word: str) -> list[str]:
        """학습된 BPE로 단어 토크나이징"""
        tokens = list(word) + ['</w>']
        
        for pair in self.merges:
            i = 0
            while i < len(tokens) - 1:
                if tokens[i] == pair[0] and tokens[i + 1] == pair[1]:
                    tokens = tokens[:i] + [pair[0] + pair[1]] + tokens[i + 2:]
                else:
                    i += 1
        
        return tokens


# === 테스트 ===
if __name__ == "__main__":
    # 학습 코퍼스
    corpus = [
        "low lower lowest",
        "new newer newest",
        "low low low new new"
    ]
    
    print("=== BPE 학습 ===")
    bpe = SimpleBPE()
    bpe.train(corpus, num_merges=10)
    
    print("\n=== 토크나이징 테스트 ===")
    test_words = ["lower", "newer", "lowest", "newest"]
    for word in test_words:
        tokens = bpe.tokenize(word)
        print(f"{word:10} → {tokens}")
```

---

## Part 3: 토크나이저에서의 활용

### 3.1 HuggingFace tokenizers 내부 구조

```python
"""
HuggingFace tokenizers가 내부적으로 Trie를 어떻게 사용하는지 이해하기
(실제 구현은 Rust로 되어 있음)
"""

# 실제 사용 예시
from transformers import AutoTokenizer

def explore_tokenizer():
    """BERT 토크나이저의 동작 분석"""
    tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
    
    # Vocabulary 살펴보기
    vocab = tokenizer.get_vocab()
    print(f"Vocabulary 크기: {len(vocab)}")
    
    # Continuation 토큰 (##으로 시작) 비율
    continuation_tokens = [t for t in vocab if t.startswith("##")]
    print(f"Continuation 토큰 수: {len(continuation_tokens)}")
    
    # 토크나이징 과정 분석
    text = "unavailable"
    tokens = tokenizer.tokenize(text)
    print(f"\n'{text}' → {tokens}")
    
    # 내부적으로 일어나는 일:
    # 1. 'unavailable' 시작
    # 2. Trie에서 longest match: 'una' (만약 있다면) 또는 'un'
    # 3. 남은 부분에 '##' 붙여서 continuation Trie 검색
    # 4. 반복...
    
    return tokenizer


# 한국어 토크나이저 예시
def explore_korean_tokenizer():
    """한국어 토크나이저의 특수성"""
    from transformers import AutoTokenizer
    
    # KoBERT 또는 다른 한국어 모델
    try:
        tokenizer = AutoTokenizer.from_pretrained("klue/bert-base")
        
        text = "자연어처리는 재미있습니다"
        tokens = tokenizer.tokenize(text)
        print(f"'{text}' → {tokens}")
        
        # 한국어의 경우:
        # - 형태소 분석 + 서브워드가 결합되는 경우가 많음
        # - 음절 단위 vs 자모 단위 선택이 중요
        
    except Exception as e:
        print(f"한국어 토크나이저 로드 실패: {e}")
```

### 3.2 커스텀 한국어 토크나이저 설계

```python
"""
한국어 Document AI를 위한 토크나이저 설계 고려사항
"""

class KoreanTokenizerDesign:
    """
    한국어 토크나이저 설계 시 고려할 점들
    """
    
    # 1. 음절 vs 자모 분해
    # 음절: "한글" → ["한", "글"]
    # 자모: "한글" → ["ㅎ", "ㅏ", "ㄴ", "ㄱ", "ㅡ", "ㄹ"]
    
    # 2. 형태소 분석 통합 여부
    # 형태소: "먹었습니다" → ["먹", "었", "습니다"]
    # 서브워드만: "먹었습니다" → ["먹었", "##습니다"]
    
    # 3. 숫자/영문 처리
    # 재무 문서에서 "2,500만원", "ROE 15%" 등의 처리
    
    @staticmethod
    def example_hybrid_approach():
        """
        하이브리드 접근: 형태소 + BPE
        
        "자연어처리기술" 처리 과정:
        1. 형태소 분석: ["자연어", "처리", "기술"]
        2. 각 형태소에 BPE 적용:
           - "자연어" → ["자연", "##어"]
           - "처리" → ["처리"]
           - "기술" → ["기술"]
        3. 최종: ["자연", "##어", "처리", "기술"]
        """
        pass
    
    @staticmethod
    def financial_document_considerations():
        """
        재무 문서 특화 토크나이저 고려사항
        
        1. 숫자 정규화: 
           - "1,234,567원" → "[NUM]원" 또는 자릿수 보존
           
        2. 테이블 구조 토큰:
           - [ROW_SEP], [COL_SEP], [HEADER] 등 특수 토큰
           
        3. 재무 용어 vocabulary:
           - "자기자본이익률", "부채비율" 등을 단일 토큰으로
           
        4. 연도/분기 패턴:
           - "2024년 1분기", "FY2024", "Q1" 등 통일 처리
        """
        pass
```

---

## Part 4: 실습 과제

### 과제 1: Trie 확장 (난이도: ⭐⭐)

```python
"""
과제: Trie에 다음 기능 추가
1. delete(word): 단어 삭제
2. count_prefix(prefix): prefix로 시작하는 단어 수
3. autocomplete(prefix, limit): prefix로 시작하는 단어 목록 반환
"""

class ExtendedTrie(Trie):
    def __init__(self):
        super().__init__()
        # TODO: 필요한 추가 속성
    
    def delete(self, word: str) -> bool:
        """단어 삭제. 성공하면 True 반환."""
        # TODO: 구현
        # 힌트: 자식이 없는 노드는 제거해야 함
        pass
    
    def count_prefix(self, prefix: str) -> int:
        """prefix로 시작하는 단어 수 반환."""
        # TODO: 구현
        # 힌트: 각 노드에 하위 단어 수를 저장하면 O(m)
        pass
    
    def autocomplete(self, prefix: str, limit: int = 10) -> list[str]:
        """prefix로 시작하는 단어 목록 반환."""
        # TODO: 구현
        # 힌트: prefix 노드에서 DFS
        pass


# 테스트 케이스
def test_extended_trie():
    trie = ExtendedTrie()
    words = ["apple", "app", "application", "apply", "apt", "banana"]
    for w in words:
        trie.insert(w)
    
    # delete 테스트
    assert trie.search("apple") == True
    assert trie.delete("apple") == True
    assert trie.search("apple") == False
    assert trie.search("app") == True  # 다른 단어는 유지
    
    # count_prefix 테스트
    assert trie.count_prefix("app") == 3  # app, application, apply
    assert trie.count_prefix("xyz") == 0
    
    # autocomplete 테스트
    results = trie.autocomplete("app", limit=5)
    assert "app" in results
    assert "application" in results
    
    print("모든 테스트 통과!")
```

### 과제 2: Suffix Array 응용 (난이도: ⭐⭐⭐)

```python
"""
과제: Suffix Array를 활용한 문자열 검색
1. find_all_occurrences(text, pattern): pattern의 모든 출현 위치
2. longest_repeated_substring(text): 가장 긴 반복 부분문자열
"""

def find_all_occurrences(text: str, pattern: str) -> list[int]:
    """
    Suffix Array를 이용한 패턴 검색.
    Binary search로 O(m log n) 달성 가능.
    
    Returns: pattern이 시작되는 모든 인덱스
    """
    # TODO: 구현
    # 힌트: SA가 정렬되어 있으므로 이진 탐색 가능
    pass


def longest_repeated_substring(text: str) -> str:
    """
    가장 긴 반복 부분문자열 찾기.
    LCP array의 최대값이 답.
    
    Returns: 가장 긴 반복 부분문자열
    """
    # TODO: 구현
    pass


# 테스트
def test_suffix_array_applications():
    text = "abracadabra"
    
    # find_all_occurrences 테스트
    positions = find_all_occurrences(text, "abra")
    assert set(positions) == {0, 7}
    
    positions = find_all_occurrences(text, "a")
    assert set(positions) == {0, 3, 5, 7, 10}
    
    # longest_repeated_substring 테스트
    lrs = longest_repeated_substring(text)
    assert lrs == "abra"
    
    print("모든 테스트 통과!")
```

### 과제 3: 미니 토크나이저 (난이도: ⭐⭐⭐⭐)

```python
"""
과제: 한국어 지원 미니 토크나이저 구현
1. BPE 학습 (Suffix Array 활용)
2. 토크나이징 (Trie 활용)
3. 숫자 정규화 전처리
"""

class MiniKoreanTokenizer:
    def __init__(self):
        self.vocab_trie = Trie()
        self.merges = []
    
    def train(self, corpus: list[str], vocab_size: int = 1000):
        """
        한국어 코퍼스에서 BPE vocabulary 학습.
        
        1. 초기 vocabulary: 모든 음절 + 기본 토큰
        2. Suffix Array로 빈번한 쌍 탐지
        3. vocab_size까지 반복 병합
        """
        # TODO: 구현
        pass
    
    def tokenize(self, text: str) -> list[str]:
        """
        학습된 vocabulary로 토크나이징.
        
        1. 숫자 정규화 (예: "1,234원" → "[NUM]원")
        2. Trie 기반 longest-match 토크나이징
        """
        # TODO: 구현
        pass
    
    def _normalize_numbers(self, text: str) -> str:
        """숫자 정규화 전처리"""
        # TODO: 구현
        # 힌트: 정규표현식 활용
        pass


# 테스트
def test_mini_tokenizer():
    corpus = [
        "자연어처리는 재미있습니다",
        "딥러닝 모델을 학습합니다",
        "매출액은 1,234억원입니다",
    ]
    
    tokenizer = MiniKoreanTokenizer()
    tokenizer.train(corpus, vocab_size=100)
    
    test_text = "자연어처리 모델"
    tokens = tokenizer.tokenize(test_text)
    print(f"'{test_text}' → {tokens}")
    
    # 숫자 정규화 테스트
    test_num = "매출 2,500만원"
    tokens = tokenizer.tokenize(test_num)
    assert "[NUM]" in ''.join(tokens)
    
    print("테스트 완료!")
```

---

## Part 5: 심화 학습

### 5.1 더 효율적인 알고리즘

```python
"""
실제 프로덕션에서 사용되는 효율적인 알고리즘들
"""

# 1. Suffix Array 구축: O(n) 알고리즘
# - SA-IS (Induced Sorting) 알고리즘
# - DC3/Skew 알고리즘
# 
# Python 라이브러리:
# - pysuffix: pip install pysuffix
# - divsufsort: pip install pydivsufsort

# 2. Trie 압축: Radix Tree (Patricia Trie)
# - 단일 자식만 있는 노드들을 병합
# - 메모리 사용량 대폭 감소

class RadixTreeNode:
    """압축 Trie 노드"""
    def __init__(self):
        self.children: dict[str, 'RadixTreeNode'] = {}  # 문자열 edge
        self.is_end: bool = False
        self.value: str | None = None


# 3. Double-Array Trie
# - 매우 빠른 검색 (배열 인덱싱만 사용)
# - HuggingFace tokenizers의 실제 구현 방식
# - 구축은 복잡하지만 검색은 O(m)에 상수 factor 최소화
```

### 5.2 참고 자료

**논문:**
- "Neural Machine Translation of Rare Words with Subword Units" (Sennrich et al., 2016) - BPE 도입
- "Google's Neural Machine Translation System" (Wu et al., 2016) - WordPiece
- "SentencePiece: A simple and language independent subword tokenizer" (Kudo & Richardson, 2018)

**도서:**
- "Introduction to Algorithms" (CLRS) - Suffix Array, Trie 기초
- "Algorithms on Strings, Trees, and Sequences" (Gusfield) - 문자열 알고리즘 심화

**코드 참고:**
- HuggingFace tokenizers: https://github.com/huggingface/tokenizers
- SentencePiece: https://github.com/google/sentencepiece

**실습 자료:**
- LeetCode Trie 문제들: #208, #211, #212, #421
- 백준 Suffix Array: #9248, #9249, #11479

---

## 체크리스트

학습 완료 후 확인:

- [ ] Trie의 insert, search, longest_prefix 구현 가능
- [ ] Suffix Array의 개념과 LCP Array 이해
- [ ] WordPiece 토크나이저의 동작 원리 설명 가능
- [ ] BPE 학습 과정에서 Suffix Array 활용 이유 이해
- [ ] 실습 과제 1, 2 완료
- [ ] (선택) 실습 과제 3 완료
