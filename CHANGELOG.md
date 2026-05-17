# Changelog

[한국어](CHANGELOG.ko.md) | English

All notable changes to this project will be documented in this file.

Format: [Semantic Versioning](https://semver.org/)

---

## [Unreleased]

---

## [0.2.0] - 2026-05-17

### Added
- Async API for all three tiers — `arandom()`, `auniform()`, `arandint()`, `achoice()`, `achoices()`, `asample()`, `ashuffle()`, `agauss()`
- Heavy/SuperHeavy: `arandom_with_proof()` async variant
- All async functions use `asyncio.run_in_executor` — no new dependencies, compatible with FastAPI, aiohttp, and any asyncio-based framework

---

## [0.1.3] - 2026-05-17

### Changed
- All tiers: persistent `requests.Session` + `HTTPAdapter` connection pooling applied to Light (`core.py`) and SuperHeavy optimizer (`optimizer.py`)
- Light: Binance entropy fetch parallelized (3 symbols → concurrent)
- SuperHeavy klines fetch: ~1.94s → ~1.04s (46% improvement)
- GitHub Actions: `checkout@v4→v5`, `setup-python@v5→v6`
- CI: Python matrix (3.10/3.11/3.12/3.13) → single 3.13 for faster feedback
- CI: `paths-ignore` added — `.md`, `.gitignore`, `.gitattributes`, `LICENSE` changes skip CI

### Added
- `coinrandom.__version__` — runtime version access via `importlib.metadata`
- `coinrandom/py.typed` — PEP 561 marker for mypy/pyright type checker support

### Removed
- `coinrandom/functions.py` — unused legacy file

---

## [0.1.2] - 2026-05-17

### Changed
- Heavy: module-level `requests.Session` per exchange with `HTTPAdapter` connection pool
- Reduces TCP+TLS handshake overhead on repeated calls (~44% improvement in sustained throughput)
- Entropy output and proof structure unchanged

---

## [0.1.1] - 2026-05-16

### Changed
- Heavy: parallelized symbol fetching within each exchange (`_fetch_binance`, `_fetch_upbit`, `_fetch_coinbase`)
- Heavy: ETH block hash now fetched concurrently with exchange data (not after)
- Heavy: ETH RPC endpoints raced simultaneously — first success wins
- Heavy total latency: ~17s → ~2s
- SuperHeavy total latency: ~30s → ~4s
- Added `tests/benchmark.py` for stage-by-stage timing measurement

---

## [0.1.0] - 2026-05-16

### Added
- Initial release
- Three-tier architecture: Light / Heavy / SuperHeavy
- Light: Binance tick + Argon2 (t=1, m=8MB), ~1ms
- Heavy: 3 exchanges + ETH block hash + Argon2 (t=4, m=64MB), RandomProof
- SuperHeavy: inverse Markowitz portfolio optimization → Heavy pipeline, SuperProof
- Full `random` module API compatibility (`random`, `randint`, `uniform`, `choice`, `choices`, `sample`, `shuffle`, `gauss`)
- HashDRBG (SHA-512 counter-based), no stdlib `random` used anywhere
- Bilingual README (Korean primary, English secondary)
- CI: Python 3.10 / 3.11 / 3.12 / 3.13 matrix
- CD: tag `v*` → PyPI auto-deploy via OIDC Trusted Publisher
