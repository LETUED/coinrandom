"""core.py — deterministic, network-free."""
from coinrandom.core import bytes_to_float, mix_entropy


def test_bytes_to_float_zero():
    assert bytes_to_float(b"\x00" * 8) == 0.0


def test_bytes_to_float_known_values():
    assert bytes_to_float((2**11).to_bytes(8, "big")) == 1 / 2**53
    assert abs(bytes_to_float((2**63).to_bytes(8, "big")) - 0.5) < 1e-15


def test_bytes_to_float_never_reaches_one():
    # the [0.0, 1.0) contract: even all-ones must stay strictly below 1.0
    assert bytes_to_float(b"\xff" * 8) < 1.0
    assert bytes_to_float(b"\xff" * 8) == (2**53 - 1) / 2**53


def test_bytes_to_float_uses_only_first_8_bytes():
    # trailing bytes must not affect the result
    assert bytes_to_float(b"\x00" * 8 + b"\xff" * 8) == 0.0


def test_bytes_to_float_in_unit_interval():
    for i in range(256):
        v = bytes_to_float(bytes([i]) * 8)
        assert 0.0 <= v <= 1.0


def test_mix_entropy_is_sha512_length_and_varies():
    out = mix_entropy(b"abc")
    assert isinstance(out, bytes) and len(out) == 64
    # os.urandom + time.time make every call differ even for identical input
    assert out != mix_entropy(b"abc")
