import hashlib
import math
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, MutableSequence, Sequence

import requests

from ..core import mix_entropy, bytes_to_float
from ..proof import RandomProof

HEAVY_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XMRUSDT", "LINKUSDT",
    "DOGEUSDT", "ATOMUSDT", "MATICUSDT", "AVAXUSDT", "DOTUSDT",
    "LTCUSDT", "UNIUSDT", "AAVEUSDT", "MKRUSDT", "CRVUSDT",
]

ARGON2_TIME_COST = 4
ARGON2_MEMORY_COST = 65536  # 64MB
ARGON2_PARALLELISM = 2
ARGON2_HASH_LEN = 64


def _fetch_binance(symbols: list[str]) -> tuple[bytes, list[dict]]:
    raw = bytearray()
    records = []
    for symbol in symbols:
        try:
            resp = requests.get(
                "https://api.binance.com/api/v3/trades",
                params={"symbol": symbol, "limit": 5},
                timeout=4,
            )
            trades = resp.json()
            for t in trades:
                raw += str(t["price"]).encode()
                raw += str(t["qty"]).encode()
                raw += str(t["time"]).encode()
                raw += str(t["isBuyerMaker"]).encode()
            records.append({"exchange": "binance", "symbol": symbol, "count": len(trades)})
        except Exception:
            pass
    return bytes(raw), records


def _fetch_upbit(symbols: list[str]) -> tuple[bytes, list[dict]]:
    raw = bytearray()
    records = []
    upbit_map = {
        "BTCUSDT": "KRW-BTC", "ETHUSDT": "KRW-ETH", "SOLUSDT": "KRW-SOL",
        "DOGEUSDT": "KRW-DOGE", "LINKUSDT": "KRW-LINK", "DOTUSDT": "KRW-DOT",
        "AVAXUSDT": "KRW-AVAX", "ATOMUSDT": "KRW-ATOM",
    }
    for symbol in symbols:
        market = upbit_map.get(symbol)
        if not market:
            continue
        try:
            resp = requests.get(
                "https://api.upbit.com/v1/trades/ticks",
                params={"market": market, "count": 5},
                timeout=4,
            )
            trades = resp.json()
            for t in trades:
                raw += str(t["trade_price"]).encode()
                raw += str(t["trade_volume"]).encode()
                raw += str(t["timestamp"]).encode()
            records.append({"exchange": "upbit", "symbol": market, "count": len(trades)})
        except Exception:
            pass
    return bytes(raw), records


def _fetch_coinbase(symbols: list[str]) -> tuple[bytes, list[dict]]:
    raw = bytearray()
    records = []
    cb_map = {
        "BTCUSDT": "BTC-USD", "ETHUSDT": "ETH-USD", "SOLUSDT": "SOL-USD",
        "LINKUSDT": "LINK-USD", "DOGEUSDT": "DOGE-USD", "LTCUSDT": "LTC-USD",
        "DOTUSDT": "DOT-USD", "AVAXUSDT": "AVAX-USD", "UNIUSDT": "UNI-USD",
    }
    for symbol in symbols:
        product = cb_map.get(symbol)
        if not product:
            continue
        try:
            resp = requests.get(
                f"https://api.exchange.coinbase.com/products/{product}/trades",
                params={"limit": 5},
                timeout=4,
            )
            trades = resp.json()
            for t in trades:
                raw += str(t["price"]).encode()
                raw += str(t["size"]).encode()
                raw += str(t["time"]).encode()
            records.append({"exchange": "coinbase", "symbol": product, "count": len(trades)})
        except Exception:
            pass
    return bytes(raw), records


_ETH_RPC_ENDPOINTS = [
    "https://eth.llamarpc.com",
    "https://rpc.ankr.com/eth",
    "https://ethereum.publicnode.com",
    "https://cloudflare-eth.com",
]

def _fetch_eth_block_hash() -> str:
    payload = {"jsonrpc": "2.0", "method": "eth_getBlockByNumber", "params": ["latest", False], "id": 1}
    for endpoint in _ETH_RPC_ENDPOINTS:
        try:
            resp = requests.post(endpoint, json=payload, timeout=5)
            h = resp.json()["result"]["hash"]
            if h:
                return h
        except Exception:
            continue
    return ""


def _argon2_stretch(data: bytes, salt: bytes) -> bytes:
    from argon2.low_level import hash_secret_raw, Type
    return hash_secret_raw(
        secret=data,
        salt=salt,
        time_cost=ARGON2_TIME_COST,
        memory_cost=ARGON2_MEMORY_COST,
        parallelism=ARGON2_PARALLELISM,
        hash_len=ARGON2_HASH_LEN,
        type=Type.ID,
    )


def _collect_entropy(symbols: list[str]) -> tuple[bytes, list[dict], str]:
    results = {}
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {
            ex.submit(_fetch_binance, symbols): "binance",
            ex.submit(_fetch_upbit, symbols): "upbit",
            ex.submit(_fetch_coinbase, symbols): "coinbase",
        }
        for f in as_completed(futures):
            results[futures[f]] = f.result()

    all_raw = b""
    all_records = []
    for key in ("binance", "upbit", "coinbase"):
        raw, records = results.get(key, (b"", []))
        all_raw += raw
        all_records.extend(records)

    block_hash = _fetch_eth_block_hash()
    all_raw += block_hash.encode()
    return all_raw, all_records, block_hash


def _build_heavy_seed(symbols: list[str]) -> tuple[bytes, list[dict], str, str]:
    raw, records, block_hash = _collect_entropy(symbols)
    mixed = mix_entropy(raw)
    salt = os.urandom(16)
    stretched = _argon2_stretch(mixed, salt)
    final_hash = hashlib.sha256(stretched).hexdigest()
    return stretched, records, block_hash, final_hash


class HeavyEngine:
    def __init__(self, symbols: list[str] = HEAVY_SYMBOLS):
        self.symbols = symbols
        self._argon2_params = {
            "time_cost": ARGON2_TIME_COST,
            "memory_cost_kb": ARGON2_MEMORY_COST,
            "parallelism": ARGON2_PARALLELISM,
            "hash_len": ARGON2_HASH_LEN,
        }

    def _generate(self) -> tuple[bytes, list[dict], str, str]:
        return _build_heavy_seed(self.symbols)

    def random(self) -> float:
        seed, _, _, _ = self._generate()
        return bytes_to_float(seed)

    def uniform(self, a: float, b: float) -> float:
        return a + (b - a) * self.random()

    def randint(self, a: int, b: int) -> int:
        span = b - a + 1
        threshold = (2**64) - (2**64 % span)
        while True:
            seed, _, _, _ = self._generate()
            val = int.from_bytes(seed[:8], "big")
            if val < threshold:
                return a + (val % span)

    def choice(self, seq: Sequence[Any]) -> Any:
        return seq[self.randint(0, len(seq) - 1)]

    def choices(self, seq: Sequence[Any], k: int = 1) -> list[Any]:
        return [self.choice(seq) for _ in range(k)]

    def sample(self, seq: Sequence[Any], k: int) -> list[Any]:
        pool = list(seq)
        result = []
        for _ in range(k):
            idx = self.randint(0, len(pool) - 1)
            result.append(pool.pop(idx))
        return result

    def shuffle(self, seq: MutableSequence[Any]) -> None:
        for i in range(len(seq) - 1, 0, -1):
            j = self.randint(0, i)
            seq[i], seq[j] = seq[j], seq[i]

    def gauss(self, mu: float = 0.0, sigma: float = 1.0) -> float:
        u1, u2 = self.random(), self.random()
        z = math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
        return mu + sigma * z

    def random_with_proof(self) -> RandomProof:
        seed, records, block_hash, final_hash = self._generate()
        return RandomProof(
            value=bytes_to_float(seed),
            timestamp=datetime.now(timezone.utc).isoformat(),
            exchanges=records,
            symbols=self.symbols,
            block_hash=block_hash,
            argon2_params=self._argon2_params,
            final_hash=final_hash,
        )
