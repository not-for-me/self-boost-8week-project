"""
Bloom Filter 구현
대규모 데이터의 멤버십 테스트를 위한 확률적 자료구조

실행: python bloom_filter.py
"""

from __future__ import annotations

import hashlib
import math
from typing import Any, Iterator


class BloomFilter:
    """
    Bloom Filter 구현

    특성:
    - False Positive: 있다고 했는데 없을 수 있음 (확률 조절 가능)
    - False Negative: 절대 없음 (없다고 하면 확실히 없음)

    Parameters:
        expected_items: 예상 삽입 원소 수
        false_positive_rate: 목표 False Positive Rate (기본: 1%)
    """

    def __init__(self, expected_items: int, false_positive_rate: float = 0.01):
        if expected_items <= 0:
            raise ValueError("expected_items must be positive")
        if not 0 < false_positive_rate < 1:
            raise ValueError("false_positive_rate must be between 0 and 1")

        self.expected_items = expected_items
        self.target_fpr = false_positive_rate

        # 최적 파라미터 계산
        self.size = self._optimal_size(expected_items, false_positive_rate)
        self.num_hashes = self._optimal_hashes(self.size, expected_items)

        # 비트 배열 (bytearray로 메모리 효율적 구현)
        self._bit_array = bytearray((self.size + 7) // 8)
        self.count = 0

    @staticmethod
    def _optimal_size(n: int, p: float) -> int:
        """
        목표 FPR을 위한 최적 비트 배열 크기

        m = -n * ln(p) / (ln(2))^2
        """
        m = -n * math.log(p) / (math.log(2) ** 2)
        return int(m) + 1

    @staticmethod
    def _optimal_hashes(m: int, n: int) -> int:
        """
        최적 해시 함수 개수

        k = (m/n) * ln(2)
        """
        k = (m / n) * math.log(2)
        return max(1, int(k))

    def _hash(self, item: Any, seed: int) -> int:
        """
        시드 기반 해시 함수

        MD5를 사용하여 다양한 해시값 생성
        """
        data = f"{seed}:{item}".encode("utf-8")
        h = hashlib.md5(data).hexdigest()
        return int(h, 16) % self.size

    def _get_bit(self, index: int) -> bool:
        """비트 배열에서 특정 비트 조회"""
        byte_index = index // 8
        bit_index = index % 8
        return bool(self._bit_array[byte_index] & (1 << bit_index))

    def _set_bit(self, index: int) -> None:
        """비트 배열에서 특정 비트 설정"""
        byte_index = index // 8
        bit_index = index % 8
        self._bit_array[byte_index] |= 1 << bit_index

    def add(self, item: Any) -> None:
        """원소 추가"""
        for seed in range(self.num_hashes):
            index = self._hash(item, seed)
            self._set_bit(index)
        self.count += 1

    def contains(self, item: Any) -> bool:
        """
        원소 존재 여부 확인

        Returns:
            True: 아마 있음 (False Positive 가능)
            False: 확실히 없음
        """
        for seed in range(self.num_hashes):
            index = self._hash(item, seed)
            if not self._get_bit(index):
                return False
        return True

    def __contains__(self, item: Any) -> bool:
        """'in' 연산자 지원"""
        return self.contains(item)

    def __len__(self) -> int:
        """추가된 원소 수 반환"""
        return self.count

    @property
    def estimated_fpr(self) -> float:
        """현재 상태의 추정 False Positive Rate"""
        if self.count == 0:
            return 0.0
        exponent = -self.num_hashes * self.count / self.size
        return (1 - math.exp(exponent)) ** self.num_hashes

    @property
    def fill_ratio(self) -> float:
        """비트 배열의 채워진 비율"""
        ones = sum(bin(byte).count("1") for byte in self._bit_array)
        return ones / self.size

    @property
    def memory_bytes(self) -> int:
        """사용 중인 메모리 (bytes)"""
        return len(self._bit_array)

    def stats(self) -> dict:
        """통계 정보 반환"""
        return {
            "size_bits": self.size,
            "num_hashes": self.num_hashes,
            "items_added": self.count,
            "fill_ratio": self.fill_ratio,
            "estimated_fpr": self.estimated_fpr,
            "target_fpr": self.target_fpr,
            "memory_kb": self.memory_bytes / 1024,
        }


class CountingBloomFilter:
    """
    Counting Bloom Filter - 삭제 지원

    각 위치를 비트 대신 카운터로 관리하여 삭제 연산 지원
    단점: 메모리 사용량 증가 (위치당 1비트 → 4바이트)
    """

    def __init__(self, expected_items: int, false_positive_rate: float = 0.01):
        self.size = BloomFilter._optimal_size(expected_items, false_positive_rate)
        self.num_hashes = BloomFilter._optimal_hashes(self.size, expected_items)
        self.counters = [0] * self.size
        self.count = 0

    def _hash(self, item: Any, seed: int) -> int:
        data = f"{seed}:{item}".encode("utf-8")
        h = hashlib.md5(data).hexdigest()
        return int(h, 16) % self.size

    def add(self, item: Any) -> None:
        """원소 추가"""
        for seed in range(self.num_hashes):
            index = self._hash(item, seed)
            self.counters[index] += 1
        self.count += 1

    def remove(self, item: Any) -> bool:
        """
        원소 삭제

        주의: 존재하지 않는 원소를 삭제하면 다른 원소에 영향을 줄 수 있음
        """
        # 먼저 존재 여부 확인
        if not self.contains(item):
            return False

        for seed in range(self.num_hashes):
            index = self._hash(item, seed)
            if self.counters[index] > 0:
                self.counters[index] -= 1

        self.count -= 1
        return True

    def contains(self, item: Any) -> bool:
        """원소 존재 여부 확인"""
        for seed in range(self.num_hashes):
            index = self._hash(item, seed)
            if self.counters[index] == 0:
                return False
        return True

    def __contains__(self, item: Any) -> bool:
        return self.contains(item)


# ============================================================
# 데모 및 테스트
# ============================================================


def demo_basic_usage():
    """기본 사용법 데모"""
    print("=" * 60)
    print("Bloom Filter 기본 사용법")
    print("=" * 60)

    # 1만 개 원소, 1% FPR
    bf = BloomFilter(expected_items=10000, false_positive_rate=0.01)

    print(f"\n설정:")
    print(f"  예상 원소 수: 10,000")
    print(f"  목표 FPR: 1%")
    print(f"  비트 배열 크기: {bf.size:,} bits ({bf.memory_bytes / 1024:.1f} KB)")
    print(f"  해시 함수 수: {bf.num_hashes}")

    # 원소 추가
    urls = [
        "https://example.com/page1",
        "https://example.com/page2",
        "https://example.com/page3",
    ]

    print(f"\n--- 원소 추가 ---")
    for url in urls:
        bf.add(url)
        print(f"  추가: {url}")

    # 조회
    print(f"\n--- 멤버십 테스트 ---")
    test_urls = urls + ["https://example.com/page999", "https://other.com"]

    for url in test_urls:
        result = url in bf
        status = "있음 (추가됨)" if url in urls else ("있음 (FP?)" if result else "없음")
        print(f"  '{url}': {result} - {status}")


def demo_fpr_measurement():
    """실제 False Positive Rate 측정"""
    print("\n" + "=" * 60)
    print("False Positive Rate 측정")
    print("=" * 60)

    import random
    import string

    def random_string(length: int = 20) -> str:
        return "".join(random.choices(string.ascii_lowercase, k=length))

    # 다양한 FPR 설정 테스트
    test_configs = [
        (10000, 0.01),   # 1%
        (10000, 0.001),  # 0.1%
        (10000, 0.1),    # 10%
    ]

    for expected_items, target_fpr in test_configs:
        bf = BloomFilter(expected_items, target_fpr)

        # 원소 추가
        added_items = set()
        for _ in range(expected_items):
            item = random_string()
            bf.add(item)
            added_items.add(item)

        # False Positive 측정
        test_count = 10000
        false_positives = 0

        for _ in range(test_count):
            item = random_string()
            if item not in added_items and item in bf:
                false_positives += 1

        actual_fpr = false_positives / test_count

        print(f"\n목표 FPR: {target_fpr:.2%}")
        print(f"  비트 배열: {bf.size:,} bits ({bf.memory_bytes / 1024:.1f} KB)")
        print(f"  해시 함수: {bf.num_hashes}개")
        print(f"  추정 FPR: {bf.estimated_fpr:.4%}")
        print(f"  실제 FPR: {actual_fpr:.4%}")


def demo_memory_comparison():
    """메모리 사용량 비교"""
    print("\n" + "=" * 60)
    print("메모리 사용량 비교: Bloom Filter vs Set")
    print("=" * 60)

    import sys

    sizes = [10_000, 100_000, 1_000_000]

    for n in sizes:
        # Bloom Filter (1% FPR)
        bf = BloomFilter(n, 0.01)
        bf_memory = bf.memory_bytes

        # Python set 예상 메모리 (문자열 20바이트 가정 + 오버헤드)
        set_memory_estimate = n * 80  # 대략적인 추정

        print(f"\n원소 수: {n:,}")
        print(f"  Bloom Filter: {bf_memory / 1024:.1f} KB")
        print(f"  Set (추정): {set_memory_estimate / 1024:.1f} KB")
        print(f"  절약률: {(1 - bf_memory / set_memory_estimate) * 100:.1f}%")


def demo_url_deduplication():
    """URL 중복 제거 시뮬레이션"""
    print("\n" + "=" * 60)
    print("URL 중복 제거 시뮬레이션")
    print("=" * 60)

    # 크롤링 시뮬레이션
    bf = BloomFilter(expected_items=100000, false_positive_rate=0.01)

    # 가상의 크롤링 데이터
    crawled_urls = [
        "https://example.com/",
        "https://example.com/about",
        "https://example.com/products",
        "https://example.com/",  # 중복
        "https://example.com/contact",
        "https://example.com/about",  # 중복
        "https://other.com/",
        "https://example.com/products",  # 중복
        "https://new-site.com/",
    ]

    print(f"\n크롤링 URL 처리:")
    new_count = 0
    dup_count = 0

    for url in crawled_urls:
        # 정규화 (실제로는 더 복잡한 로직)
        normalized = url.lower().rstrip("/")

        if normalized in bf:
            print(f"  [SKIP] {url}")
            dup_count += 1
        else:
            print(f"  [NEW]  {url}")
            bf.add(normalized)
            new_count += 1

    print(f"\n결과:")
    print(f"  새 URL: {new_count}")
    print(f"  중복 스킵: {dup_count}")
    print(f"  Bloom Filter 상태: {bf.stats()}")


def demo_counting_bloom_filter():
    """Counting Bloom Filter 데모"""
    print("\n" + "=" * 60)
    print("Counting Bloom Filter (삭제 지원)")
    print("=" * 60)

    cbf = CountingBloomFilter(expected_items=1000, false_positive_rate=0.01)

    # 추가
    items = ["apple", "banana", "cherry"]
    print("\n--- 원소 추가 ---")
    for item in items:
        cbf.add(item)
        print(f"  추가: {item}")

    # 조회
    print("\n--- 추가 후 조회 ---")
    for item in items + ["durian"]:
        print(f"  '{item}' in cbf: {item in cbf}")

    # 삭제
    print("\n--- 'banana' 삭제 ---")
    cbf.remove("banana")

    # 삭제 후 조회
    print("\n--- 삭제 후 조회 ---")
    for item in items:
        print(f"  '{item}' in cbf: {item in cbf}")


def demo_large_scale_simulation():
    """대규모 시뮬레이션"""
    print("\n" + "=" * 60)
    print("대규모 시뮬레이션: 100만 문서 중복 체크")
    print("=" * 60)

    import time

    n = 1_000_000
    bf = BloomFilter(expected_items=n, false_positive_rate=0.001)

    print(f"\n설정:")
    print(f"  문서 수: {n:,}")
    print(f"  목표 FPR: 0.1%")
    print(f"  메모리: {bf.memory_bytes / 1024 / 1024:.2f} MB")

    # 삽입 성능
    print(f"\n--- 삽입 성능 ---")
    start = time.perf_counter()
    for i in range(n):
        bf.add(f"document_{i}")
    elapsed = time.perf_counter() - start

    print(f"  {n:,}개 삽입: {elapsed:.2f}초")
    print(f"  초당 삽입: {n / elapsed:,.0f} ops/sec")

    # 조회 성능
    print(f"\n--- 조회 성능 ---")
    test_n = 100_000
    start = time.perf_counter()
    for i in range(test_n):
        _ = f"document_{i}" in bf
    elapsed = time.perf_counter() - start

    print(f"  {test_n:,}개 조회: {elapsed:.3f}초")
    print(f"  초당 조회: {test_n / elapsed:,.0f} ops/sec")

    print(f"\n최종 통계: {bf.stats()}")


if __name__ == "__main__":
    demo_basic_usage()
    demo_fpr_measurement()
    demo_memory_comparison()
    demo_url_deduplication()
    demo_counting_bloom_filter()
    demo_large_scale_simulation()
