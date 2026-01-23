# "Expand from Center" 패턴의 일반화

이 문서는 LeetCode의 [Longest Palindromic Substring](https://leetcode.com/problems/longest-palindromic-substring/) 문제에서 사용한 접근법을 일반화하여 정리한 내용입니다.

## 원본 문제 풀이

```python
class Solution(object):
    def longestPalindrome(self, s):
        """
        :type s: str
        :rtype: str
        """
        if len(s) < 2 or s == s[::-1]:
            return s

        def expand(left, right):
            while -1 < left and right < len(s) and s[left] == s[right]:
                left -= 1
                right += 1

            return s[left+1 : right]

        result = ''
        for i in range(len(s)):
            result = max(result, expand(i, i+1), expand(i,i+2), key=len)
        return result
```

---

## 핵심 패턴: Seed and Expand

이 문제에서 사용한 접근법은 **"Seed and Expand"** 또는 **"Center Expansion"** 패턴이라고 불립니다.

### 핵심 아이디어

```
1. 최소 조건(seed)을 만족하는 지점을 찾는다
2. 해당 지점에서 양방향으로 확장하며 조건 유지 여부 확인
3. 조건이 깨지면 멈추고 결과 반환
```

이 패턴은 **O(n²) → O(n) 또는 O(n log n)** 최적화가 가능한 경우가 많습니다.

---

## 관련 알고리즘 및 응용

### 1. Manacher's Algorithm (O(n) Palindrome)

Center Expansion을 최적화한 알고리즘으로, 이전에 계산한 palindrome 정보를 재활용합니다.

```python
def manacher(s):
    # 문자 사이에 '#' 삽입하여 홀수/짝수 케이스 통합
    t = '#' + '#'.join(s) + '#'
    n = len(t)
    p = [0] * n  # p[i] = i 중심 palindrome 반지름
    center = right = 0

    for i in range(n):
        if i < right:
            mirror = 2 * center - i
            p[i] = min(right - i, p[mirror])  # 이전 정보 활용

        # expand from center
        while (i - p[i] - 1 >= 0 and
               i + p[i] + 1 < n and
               t[i - p[i] - 1] == t[i + p[i] + 1]):
            p[i] += 1

        if i + p[i] > right:
            center, right = i, i + p[i]

    max_len = max(p)
    center_idx = p.index(max_len)
    start = (center_idx - max_len) // 2
    return s[start:start + max_len]
```

**AI/ML 관점**: 이전 계산 결과를 캐싱하여 중복 연산 제거 → **Dynamic Programming의 핵심 아이디어**

---

### 2. Two Pointer / Sliding Window 패턴

Expand 패턴의 변형으로, 다양한 문자열/배열 문제에 적용됩니다.

| 문제 유형 | Seed 조건 | Expand 조건 |
|----------|----------|-------------|
| Longest Palindrome | s[i] == s[i+1] | s[left] == s[right] |
| Longest Substring Without Repeating | 단일 문자 | 중복 없음 |
| Minimum Window Substring | 필수 문자 포함 | 최소화 |
| Container With Most Water | 양 끝 포인터 | 높이 비교하며 축소 |

---

### 3. AI/ML 데이터 처리에서의 응용

#### (a) Sequence Labeling에서 Entity Boundary Detection

```python
def expand_entity(tokens, probs, center_idx, threshold=0.5):
    """NER에서 entity boundary 확장"""
    left = right = center_idx

    # seed: 확률이 threshold 이상인 토큰
    if probs[center_idx] < threshold:
        return None

    # expand left
    while left > 0 and probs[left - 1] >= threshold:
        left -= 1

    # expand right
    while right < len(tokens) - 1 and probs[right + 1] >= threshold:
        right += 1

    return tokens[left:right + 1]
```

#### (b) Time Series Anomaly Detection

```python
def find_anomaly_window(data, scores, threshold):
    """이상 점수가 높은 구간 확장"""
    windows = []
    i = 0
    while i < len(data):
        if scores[i] > threshold:  # seed 발견
            left = right = i
            # expand
            while left > 0 and scores[left-1] > threshold * 0.8:
                left -= 1
            while right < len(data)-1 and scores[right+1] > threshold * 0.8:
                right += 1
            windows.append((left, right))
            i = right + 1
        else:
            i += 1
    return windows
```

#### (c) Text Segmentation / Chunking

LLM을 위한 문서 청킹에서도 비슷한 패턴이 사용됩니다:

```python
def semantic_chunking(sentences, embeddings, similarity_threshold=0.7):
    """의미적으로 유사한 문장들을 하나의 청크로 묶기"""
    chunks = []
    i = 0

    while i < len(sentences):
        chunk_start = i
        chunk_end = i

        # expand: 다음 문장과 유사도가 높으면 확장
        while chunk_end < len(sentences) - 1:
            sim = cosine_similarity(
                embeddings[chunk_end],
                embeddings[chunk_end + 1]
            )
            if sim >= similarity_threshold:
                chunk_end += 1
            else:
                break

        chunks.append(sentences[chunk_start:chunk_end + 1])
        i = chunk_end + 1

    return chunks
```

---

### 4. 일반화된 패턴 템플릿

```python
def seed_and_expand(data, is_seed, can_expand, extract_result):
    """
    범용 Seed-and-Expand 패턴

    Args:
        data: 입력 데이터
        is_seed: (index) -> bool, seed 조건 체크
        can_expand: (left, right) -> bool, 확장 가능 여부
        extract_result: (left, right) -> result, 결과 추출
    """
    results = []

    for i in range(len(data)):
        if not is_seed(i):
            continue

        left, right = i, i

        # expand left
        while left > 0 and can_expand(left - 1, right):
            left -= 1

        # expand right
        while right < len(data) - 1 and can_expand(left, right + 1):
            right += 1

        results.append(extract_result(left, right))

    return results
```

---

## 심화 학습 추천

1. **Suffix Array + LCP Array**: O(n log n)에 모든 palindrome 찾기
2. **Z-Algorithm**: 패턴 매칭의 또 다른 linear-time 접근
3. **Rolling Hash (Rabin-Karp)**: 문자열 비교를 O(1)로 최적화
4. **KMP Algorithm**: prefix function을 이용한 패턴 매칭

이 패턴들은 모두 **"이전 계산 결과를 활용한 점진적 확장"**이라는 공통된 철학을 공유합니다. ML 파이프라인에서 데이터 전처리, 시퀀스 분석, 청킹 등에 직접 적용할 수 있습니다.

---

## 참고 자료

- [LeetCode - Longest Palindromic Substring](https://leetcode.com/problems/longest-palindromic-substring/)
- Manacher's Algorithm - Wikipedia
- Two Pointers Technique - GeeksforGeeks
