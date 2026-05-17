import hashlib
import os
import struct
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from requests.adapters import HTTPAdapter

BINANCE_TRADES = "https://api.binance.com/api/v3/trades"

_session = requests.Session()
_session.mount("https://", HTTPAdapter(pool_connections=1, pool_maxsize=10))


def fetch_binance_entropy(symbols: list[str], limit: int = 5) -> bytes:
    def _one(symbol: str) -> tuple[str, bytes]:
        try:
            resp = _session.get(
                BINANCE_TRADES,
                params={"symbol": symbol, "limit": limit},
                timeout=3,
            )
            raw = bytearray()
            for t in resp.json():
                raw += str(t["price"]).encode()
                raw += str(t["qty"]).encode()
                raw += str(t["time"]).encode()
                raw += str(t["isBuyerMaker"]).encode()
            return symbol, bytes(raw)
        except Exception:
            return symbol, b""

    result: dict[str, bytes] = {}
    with ThreadPoolExecutor(max_workers=len(symbols)) as ex:
        for sym, raw in ex.map(_one, symbols):
            result[sym] = raw

    return b"".join(result[s] for s in symbols)


def mix_entropy(*sources: bytes) -> bytes:
    ts = struct.pack(">d", time.time())
    sys_e = os.urandom(32)
    combined = b"".join(sources) + ts + sys_e
    return hashlib.sha512(combined).digest()


def bytes_to_float(b: bytes) -> float:
    val = int.from_bytes(b[:8], "big")
    return val / (2**64)
