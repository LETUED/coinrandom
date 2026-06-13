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
    val = int.from_bytes(b[:8], "big")
    return val / (2**64)
