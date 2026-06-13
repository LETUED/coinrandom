import asyncio
import functools
import hashlib
import math
import os
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, MutableSequence, Sequence

import requests
from requests.adapters import HTTPAdapter

from ..core import mix_entropy, bytes_to_float
from ..chains.eth import fetch_entropy as fetch_eth_entropy
from ..chains.btc import fetch_entropy as fetch_btc_entropy
from ..chains.sol import fetch_entropy as fetch_sol_entropy
from ..proof import RandomProof


def _make_session(pool_maxsize: int) -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = "coinrandom/2.0 (+https://github.com/LETUED/coinrandom)"
    adapter = HTTPAdapter(pool_connections=1, pool_maxsize=pool_maxsize)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


_session_binance  = _make_session(20)
_session_upbit    = _make_session(10)
_session_coinbase = _make_session(10)

STANDARD_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XMRUSDT", "LINKUSDT",
    "DOGEUSDT", "ATOMUSDT", "MATICUSDT", "AVAXUSDT", "DOTUSDT",
    "LTCUSDT", "UNIUSDT", "AAVEUSDT", "MKRUSDT", "CRVUSDT",
]

ARGON2_TIME_COST = 4
ARGON2_MEMORY_COST = 65536  # 64MB
ARGON2_PARALLELISM = 2
ARGON2_HASH_LEN = 64


def _fetch_binance(symbols: list[str]) -> tuple[bytes, list[dict]]:
    def _one(symbol: str) -> tuple[str, bytes, dict | None]:
        try:
            resp = _session_binance.get(
                "https://data-api.binance.vision/api/v3/trades",
                params={"symbol": symbol, "limit": 5},
                timeout=4,
            )
            trades = resp.json()
            raw = bytearray()
            for t in trades:
                raw += str(t["price"]).encode()
                raw += str(t["qty"]).encode()
                raw += str(t["time"]).encode()
                raw += str(t["isBuyerMaker"]).encode()
            return symbol, bytes(raw), {"exchange": "binance", "symbol": symbol, "count": len(trades)}
        except Exception:
            return symbol, b"", None

    bucket: dict[str, tuple[bytes, dict | None]] = {}
    with ThreadPoolExecutor(max_workers=max(len(symbols), 1)) as ex:
        for sym, raw, rec in ex.map(_one, symbols):
            bucket[sym] = (raw, rec)

    all_raw = bytearray()
    records = []
    for s in symbols:
        raw, rec = bucket.get(s, (b"", None))
        all_raw += raw
        if rec:
            records.append(rec)
    return bytes(all_raw), records


def _fetch_upbit(symbols: list[str]) -> tuple[bytes, list[dict]]:
    upbit_map = {
        "BTCUSDT": "KRW-BTC", "ETHUSDT": "KRW-ETH", "SOLUSDT": "KRW-SOL",
        "DOGEUSDT": "KRW-DOGE", "LINKUSDT": "KRW-LINK", "DOTUSDT": "KRW-DOT",
        "AVAXUSDT": "KRW-AVAX", "ATOMUSDT": "KRW-ATOM",
    }
    mapped = [(s, upbit_map[s]) for s in symbols if s in upbit_map]

    def _one(args: tuple[str, str]) -> tuple[str, bytes, dict | None]:
        symbol, market = args
        try:
            resp = _session_upbit.get(
                "https://api.upbit.com/v1/trades/ticks",
                params={"market": market, "count": 5},
                timeout=4,
            )
            trades = resp.json()
            raw = bytearray()
            for t in trades:
                raw += str(t["trade_price"]).encode()
                raw += str(t["trade_volume"]).encode()
                raw += str(t["timestamp"]).encode()
            return symbol, bytes(raw), {"exchange": "upbit", "symbol": market, "count": len(trades)}
        except Exception:
            return symbol, b"", None

    bucket: dict[str, tuple[bytes, dict | None]] = {}
    with ThreadPoolExecutor(max_workers=max(len(mapped), 1)) as ex:
        for sym, raw, rec in ex.map(_one, mapped):
            bucket[sym] = (raw, rec)

    all_raw = bytearray()
    records = []
    for s, _ in mapped:
        raw, rec = bucket.get(s, (b"", None))
        all_raw += raw
        if rec:
            records.append(rec)
    return bytes(all_raw), records


def _fetch_coinbase(symbols: list[str]) -> tuple[bytes, list[dict]]:
    cb_map = {
        "BTCUSDT": "BTC-USD", "ETHUSDT": "ETH-USD", "SOLUSDT": "SOL-USD",
        "LINKUSDT": "LINK-USD", "DOGEUSDT": "DOGE-USD", "LTCUSDT": "LTC-USD",
        "DOTUSDT": "DOT-USD", "AVAXUSDT": "AVAX-USD", "UNIUSDT": "UNI-USD",
    }
    mapped = [(s, cb_map[s]) for s in symbols if s in cb_map]

    def _one(args: tuple[str, str]) -> tuple[str, bytes, dict | None]:
        symbol, product = args
        try:
            resp = _session_coinbase.get(
                f"https://api.exchange.coinbase.com/products/{product}/trades",
                params={"limit": 5},
                timeout=4,
            )
            trades = resp.json()
            raw = bytearray()
            for t in trades:
                raw += str(t["price"]).encode()
                raw += str(t["size"]).encode()
                raw += str(t["time"]).encode()
            return symbol, bytes(raw), {"exchange": "coinbase", "symbol": product, "count": len(trades)}
        except Exception:
            return symbol, b"", None

    bucket: dict[str, tuple[bytes, dict | None]] = {}
    with ThreadPoolExecutor(max_workers=max(len(mapped), 1)) as ex:
        for sym, raw, rec in ex.map(_one, mapped):
            bucket[sym] = (raw, rec)

    all_raw = bytearray()
    records = []
    for s, _ in mapped:
        raw, rec = bucket.get(s, (b"", None))
        all_raw += raw
        if rec:
            records.append(rec)
    return bytes(all_raw), records


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


def _collect_entropy(symbols: list[str]) -> tuple[bytes, list[dict], dict[str, str]]:
    results: dict = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = {
            ex.submit(_fetch_binance, symbols): "binance",
            ex.submit(_fetch_upbit, symbols): "upbit",
            ex.submit(_fetch_coinbase, symbols): "coinbase",
            ex.submit(fetch_eth_entropy): "eth",
            ex.submit(fetch_btc_entropy): "btc",
            ex.submit(fetch_sol_entropy): "sol",
        }
        for f in as_completed(futures):
            results[futures[f]] = f.result()

    all_raw = b""
    all_records = []
    market_active = 0
    for key in ("binance", "upbit", "coinbase"):
        raw, records = results.get(key, (b"", []))
        all_raw += raw
        all_records.extend(records)
        if raw:
            market_active += 1

    eth_raw, eth_id = results.get("eth", (b"", ""))
    btc_raw, btc_id = results.get("btc", (b"", ""))
    sol_raw, sol_id = results.get("sol", (b"", ""))

    all_raw += eth_raw + btc_raw + sol_raw

    blockchain_active = sum(1 for r in [eth_raw, btc_raw, sol_raw] if r)
    if blockchain_active == 0:
        raise RuntimeError(
            "coinrandom: no blockchain sources responded. Cannot guarantee entropy quality."
        )

    total_active = market_active + blockchain_active
    if total_active < 5:
        warnings.warn(
            f"coinrandom: only {total_active}/6 entropy sources responded. "
            "Randomness quality may be reduced.",
            stacklevel=2,
        )

    block_hashes = {"ETH": eth_id, "BTC": btc_id, "SOL": sol_id}
    return all_raw, all_records, block_hashes


def _build_standard_seed(symbols: list[str]) -> tuple[bytes, list[dict], dict[str, str], str]:
    raw, records, block_hashes = _collect_entropy(symbols)
    mixed = mix_entropy(raw)
    salt = os.urandom(16)
    stretched = _argon2_stretch(mixed, salt)
    final_hash = hashlib.sha256(stretched).hexdigest()
    return stretched, records, block_hashes, final_hash


class StandardEngine:
    def __init__(self, symbols: list[str] = STANDARD_SYMBOLS):
        self.symbols = symbols
        self._argon2_params = {
            "time_cost": ARGON2_TIME_COST,
            "memory_cost_kb": ARGON2_MEMORY_COST,
            "parallelism": ARGON2_PARALLELISM,
            "hash_len": ARGON2_HASH_LEN,
        }

    def _generate(self) -> tuple[bytes, list[dict], dict[str, str], str]:
        return _build_standard_seed(self.symbols)

    def random(self) -> float:
        seed, _, _, _ = self._generate()
        return bytes_to_float(seed)

    def uniform(self, a: float, b: float) -> float:
        return a + (b - a) * self.random()

    def randint(self, a: int, b: int) -> int:
        if b < a:
            raise ValueError(f"empty range for randint({a}, {b})")
        span = b - a + 1
        threshold = (2**64) - (2**64 % span)
        while True:
            seed, _, _, _ = self._generate()
            val = int.from_bytes(seed[:8], "big")
            if val < threshold:
                return a + (val % span)

    def choice(self, seq: Sequence[Any]) -> Any:
        if len(seq) == 0:
            raise IndexError("Cannot choose from an empty sequence")
        return seq[self.randint(0, len(seq) - 1)]

    def choices(self, seq: Sequence[Any], k: int = 1) -> list[Any]:
        return [self.choice(seq) for _ in range(k)]

    def sample(self, seq: Sequence[Any], k: int) -> list[Any]:
        pool = list(seq)
        if not 0 <= k <= len(pool):
            raise ValueError("Sample larger than population or is negative")
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
        u1 = self.random()
        while u1 == 0.0:
            u1 = self.random()
        u2 = self.random()
        z = math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
        return mu + sigma * z

    def random_with_proof(self) -> RandomProof:
        seed, records, block_hashes, final_hash = self._generate()
        return RandomProof(
            value=bytes_to_float(seed),
            timestamp=datetime.now(timezone.utc).isoformat(),
            exchanges=records,
            symbols=self.symbols,
            block_hashes=block_hashes,
            argon2_params=self._argon2_params,
            final_hash=final_hash,
        )

    # ── Async API ─────────────────────────────────────────

    def _run(self, fn, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return loop.run_in_executor(None, functools.partial(fn, *args, **kwargs))

    async def arandom(self) -> float:
        return await self._run(self.random)

    async def auniform(self, a: float, b: float) -> float:
        return await self._run(self.uniform, a, b)

    async def arandint(self, a: int, b: int) -> int:
        return await self._run(self.randint, a, b)

    async def achoice(self, seq: Sequence[Any]) -> Any:
        return await self._run(self.choice, seq)

    async def achoices(self, seq: Sequence[Any], k: int = 1) -> list[Any]:
        return await self._run(self.choices, seq, k=k)

    async def asample(self, seq: Sequence[Any], k: int) -> list[Any]:
        return await self._run(self.sample, seq, k)

    async def ashuffle(self, seq: MutableSequence[Any]) -> None:
        return await self._run(self.shuffle, seq)

    async def agauss(self, mu: float = 0.0, sigma: float = 1.0) -> float:
        return await self._run(self.gauss, mu, sigma)

    async def arandom_with_proof(self) -> RandomProof:
        return await self._run(self.random_with_proof)
