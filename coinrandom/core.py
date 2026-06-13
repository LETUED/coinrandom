import hashlib
import os
import struct
import time


def mix_entropy(*sources: bytes) -> bytes:
    ts = struct.pack(">d", time.time())
    sys_e = os.urandom(32)
    combined = b"".join(sources) + ts + sys_e
    return hashlib.sha512(combined).digest()


def bytes_to_float(b: bytes) -> float:
    # 53 bits of entropy mapped to [0.0, 1.0) — same technique as CPython's
    # random(). Dividing the full 64-bit value by 2**64 can round up to exactly
    # 1.0, which would violate the half-open interval that callers rely on.
    val = int.from_bytes(b[:8], "big") >> 11
    return val / (2**53)
