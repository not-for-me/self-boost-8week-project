"""
Suffix Array 구현
BPE 학습의 핵심 자료구조

실행: python suffix_array_implementation.py
"""

from __future__ import annotations
from collections import Counter


def build_suffix_array_naive(text: str) -> list[int]:
    """
    Suffix Array를 단순 정렬로 구축.
    
    시간복잡도: O(n² log n)
    - n개의 suffix 생성: O(n²) 공간
    - 정렬: O(n log n) 비교, 각 비교 O(n)
    
    교육용 구현. 실제로는 O(n) 알고리즘 사용 (SA-IS, DC3 등)
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
    
    핵심 아이디어:
    - rank[i]: suffix i의 SA에서의 위치
    - 만약 lcp[rank[i]] = k 이면, lcp[rank[i+1]] >= k-1
    - 즉, 한 칸 뒤로 가면 LCP가 최대 1만 감소
    """
    n = len(text)
    rank = [0] * n  # rank[i] = suffix i의 suffix array에서의 위치
    lcp = [0] * n
    
    # rank 배열 구축
    for i, suffix_idx in enumerate(suffix_array):
        rank[suffix_idx] = i
    
    k = 0  # 현재 LCP 길이
    for i in range(n):
        if rank[i] == 0:
            k = 0
            continue
        
        j = suffix_array[rank[i] - 1]  # SA에서 바로 앞 suffix의 시작 인덱스
        
        # 공통 prefix 계산
        while i + k < n and j + k < n and text[i + k] == text[j + k]:
            k += 1
        
        lcp[rank[i]] = k
        
        # 다음 반복을 위해 k 감소 (최대 1만큼)
        if k > 0:
            k -= 1
    
    return lcp


def find_repeated_substrings(text: str, min_length: int = 2) -> dict[str, int]:
    """
    Suffix Array + LCP를 활용한 반복 substring 탐지.
    BPE 학습의 기초가 되는 연산.

    원리:
    - SA가 정렬되어 있으므로, 같은 prefix를 가진 suffix들이 인접
    - LCP[i]가 k이면, SA[i-1]과 SA[i]가 길이 k의 공통 prefix 공유
    - 연속으로 LCP >= k인 구간의 길이 + 1 = 해당 prefix의 출현 횟수

    반환값: {substring: 출현 횟수} (2회 이상 등장하는 것만)
    """
    sa = build_suffix_array_naive(text)
    lcp = build_lcp_array(text, sa)
    n = len(text)

    repeated: dict[str, int] = {}

    # 각 길이별로 연속 구간을 찾아 카운트
    for length in range(min_length, n):
        i = 1
        while i < n:
            if lcp[i] >= length:
                # LCP >= length인 연속 구간의 시작
                # 이 구간에 속한 suffix들은 모두 같은 length-prefix를 공유
                start = i - 1  # 구간 시작 (이전 suffix 포함)
                while i < n and lcp[i] >= length:
                    i += 1
                end = i - 1  # 구간 끝

                count = end - start + 1  # 구간 내 suffix 수 = 출현 횟수
                substr = text[sa[start]:sa[start] + length]

                # 더 긴 substring으로 이미 카운트된 경우 스킵
                if substr not in repeated:
                    repeated[substr] = count
            else:
                i += 1

    # 빈도 기준 정렬
    return dict(sorted(repeated.items(), key=lambda x: (-x[1], -len(x[0]))))


def find_most_frequent_bigram(text: str) -> tuple[str, int] | None:
    """
    가장 빈번한 bigram (2글자 쌍) 찾기.
    BPE의 각 iteration에서 수행하는 연산.
    """
    if len(text) < 2:
        return None
    
    bigrams = Counter()
    for i in range(len(text) - 1):
        bigram = text[i:i + 2]
        if ' ' not in bigram:  # 공백 제외
            bigrams[bigram] += 1
    
    if not bigrams:
        return None
    
    return bigrams.most_common(1)[0]


def longest_repeated_substring(text: str) -> str:
    """
    가장 긴 반복 부분문자열 찾기.
    LCP array의 최대값 위치에서 해당 substring 추출.
    """
    if len(text) < 2:
        return ""
    
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


def demo_suffix_array_basics():
    """Suffix Array 기본 데모"""
    print("=" * 60)
    print("Suffix Array 기본 개념")
    print("=" * 60)
    
    text = "banana$"
    
    print(f"\nText: '{text}'")
    print(f"Length: {len(text)}")
    
    # 모든 suffix 보여주기
    print("\n--- 모든 Suffix (정렬 전) ---")
    for i in range(len(text)):
        print(f"  {i}: {text[i:]}")
    
    # Suffix Array 구축
    sa = build_suffix_array_naive(text)
    print(f"\n--- Suffix Array ---")
    print(f"SA = {sa}")
    
    print("\n--- 정렬된 Suffix ---")
    for i, idx in enumerate(sa):
        print(f"  SA[{i}] = {idx}: '{text[idx:]}'")
    
    # LCP Array
    lcp = build_lcp_array(text, sa)
    print(f"\n--- LCP Array ---")
    print(f"LCP = {lcp}")
    
    print("\n--- LCP 의미 ---")
    for i in range(1, len(sa)):
        common = text[sa[i]:sa[i] + lcp[i]] if lcp[i] > 0 else "(없음)"
        print(f"  LCP[{i}] = {lcp[i]}: '{text[sa[i-1]:]}' 와 '{text[sa[i]:]}' "
              f"의 공통 prefix = '{common}'")


def demo_repeated_substrings():
    """반복 Substring 탐지 데모"""
    print("\n" + "=" * 60)
    print("반복 Substring 탐지 (BPE 기초)")
    print("=" * 60)
    
    text = "abracadabra"
    print(f"\nText: '{text}'")
    
    # 반복 substring 찾기
    repeated = find_repeated_substrings(text, min_length=2)

    print("\n--- 반복되는 Substring (길이 >= 2) ---")
    for substr, count in list(repeated.items())[:10]:
        print(f"  '{substr}': {count}회 등장")
    
    # 가장 긴 반복 substring
    lrs = longest_repeated_substring(text)
    print(f"\n--- 가장 긴 반복 Substring ---")
    print(f"  '{lrs}' (길이: {len(lrs)})")


def demo_bpe_simulation():
    """BPE 학습 시뮬레이션 (단순화된 버전)"""
    print("\n" + "=" * 60)
    print("BPE 학습 시뮬레이션")
    print("=" * 60)

    # 코퍼스를 문자 리스트로 표현 (단어 경계는 _로 표시)
    words = ["l o w _", "l o w e r _", "l o w e s t _",
             "n e w _", "n e w e r _", "n e w e s t _"]
    corpus = [word.split() for word in words]

    print(f"\n초기 코퍼스:")
    for word in corpus:
        print(f"  {word}")

    vocab = set(char for word in corpus for char in word)
    print(f"\n초기 vocabulary: {vocab}")

    merges = []

    print("\n--- BPE Merge 과정 ---")
    for i in range(10):
        # 가장 빈번한 bigram 찾기
        pairs = {}
        for word in corpus:
            for j in range(len(word) - 1):
                pair = (word[j], word[j + 1])
                pairs[pair] = pairs.get(pair, 0) + 1

        if not pairs:
            break

        best_pair = max(pairs, key=pairs.get)
        count = pairs[best_pair]

        if count < 2:
            break

        print(f"Step {i + 1}: '{best_pair[0]}' + '{best_pair[1]}' → "
              f"'{best_pair[0] + best_pair[1]}' (빈도: {count})")

        merges.append(best_pair)

        # 코퍼스에 병합 적용
        new_corpus = []
        for word in corpus:
            new_word = []
            j = 0
            while j < len(word):
                if (j < len(word) - 1 and
                    word[j] == best_pair[0] and
                    word[j + 1] == best_pair[1]):
                    new_word.append(best_pair[0] + best_pair[1])
                    j += 2
                else:
                    new_word.append(word[j])
                    j += 1
            new_corpus.append(new_word)
        corpus = new_corpus

    print(f"\n최종 코퍼스:")
    for word in corpus:
        print(f"  {word}")

    print(f"\n학습된 Merge 규칙:")
    for i, (a, b) in enumerate(merges):
        print(f"  {i + 1}. '{a}' + '{b}' → '{a + b}'")


class SimpleBPETrainer:
    """
    단순화된 BPE 학습기
    Suffix Array를 활용한 빈번한 쌍 탐지
    """
    
    def __init__(self):
        self.merges: list[tuple[str, str]] = []
        self.vocab: set[str] = set()
    
    def train(self, corpus: list[str], num_merges: int = 10) -> None:
        """
        BPE 학습
        
        1. 단어를 문자 시퀀스로 변환 (</w>로 단어 끝 표시)
        2. 가장 빈번한 쌍을 찾아 병합
        3. num_merges 횟수만큼 반복
        """
        # 단어 → 문자 리스트 변환
        words: list[list[str]] = []
        word_freq: dict[tuple[str, ...], int] = {}
        
        for text in corpus:
            for word in text.split():
                word_tuple = tuple(list(word) + ['</w>'])
                word_freq[word_tuple] = word_freq.get(word_tuple, 0) + 1
        
        # 초기 vocabulary
        self.vocab = set()
        for word_tuple in word_freq:
            for char in word_tuple:
                self.vocab.add(char)
        
        print(f"초기 vocabulary 크기: {len(self.vocab)}")
        print(f"고유 단어 수: {len(word_freq)}")
        
        for i in range(num_merges):
            # 모든 인접 쌍의 빈도 계산
            pairs = Counter()
            for word_tuple, freq in word_freq.items():
                for j in range(len(word_tuple) - 1):
                    pair = (word_tuple[j], word_tuple[j + 1])
                    pairs[pair] += freq
            
            if not pairs:
                break
            
            # 가장 빈번한 쌍
            best_pair = pairs.most_common(1)[0]
            pair, count = best_pair
            
            if count < 2:
                break
            
            print(f"Merge {i + 1}: {pair[0]} + {pair[1]} → "
                  f"{pair[0] + pair[1]} (빈도: {count})")
            
            # 병합 기록
            self.merges.append(pair)
            new_token = pair[0] + pair[1]
            self.vocab.add(new_token)
            
            # 모든 단어에 병합 적용
            new_word_freq = {}
            for word_tuple, freq in word_freq.items():
                new_word = self._apply_merge(list(word_tuple), pair)
                new_word_freq[tuple(new_word)] = freq
            word_freq = new_word_freq
        
        print(f"\n최종 vocabulary 크기: {len(self.vocab)}")
    
    def _apply_merge(self, word: list[str], pair: tuple[str, str]) -> list[str]:
        """단어에 병합 규칙 적용"""
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
        return new_word
    
    def tokenize(self, word: str) -> list[str]:
        """학습된 BPE로 단어 토크나이징"""
        tokens = list(word) + ['</w>']
        
        for pair in self.merges:
            tokens = self._apply_merge(tokens, pair)
        
        return tokens


def demo_bpe_trainer():
    """BPE Trainer 데모"""
    print("\n" + "=" * 60)
    print("BPE Trainer 실전 데모")
    print("=" * 60)
    
    corpus = [
        "low lower lowest",
        "new newer newest", 
        "show showed showing",
        "low low low",
        "new new",
    ]
    
    print("\n학습 코퍼스:")
    for text in corpus:
        print(f"  '{text}'")
    
    print("\n--- BPE 학습 ---")
    trainer = SimpleBPETrainer()
    trainer.train(corpus, num_merges=15)
    
    print("\n--- 토크나이징 테스트 ---")
    test_words = ["lower", "newer", "lowest", "newest", "showed", "unknown"]
    for word in test_words:
        tokens = trainer.tokenize(word)
        print(f"  {word:12} → {tokens}")


if __name__ == "__main__":
    demo_suffix_array_basics()
    demo_repeated_substrings()
    demo_bpe_simulation()
    demo_bpe_trainer()
