from app.benchmark import make_products, measure, nearest_rank_percentile


def test_synthetic_data_deterministic():
    assert make_products(100) == make_products(100)
    assert len(make_products(100)) == 100
    assert len({p["id"] for p in make_products(100)}) == 100
    assert all(1000 <= p["price_cents"] <= 100000 for p in make_products(100))


def test_percentile_nearest_rank():
    assert nearest_rank_percentile([4, 1, 3, 2, 5], .95) == 5
    assert nearest_rank_percentile([4, 1, 3, 2, 5], .5) == 3


def test_measure():
    count = 0

    def run():
        nonlocal count
        count += 1

    stats = measure(run, 8)
    assert count == 9  # one warm-up
    assert stats["runs"] == 8
    assert stats["p95_ms"] >= stats["p50_ms"]
    assert stats["sequential_queries_per_sec"] > 0
