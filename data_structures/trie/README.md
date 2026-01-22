# Trie (Prefix Tree)

> 토크나이저의 핵심 자료구조 - 문자열 검색과 prefix matching에 최적화

---

## 1. 개념

**Trie**는 문자열 집합을 저장하는 트리 자료구조로, 각 노드가 문자 하나를 나타낸다.

```
예: {"app", "apple", "apt", "bat"} 저장

        root
       /    \
      a      b
      |      |
      p      a
     / \     |
    p   t*   t*
    |
    l
    |
    e*

* = 단어의 끝을 표시
```

### 핵심 특성

| 특성 | 설명 |
|------|------|
| **공간 효율** | 공통 prefix를 공유하여 메모리 절약 |
| **빠른 검색** | 검색/삽입: O(m), m = 문자열 길이 |
| **Prefix 연산** | Prefix 기반 검색에 최적화 |

---

## 2. 왜 토크나이저에 중요한가?

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

---

## 3. 시간/공간 복잡도

| 연산 | 시간복잡도 | 설명 |
|------|-----------|------|
| insert | O(m) | m = 단어 길이 |
| search | O(m) | 정확한 단어 검색 |
| starts_with | O(m) | prefix 존재 여부 |
| longest_prefix | O(m) | 가장 긴 매칭 prefix |
| all_prefixes | O(m) | 모든 매칭 prefix |

**공간복잡도:**
- 최악: O(총 문자 수)
- 실제: 공통 prefix 공유로 더 효율적

---

## 4. 구현

### 기본 구현

```python
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

        for char in text:
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
```

### 사용 예시

```python
trie = Trie()

# Vocabulary 삽입
vocab = ["un", "una", "unab", "unable", "unavailable", "under"]
for word in vocab:
    trie.insert(word)

# 기본 검색
print(trie.search("unable"))      # True
print(trie.search("unava"))       # False (중간 prefix)

# Longest prefix match (토크나이저 핵심)
print(trie.longest_prefix("unavailable"))  # "unavailable"
print(trie.longest_prefix("inability"))    # None
print(trie.longest_prefix("undertake"))    # "under"

# All prefixes
print(trie.all_prefixes("unavailable"))
# ['un', 'una', 'unab', 'unavailable']
```

---

## 5. WordPiece 토크나이저 구현

```python
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
            if start == 0:
                trie = self.word_start_trie
                substr = word
            else:
                trie = self.continuation_trie
                substr = self.prefix + word[start:]

            match = trie.longest_prefix(substr)

            if match is None:
                return [self.unk_token]

            tokens.append(match)

            if start == 0:
                start += len(match)
            else:
                start += len(match) - len(self.prefix)

        return tokens


# 사용 예시
vocab = [
    "un", "play", "the", "a", "is",
    "##able", "##avail", "##available", "##ing", "##ed", "##er", "##s"
]

tokenizer = WordPieceTokenizer(vocab)

print(tokenizer.tokenize_word("unavailable"))  # ['un', '##available']
print(tokenizer.tokenize_word("playing"))      # ['play', '##ing']
print(tokenizer.tokenize_word("player"))       # ['play', '##er']
```

---

## 6. 변형: Radix Tree (Patricia Trie)

단일 자식만 있는 노드들을 병합하여 메모리 절약:

```
일반 Trie:           Radix Tree:
    t                    t
    |                    |
    e                   est
    |                   / \
    s                  s   ing
    |
    t
   / \
  s   i
      |
      n
      |
      g
```

**장점:**
- 메모리 사용량 대폭 감소
- 검색 속도 동일 (O(m))

---

## 7. 실전 활용

### HuggingFace tokenizers 내부 구조

```python
from transformers import AutoTokenizer

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
print(f"'{text}' → {tokens}")
```

---

## 참고 자료

**논문:**
- "Neural Machine Translation of Rare Words with Subword Units" (Sennrich et al., 2016) - BPE
- "Google's Neural Machine Translation System" (Wu et al., 2016) - WordPiece

**코드:**
- HuggingFace tokenizers: https://github.com/huggingface/tokenizers

**LeetCode 연습:**
- #208: Implement Trie
- #211: Design Add and Search Words Data Structure
- #212: Word Search II
