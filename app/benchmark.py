"""Deterministic dataset generation and sequential benchmark statistics."""
import math
import random
import statistics
import time
from typing import Callable

CATEGORIES = ("books", "electronics", "home", "sports", "clothing")


def make_products(count: int) -> list[dict]:
    """Generate equivalent records for both databases; all values are synthetic."""
    rng = random.Random(42)
    return [
        {"id": i, "category": CATEGORIES[rng.randrange(len(CATEGORIES))],
         "price_cents": rng.randint(1000, 100_000)}
        for i in range(1, count + 1)
    ]


def nearest_rank_percentile(samples: list[float], percentile: float) -> float:
    ordered = sorted(samples)
    return ordered[max(0, math.ceil(len(ordered) * percentile) - 1)]


def measure(fn: Callable[[], object], repetitions: int) -> dict:
    """Measures single-threaded end-to-end query/fetch latency, not server-only time."""
    fn()  # warm up once, excluded from numbers
    measurements = []
    started = time.perf_counter()
    for _ in range(repetitions):
        tick = time.perf_counter()
        fn()
        measurements.append((time.perf_counter() - tick) * 1000)
    elapsed = time.perf_counter() - started
    return {
        "runs": repetitions,
        "p50_ms": round(statistics.median(measurements), 3),
        "p95_ms": round(nearest_rank_percentile(measurements, 0.95), 3),
        "mean_ms": round(statistics.mean(measurements), 3),
        "min_ms": round(min(measurements), 3),
        "max_ms": round(max(measurements), 3),
        "sequential_queries_per_sec": round(repetitions / elapsed, 2),
    }
