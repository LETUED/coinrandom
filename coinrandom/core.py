import hashlib
import os
import struct
import time

import requests

BINANCE_TRADES = "https://api.binance.com/api/v3/trades"


def fetch_binance_entropy(symbols: list[str], limit: int = 5) -> bytes:
    raw = bytearray()
    for symbol in symbols:
        try:
            resp = requests.get(
                BINANCE_TRADES,
                params={"symbol": symbol, "limit": limit},
                timeout=3,
            )
            for t in resp.json():
                raw += str(t["price"]).encode()
                raw += str(t["qty"]).encode()
                raw += str(t["time"]).encode()
                raw += str(t["isBuyerMaker"]).encode()
        except Exception:
            pass
    return bytes(raw)


def mix_entropy(*sources: bytes) -> bytes:
    ts = struct.pack(">d", time.time())
    sys_e = os.urandom(32)
    combined = b"".join(sources) + ts + sys_e
    return hashlib.sha512(combined).digest()


def bytes_to_float(b: bytes) -> float:
    val = int.from_bytes(b[:8], "big")
    return val / (2**64)
