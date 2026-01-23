"""
MinHash & LSH (Locality-Sensitive Hashing) 구현
대규모 문서의 Near-Duplicate Detection을 위한 알고리즘

실행: python minhash.py
"""

from __future__ import annotations

import hashlib
import random
import re
from collections import defaultdict
from typing import Dict, List, Set, Tuple


class MinHash:
    """
    MinHash Signature 생성기

    Jaccard 유사도를 보존하는 고정 크기 signature를 생성합니다.

    Parameters:
        num_perm: 순열(해시 함수) 개수 = signature 크기
        seed: 랜덤 시드 (재현성용)
    """

    def __init__(self, num_perm: int = 128, seed: int = 42):
        self.num_perm = num_perm
        self.seed = seed
        self._init_hash_params()

    def _init_hash_params(self):
        """해시 함수 파라미터 초기화 (ax + b mod p 형태)"""
        random.seed(self.seed)

        # Mersenne prime (2^61 - 1)
        self._prime = (1 << 61) - 1
        self._max_hash = (1 << 32) - 1

        # 랜덤 a, b 생성 (각 해시 함수마다 다른 값)
        self._a = [random.randint(1, self._prime - 1)
                   for _ in range(self.num_perm)]
        self._b = [random.randint(0, self._prime - 1)
                   for _ in range(self.num_perm)]

    def _hash_value(self, value: int, i: int) -> int:
        """i번째 해시 함수 적용"""
        return ((self._a[i] * value + self._b[i]) % self._prime) & self._max_hash

    def _shingle_to_int(self, shingle: str) -> int:
        """shingle을 정수로 변환"""
        return int(hashlib.sha1(shingle.encode("utf-8")).hexdigest()[:16], 16)

    def signature(self, shingles: Set[str]) -> List[int]:
        """
        집합에서 MinHash signature 생성

        Args:
            shingles: 문서의 shingle 집합

        Returns:
            길이 num_perm의 signature 벡터
        """
        if not shingles:
            return [self._max_hash] * self.num_perm

        # 모든 shingle을 정수로 변환
        hashed_shingles = [self._shingle_to_int(s) for s in shingles]

        # 각 해시 함수에 대해 최소값 계산
        signature = []
        for i in range(self.num_perm):
            min_hash = min(self._hash_value(h, i) for h in hashed_shingles)
            signature.append(min_hash)

        return signature

    @staticmethod
    def similarity(sig1: List[int], sig2: List[int]) -> float:
        """
        두 signature 간 추정 Jaccard 유사도

        Args:
            sig1, sig2: MinHash signatures

        Returns:
            추정 Jaccard 유사도 (0.0 ~ 1.0)
        """
        if len(sig1) != len(sig2):
            raise ValueError("Signatures must have the same length")

        matches = sum(1 for a, b in zip(sig1, sig2) if a == b)
        return matches / len(sig1)


class LSHIndex:
    """
    LSH (Locality-Sensitive Hashing) 인덱스

    MinHash signature를 기반으로 유사한 문서를 빠르게 검색합니다.

    Parameters:
        num_perm: MinHash signature 크기
        num_bands: band 개수 (num_perm을 나눌 수 있어야 함)
        seed: MinHash 랜덤 시드
    """

    def __init__(self, num_perm: int = 128, num_bands: int = 16, seed: int = 42):
        if num_perm % num_bands != 0:
            raise ValueError(
                f"num_perm ({num_perm}) must be divisible by num_bands ({num_bands})"
            )

        self.num_perm = num_perm
        self.num_bands = num_bands
        self.rows_per_band = num_perm // num_bands

        self.minhash = MinHash(num_perm, seed)

        # 각 band별 bucket (hash -> doc_id 리스트)
        self.buckets: List[Dict[int, List[str]]] = [
            defaultdict(list) for _ in range(num_bands)
        ]

        # 문서별 signature 저장
        self.signatures: Dict[str, List[int]] = {}

    @property
    def threshold(self) -> float:
        """대략적인 similarity threshold"""
        return (1 / self.num_bands) ** (1 / self.rows_per_band)

    def _band_hash(self, band: List[int]) -> int:
        """band를 단일 해시값으로 변환"""
        return hash(tuple(band))

    def add(self, doc_id: str, shingles: Set[str]) -> None:
        """
        문서를 인덱스에 추가

        Args:
            doc_id: 문서 식별자
            shingles: 문서의 shingle 집합
        """
        if doc_id in self.signatures:
            return  # 이미 추가된 문서

        sig = self.minhash.signature(shingles)
        self.signatures[doc_id] = sig

        # 각 band를 해당 bucket에 추가
        for b in range(self.num_bands):
            start = b * self.rows_per_band
            end = start + self.rows_per_band
            band = sig[start:end]
            band_hash = self._band_hash(band)
            self.buckets[b][band_hash].append(doc_id)

    def query(self, shingles: Set[str], top_k: int | None = None) -> List[Tuple[str, float]]:
        """
        유사한 문서 검색

        Args:
            shingles: 쿼리 문서의 shingle 집합
            top_k: 상위 k개만 반환 (None이면 전체)

        Returns:
            (doc_id, estimated_similarity) 리스트 (유사도 내림차순)
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

        results.sort(key=lambda x: -x[1])

        if top_k is not None:
            results = results[:top_k]

        return results

    def find_similar_pairs(self, threshold: float | None = None) -> List[Tuple[str, str, float]]:
        """
        인덱스 내 유사한 문서 쌍 찾기

        Args:
            threshold: 유사도 임계값 (None이면 self.threshold 사용)

        Returns:
            (doc_id1, doc_id2, similarity) 리스트 (유사도 내림차순)
        """
        if threshold is None:
            threshold = self.threshold

        # 후보 쌍 수집 (같은 bucket에 있는 문서들)
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

        results.sort(key=lambda x: -x[2])
        return results

    def stats(self) -> dict:
        """인덱스 통계"""
        total_buckets = sum(len(b) for b in self.buckets)
        non_empty_buckets = sum(1 for b in self.buckets for v in b.values() if v)

        return {
            "num_documents": len(self.signatures),
            "num_perm": self.num_perm,
            "num_bands": self.num_bands,
            "rows_per_band": self.rows_per_band,
            "threshold": self.threshold,
            "total_buckets": total_buckets,
            "avg_bucket_size": len(self.signatures) / max(1, non_empty_buckets),
        }


# ============================================================
# 유틸리티 함수
# ============================================================


def create_shingles(text: str, k: int = 5) -> Set[str]:
    """
    텍스트에서 k-gram shingle 집합 생성

    Args:
        text: 입력 텍스트
        k: shingle 크기 (영문 5~10, 한글 3~5 권장)

    Returns:
        shingle 집합
    """
    text = text.lower().strip()
    if len(text) < k:
        return {text} if text else set()
    return {text[i:i + k] for i in range(len(text) - k + 1)}


def create_word_shingles(text: str, k: int = 3) -> Set[str]:
    """
    단어 기반 k-gram shingle 생성

    Args:
        text: 입력 텍스트
        k: 단어 shingle 크기

    Returns:
        shingle 집합 (단어 튜플의 문자열 표현)
    """
    words = text.lower().split()
    if len(words) < k:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i:i + k]) for i in range(len(words) - k + 1)}


def preprocess_text(text: str) -> str:
    """MinHash용 텍스트 전처리"""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)  # 연속 공백 제거
    text = re.sub(r"[^\w\s]", "", text)  # 특수문자 제거
    return text.strip()


def jaccard_similarity(set1: Set, set2: Set) -> float:
    """실제 Jaccard 유사도 계산 (검증용)"""
    if not set1 and not set2:
        return 1.0
    if not set1 or not set2:
        return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union


# ============================================================
# 데모 및 테스트
# ============================================================


def demo_minhash_basics():
    """MinHash 기본 개념 데모"""
    print("=" * 60)
    print("MinHash 기본 개념")
    print("=" * 60)

    mh = MinHash(num_perm=128)

    # 두 유사한 문서
    doc1 = "오늘 날씨가 매우 맑고 화창합니다. 기온은 25도입니다."
    doc2 = "오늘 날씨가 매우 맑고 화창합니다. 기온은 26도입니다."
    doc3 = "내일은 비가 올 예정입니다. 우산을 챙기세요."

    # Shingle 생성
    shingles1 = create_shingles(doc1, k=3)
    shingles2 = create_shingles(doc2, k=3)
    shingles3 = create_shingles(doc3, k=3)

    print(f"\n문서 1: {doc1}")
    print(f"문서 2: {doc2}")
    print(f"문서 3: {doc3}")

    print(f"\n--- Shingle 예시 (k=3) ---")
    print(f"문서 1 shingle 수: {len(shingles1)}")
    print(f"예시: {list(shingles1)[:5]}")

    # 실제 Jaccard 유사도
    print(f"\n--- 실제 Jaccard 유사도 ---")
    real_sim_12 = jaccard_similarity(shingles1, shingles2)
    real_sim_13 = jaccard_similarity(shingles1, shingles3)
    print(f"문서 1 vs 2: {real_sim_12:.4f}")
    print(f"문서 1 vs 3: {real_sim_13:.4f}")

    # MinHash signature
    sig1 = mh.signature(shingles1)
    sig2 = mh.signature(shingles2)
    sig3 = mh.signature(shingles3)

    print(f"\n--- MinHash Signature (처음 10개) ---")
    print(f"문서 1: {sig1[:10]}")
    print(f"문서 2: {sig2[:10]}")

    # 추정 유사도
    print(f"\n--- 추정 Jaccard 유사도 (MinHash) ---")
    est_sim_12 = MinHash.similarity(sig1, sig2)
    est_sim_13 = MinHash.similarity(sig1, sig3)
    print(f"문서 1 vs 2: {est_sim_12:.4f} (실제: {real_sim_12:.4f})")
    print(f"문서 1 vs 3: {est_sim_13:.4f} (실제: {real_sim_13:.4f})")


def demo_lsh_index():
    """LSH 인덱스 데모"""
    print("\n" + "=" * 60)
    print("LSH Index 데모")
    print("=" * 60)

    # 인덱스 생성
    lsh = LSHIndex(num_perm=128, num_bands=16)

    print(f"\n설정:")
    print(f"  Signature 크기: {lsh.num_perm}")
    print(f"  Band 수: {lsh.num_bands}")
    print(f"  Rows per band: {lsh.rows_per_band}")
    print(f"  Threshold: {lsh.threshold:.3f}")

    # 문서 추가
    documents = {
        "doc1": "인공지능은 현대 기술의 핵심입니다. 머신러닝과 딥러닝이 발전하고 있습니다.",
        "doc2": "인공지능은 현대 기술의 핵심입니다. 머신러닝과 딥러닝이 크게 발전하고 있습니다.",
        "doc3": "오늘 주식 시장은 상승세를 보였습니다. 코스피 지수가 올랐습니다.",
        "doc4": "오늘 주식 시장은 상승세를 보였습니다. 코스피 지수가 크게 올랐습니다.",
        "doc5": "날씨가 맑아서 산책하기 좋은 날입니다.",
    }

    print(f"\n--- 문서 추가 ---")
    for doc_id, content in documents.items():
        shingles = create_shingles(preprocess_text(content), k=3)
        lsh.add(doc_id, shingles)
        print(f"  {doc_id}: {content[:30]}...")

    print(f"\n인덱스 통계: {lsh.stats()}")

    # 유사 쌍 찾기
    print(f"\n--- 유사한 문서 쌍 (threshold >= {lsh.threshold:.2f}) ---")
    pairs = lsh.find_similar_pairs()
    for doc1, doc2, sim in pairs:
        print(f"  {doc1} <-> {doc2}: {sim:.4f}")

    # 쿼리 검색
    print(f"\n--- 쿼리 검색 ---")
    query = "인공지능 기술이 발전하고 있습니다."
    query_shingles = create_shingles(preprocess_text(query), k=3)
    results = lsh.query(query_shingles, top_k=3)

    print(f"쿼리: {query}")
    print("유사 문서:")
    for doc_id, sim in results:
        print(f"  {doc_id}: {sim:.4f} - {documents[doc_id][:40]}...")


def demo_document_deduplication():
    """문서 중복 제거 데모"""
    print("\n" + "=" * 60)
    print("문서 중복 제거 시뮬레이션")
    print("=" * 60)

    # 크롤링된 문서 시뮬레이션 (일부 중복/유사)
    crawled_docs = [
        {"id": "1", "content": "파이썬은 배우기 쉬운 프로그래밍 언어입니다."},
        {"id": "2", "content": "자바스크립트로 웹 개발을 할 수 있습니다."},
        {"id": "3", "content": "파이썬은 배우기 쉬운 프로그래밍 언어입니다."},  # 완전 중복
        {"id": "4", "content": "파이썬은 배우기 매우 쉬운 프로그래밍 언어입니다."},  # 유사
        {"id": "5", "content": "머신러닝은 데이터에서 패턴을 학습합니다."},
        {"id": "6", "content": "자바스크립트로 웹 개발을 쉽게 할 수 있습니다."},  # 유사
        {"id": "7", "content": "딥러닝은 머신러닝의 한 분야입니다."},
        {"id": "8", "content": "머신러닝은 데이터에서 패턴을 학습합니다."},  # 완전 중복
    ]

    print(f"\n크롤링된 문서: {len(crawled_docs)}개")

    # 중복 제거
    lsh = LSHIndex(num_perm=128, num_bands=16)
    unique_docs = []
    duplicates = []

    for doc in crawled_docs:
        shingles = create_shingles(preprocess_text(doc["content"]), k=3)

        # 유사 문서 검색
        candidates = lsh.query(shingles)
        is_duplicate = any(sim >= 0.7 for _, sim in candidates)

        if is_duplicate:
            duplicates.append((doc["id"], candidates[0] if candidates else None))
        else:
            lsh.add(doc["id"], shingles)
            unique_docs.append(doc)

    print(f"\n--- 결과 ---")
    print(f"고유 문서: {len(unique_docs)}개")
    print(f"중복/유사 문서: {len(duplicates)}개")

    print(f"\n고유 문서:")
    for doc in unique_docs:
        print(f"  [{doc['id']}] {doc['content']}")

    print(f"\n중복으로 제거된 문서:")
    for doc_id, match in duplicates:
        match_info = f"(유사: {match[0]}, {match[1]:.2f})" if match else ""
        doc_content = next(d["content"] for d in crawled_docs if d["id"] == doc_id)
        print(f"  [{doc_id}] {doc_content} {match_info}")


def demo_accuracy_by_signature_size():
    """Signature 크기에 따른 정확도"""
    print("\n" + "=" * 60)
    print("Signature 크기에 따른 정확도")
    print("=" * 60)

    doc1 = "인공지능과 머신러닝 기술이 빠르게 발전하고 있습니다. 다양한 산업에 적용되고 있습니다."
    doc2 = "인공지능과 머신러닝 기술이 빠르게 발전하고 있습니다. 여러 산업에 적용되고 있습니다."

    shingles1 = create_shingles(doc1, k=3)
    shingles2 = create_shingles(doc2, k=3)

    real_jaccard = jaccard_similarity(shingles1, shingles2)
    print(f"\n실제 Jaccard 유사도: {real_jaccard:.4f}")

    print(f"\n{'Signature 크기':<15} {'추정 유사도':<15} {'오차':<10}")
    print("-" * 40)

    for num_perm in [16, 32, 64, 128, 256, 512]:
        errors = []
        for trial in range(10):  # 여러 번 시도
            mh = MinHash(num_perm=num_perm, seed=trial)
            sig1 = mh.signature(shingles1)
            sig2 = mh.signature(shingles2)
            est = MinHash.similarity(sig1, sig2)
            errors.append(abs(est - real_jaccard))

        avg_error = sum(errors) / len(errors)
        est_avg = real_jaccard + (sum(e * (1 if i % 2 == 0 else -1)
                                      for i, e in enumerate(errors)) / len(errors))

        print(f"{num_perm:<15} {est_avg:.4f}{'':>10} ±{avg_error:.4f}")


def demo_large_scale():
    """대규모 시뮬레이션"""
    print("\n" + "=" * 60)
    print("대규모 시뮬레이션")
    print("=" * 60)

    import time

    # 문서 생성
    n_docs = 10000
    print(f"\n{n_docs:,}개 문서 생성 중...")

    random.seed(42)
    base_texts = [
        "인공지능 기술이 발전하고 있습니다",
        "데이터 분석은 중요한 업무입니다",
        "파이썬은 프로그래밍 언어입니다",
        "머신러닝 모델을 학습합니다",
        "딥러닝은 신경망 기반입니다",
    ]

    documents = []
    for i in range(n_docs):
        base = random.choice(base_texts)
        # 약간의 변형 추가
        if random.random() < 0.1:
            base = base + " 추가 내용입니다."
        documents.append({"id": str(i), "content": base + f" 문서 {i}"})

    # 인덱스 구축
    lsh = LSHIndex(num_perm=128, num_bands=16)

    print(f"\n인덱스 구축 중...")
    start = time.perf_counter()

    for doc in documents:
        shingles = create_shingles(doc["content"], k=3)
        lsh.add(doc["id"], shingles)

    build_time = time.perf_counter() - start
    print(f"구축 시간: {build_time:.2f}초 ({n_docs / build_time:,.0f} docs/sec)")

    # 유사 쌍 찾기
    print(f"\n유사 쌍 검색 중...")
    start = time.perf_counter()
    pairs = lsh.find_similar_pairs(threshold=0.5)
    search_time = time.perf_counter() - start

    print(f"검색 시간: {search_time:.2f}초")
    print(f"발견된 유사 쌍: {len(pairs):,}개")

    print(f"\n상위 10개 유사 쌍:")
    for doc1, doc2, sim in pairs[:10]:
        print(f"  {doc1} <-> {doc2}: {sim:.3f}")


if __name__ == "__main__":
    demo_minhash_basics()
    demo_lsh_index()
    demo_document_deduplication()
    demo_accuracy_by_signature_size()
    demo_large_scale()
