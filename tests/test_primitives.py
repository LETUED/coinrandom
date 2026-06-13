"""Generator primitives via injected entropy — no network.

We replace StandardEngine._generate with a scripted byte stream so randint's
rejection sampling and the sequence ops are exercised deterministically.
"""
import pytest

from coinrandom.heavy.engine import HeavyEngine
from coinrandom.standard.engine import StandardEngine

SPAN10_THRESHOLD = (2**64) - (2**64 % 10)  # values >= this are rejected by randint(0,9)


def make_engine(values):
    """values: iterable of ints placed in the top 8 bytes of the seed."""
    eng = StandardEngine()
    it = iter(values)

    def fake_generate():
        v = next(it)
        return (v.to_bytes(8, "big") + bytes(56), [], {}, "")

    eng._generate = fake_generate
    return eng


def test_random_maps_value_to_unit_interval():
    eng = make_engine([0, 2**63, 2**64 - 1])
    assert eng.random() == 0.0
    assert abs(eng.random() - 0.5) < 1e-15
    assert eng.random() < 1.0


def test_randint_maps_value():
    eng = make_engine([0, 5, 9])
    assert eng.randint(0, 9) == 0
    assert eng.randint(0, 9) == 5
    assert eng.randint(0, 9) == 9


def test_randint_rejection_resamples_at_or_above_threshold():
    # values at or above the rejection threshold must be resampled
    eng = make_engine([SPAN10_THRESHOLD, SPAN10_THRESHOLD + 1, 7])
    assert eng.randint(0, 9) == 7


def test_randint_range_sweep_in_bounds():
    eng = make_engine(range(0, 2**64, 2**60))
    for _ in range(16):
        v = eng.randint(10, 20)
        assert 10 <= v <= 20


def test_randint_uniform_buckets():
    # consecutive inputs 0..999 -> each residue mod 10 appears exactly 100 times
    eng = make_engine(range(1000))
    counts = [0] * 10
    for _ in range(1000):
        counts[eng.randint(0, 9)] += 1
    assert counts == [100] * 10, counts


def test_choice_uses_index():
    eng = make_engine([2])  # index 2
    assert eng.choice(["a", "b", "c", "d"]) == "c"


def test_sample_no_duplicates():
    eng = make_engine([0, 0, 0])  # pop(0) three times from shrinking pool
    out = eng.sample([10, 20, 30, 40], k=3)
    assert out == [10, 20, 30]
    assert len(set(out)) == 3


def test_shuffle_preserves_elements():
    eng = make_engine([0, 0, 0, 0])
    lst = [1, 2, 3, 4, 5]
    eng.shuffle(lst)
    assert sorted(lst) == [1, 2, 3, 4, 5]


# ── drop-in API contract guards (match stdlib random) ──────────────

def test_randint_empty_range_raises():
    eng = make_engine([])
    with pytest.raises(ValueError):
        eng.randint(5, 3)


def test_choice_empty_raises_indexerror():
    eng = make_engine([])
    with pytest.raises(IndexError):
        eng.choice([])


def test_sample_too_large_raises_valueerror():
    eng = make_engine([])
    with pytest.raises(ValueError):
        eng.sample([1, 2, 3], k=5)


def test_sample_negative_k_raises_valueerror():
    eng = make_engine([])
    with pytest.raises(ValueError):
        eng.sample([1, 2, 3], k=-1)


@pytest.mark.parametrize("engine", [StandardEngine(), HeavyEngine()])
def test_guards_apply_to_both_engines(engine):
    # guards validate before the entropy pipeline, so no network is touched
    with pytest.raises(ValueError):
        engine.randint(5, 3)
    with pytest.raises(IndexError):
        engine.choice([])
    with pytest.raises(ValueError):
        engine.sample([1, 2, 3], k=5)
