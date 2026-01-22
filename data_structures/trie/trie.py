"""
Trie (Prefix Tree) 구현
토크나이저의 핵심 자료구조

실행: python trie.py
"""

from __future__ import annotations


class TrieNode:
    """Trie 노드"""

    def __init__(self):
        self.children: dict[str, TrieNode] = {}
        self.is_end: bool = False
        self.value: str | None = None  # 저장된 전체 단어


class Trie:
    """
    Trie (Prefix Tree) 구현

    시간복잡도 (m = 문자열 길이):
    - insert: O(m)
    - search: O(m)
    - longest_prefix: O(m)

    공간복잡도:
    - 최악: O(총 문자 수)
    - 공통 prefix 공유로 실제로는 더 효율적
    """

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

        예: vocab = {"un", "una", "unable"}
            longest_prefix("unavailable") → "una"
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
        """
        text의 prefix 중 Trie에 있는 모든 것 반환 (길이순)

        예: vocab = {"un", "una", "unable"}
            all_prefixes("unable") → ["un", "una", "unable"]
        """
        node = self.root
        prefixes = []

        for char in text:
            if char not in node.children:
                break
            node = node.children[char]
            if node.is_end:
                prefixes.append(node.value)

        return prefixes

    def get_all_words(self) -> list[str]:
        """Trie에 저장된 모든 단어 반환 (DFS)"""
        words = []
        self._collect_words(self.root, words)
        return words

    def _collect_words(self, node: TrieNode, words: list[str]) -> None:
        """DFS로 모든 단어 수집"""
        if node.is_end:
            words.append(node.value)
        for child in node.children.values():
            self._collect_words(child, words)

    def visualize(self, max_depth: int = 5) -> str:
        """Trie 구조 시각화 (디버깅용)"""
        lines = ["(root)"]
        self._visualize_children(self.root, "", lines, 0, max_depth)
        return "\n".join(lines)

    def _visualize_children(self, node: TrieNode, prefix: str,
                            lines: list[str], depth: int, max_depth: int) -> None:
        """자식 노드들을 시각화"""
        if depth >= max_depth:
            if node.children:
                lines.append(f"{prefix}...")
            return

        children = list(node.children.items())
        for i, (char, child) in enumerate(children):
            is_last = (i == len(children) - 1)
            connector = "└── " if is_last else "├── "
            end_marker = "*" if child.is_end else ""

            lines.append(f"{prefix}{connector}{char}{end_marker}")

            # 자식의 prefix: 마지막이면 공백, 아니면 │
            child_prefix = prefix + ("    " if is_last else "│   ")
            self._visualize_children(child, child_prefix, lines, depth + 1, max_depth)


# ============================================================
# 데모 및 테스트
# ============================================================


def demo_basic_operations():
    """기본 연산 데모"""
    print("=" * 60)
    print("Trie 기본 연산 데모")
    print("=" * 60)

    trie = Trie()

    # Vocabulary 삽입
    vocab = ["un", "una", "unab", "unable", "unavailable", "under", "undo"]
    print(f"\nVocabulary: {vocab}")

    for word in vocab:
        trie.insert(word)

    # 구조 시각화
    print("\nTrie 구조:")
    print(trie.visualize())

    # 기본 검색 테스트
    print("\n--- 기본 검색 ---")
    test_searches = ["unable", "unab", "unava", "xyz"]
    for word in test_searches:
        result = trie.search(word)
        print(f"search('{word}'): {result}")

    # Prefix 존재 여부
    print("\n--- Prefix 존재 여부 ---")
    test_prefixes = ["un", "una", "xyz"]
    for prefix in test_prefixes:
        result = trie.starts_with(prefix)
        print(f"starts_with('{prefix}'): {result}")


def demo_longest_prefix():
    """Longest Prefix 데모 - 토크나이저 핵심 연산"""
    print("\n" + "=" * 60)
    print("Longest Prefix 데모 (토크나이저 핵심)")
    print("=" * 60)

    trie = Trie()
    vocab = ["un", "una", "unab", "unable", "unavailable", "under"]
    for word in vocab:
        trie.insert(word)

    print(f"\nVocabulary: {vocab}")
    print("\n--- Longest Prefix Match ---")

    test_cases = [
        "unavailable",    # unavailable (전체 매칭)
        "inability",      # None (매칭 없음)
        "undertake",      # under
        "unable",         # unable
        "una",            # una
        "universal",      # un
    ]

    for text in test_cases:
        result = trie.longest_prefix(text)
        print(f"longest_prefix('{text}'): {result}")

    # All prefixes
    print("\n--- All Prefixes ---")
    text = "unavailable"
    prefixes = trie.all_prefixes(text)
    print(f"all_prefixes('{text}'): {prefixes}")


def demo_tokenizer_simulation():
    """토크나이저 시뮬레이션"""
    print("\n" + "=" * 60)
    print("WordPiece 토크나이저 시뮬레이션")
    print("=" * 60)

    # 두 개의 Trie: 단어 시작용 / continuation용
    word_start_trie = Trie()
    continuation_trie = Trie()

    # 샘플 vocabulary
    word_start_vocab = ["un", "play", "the", "a", "is", "new", "low"]
    continuation_vocab = ["##able", "##avail", "##available", "##ing",
                          "##ed", "##er", "##s", "##est"]

    for word in word_start_vocab:
        word_start_trie.insert(word)
    for word in continuation_vocab:
        continuation_trie.insert(word)

    print(f"\nWord start vocab: {word_start_vocab}")
    print(f"Continuation vocab: {continuation_vocab}")

    def tokenize_word(word: str) -> list[str]:
        """단일 단어 토크나이징"""
        tokens = []
        start = 0

        while start < len(word):
            if start == 0:
                trie = word_start_trie
                substr = word
            else:
                trie = continuation_trie
                substr = "##" + word[start:]

            match = trie.longest_prefix(substr)

            if match is None:
                return ["[UNK]"]

            tokens.append(match)

            if start == 0:
                start += len(match)
            else:
                start += len(match) - 2  # "##" 길이 제외

        return tokens

    print("\n--- 토크나이징 결과 ---")
    test_words = ["unavailable", "playing", "player", "plays",
                  "newest", "lowest", "the", "unknown"]

    for word in test_words:
        tokens = tokenize_word(word)
        print(f"{word:15} → {tokens}")


if __name__ == "__main__":
    demo_basic_operations()
    demo_longest_prefix()
    demo_tokenizer_simulation()
