# Changelog

[한국어](CHANGELOG.ko.md) | English

All notable changes to this project will be documented in this file.

Format: [Semantic Versioning](https://semver.org/)

---

## [Unreleased]

---

## [2.0.1] - 2026-06-13

### Fixed
- Replaced dead `rpc.ankr.com` ETH/SOL endpoints (now require an API key → silent 401/403) with verified keyless RPCs, and dropped the unreliable `eth.llamarpc.com`/`cloudflare-eth.com`. Restores real multi-endpoint redundancy for the blockchain entropy tier.
- Heavy optimizer no longer silently degrades to a no-op when `api.binance.com` is geo-blocked (HTTP 451 from US/cloud IPs): klines are fetched from the keyless `data-api.binance.vision` public mirror first, with `api.binance.com` as fallback. The Standard tier's Binance trades use the same mirror.
- Heavy optimizer: zero-variance (flat-return) coins no longer produce `NaN` that gets preferentially selected or leaks invalid `NaN` into the proof JSON (`np.nan_to_num`). The `<2`-valid-coin fallback now pairs the identity matrix with the symbols that actually had data.
- `random()`/`uniform()`/`gauss()` now guarantee the documented `[0.0, 1.0)` interval — `bytes_to_float` maps 53 bits (CPython technique) instead of dividing the full 64-bit value by `2**64`, which could round up to exactly `1.0`.
- Drop-in parity with `random`: `randint(a, b)` with `a > b` raises `ValueError`; `choice([])` raises `IndexError`; `sample(seq, k)` with `k > len`/`k < 0` raises `ValueError` — all validated before the entropy pipeline runs (previously an opaque `ZeroDivisionError` or silently wrong values).
- Chain parsers now skip a single malformed datum (bad hex log / out-of-range Solana balance) instead of dropping the whole source.

### Changed
- Added a descriptive `User-Agent` to all outbound requests to reduce spurious WAF/Cloudflare blocks.
- Raised the `requests` floor to `>=2.32.4` (closes CVE-2024-47081 and CVE-2024-35195); aligned `numpy`/`scipy` floors to tested versions.
- CI split into a deterministic offline test gate (pytest, Python 3.10–3.13 matrix) and a non-blocking live smoke job, so third-party outages no longer fail the build. The Heavy optimizer is now covered by offline unit tests.

---

## [2.0.0] - 2026-06-13

### Changed (BREAKING)
- Tier restructure — dropped the low-security `Light` tier and shifted the remaining tiers down one level:
  - `Heavy` → **`Standard`**, now the default API (`coinrandom.random()`). Runs the full entropy pipeline (3 exchanges + ETH/BTC/SOL block data + Argon2id t=4, m=64MB) on every call.
  - `SuperHeavy` → **`Heavy`** (`coinrandom.heavy`). Inverse-portfolio optimization + the Standard pipeline. Requires the `[heavy]` extra.
- `SuperProof` dataclass renamed to **`HeavyProof`**.
- Optional dependency group `[superheavy]` renamed to **`[heavy]`** (numpy, scipy).
- `coinrandom.random_with_proof()` is now available at the top level (Standard tier) and returns a `RandomProof`.

### Removed (BREAKING)
- `Light` tier and the `coinrandom.light` module — the ~1ms Binance-only / Argon2 (t=1, m=8MB) tier is gone; the secure full pipeline is the default now.
- `coinrandom.superheavy` module — use `coinrandom.heavy`.

### Migration
- `pip install "coinrandom[superheavy]"` → `pip install "coinrandom[heavy]"`
- `from coinrandom import superheavy` → `from coinrandom import heavy`
- Old `from coinrandom import heavy` (full pipeline) → use the `coinrandom` top level, or `from coinrandom import standard`
- `Light` (`coinrandom.random()` 1ms tier) → no direct replacement; the default is now the secure pipeline
- `SuperProof` → `HeavyProof`

---

## [1.2.0] - 2026-05-18

### Added
- Solana block data as 7th entropy source (`coinrandom/chains/sol.py`)
  - `getBlock` with `transactionDetails: "accounts"` — preBalances + postBalances of up to 30 transactions
  - 3 public RPC endpoints raced (Solana mainnet-beta, Ankr, PublicNode)
  - Independent from ETH/BTC validator sets
  - `RandomProof.block_hashes` now includes `"SOL"` key
- `chains/` package structure for extensible chain support
  - `chains/eth.py` — ETH PREVRANDAO (EIP-4399 `mixHash`) + Uniswap V3 swap logs
  - `chains/btc.py` — BTC block hash
  - `chains/sol.py` — SOL block balance data
- ETH entropy upgraded: `block.hash` → `block.mixHash` (PREVRANDAO) — validator RANDAO absorbed

### Changed
- Entropy source tier separation: blockchain sources (ETH/BTC/SOL) are tier 1 (availability guarantee); CEX sources are tier 2 (quality enhancement)
- New error condition: if all blockchain sources fail, raises `RuntimeError` instead of warning
- Warning threshold updated: `< 5/6` sources (was `4/6`)

### Removed
- `coinrandom/dex.py` — logic consolidated into `coinrandom/chains/eth.py`

---

## [1.1.0] - 2026-05-18

### Added
- Uniswap V3 on-chain swap data as a 6th entropy source (`coinrandom/dex.py`)
  - Pools: USDC/ETH, WBTC/ETH, ETH/USDT (0.05% tier)
  - Reads `Swap` event logs via raw JSON-RPC — no new dependencies
  - 4 public RPC endpoints raced simultaneously (LlamaNodes, Ankr, Cloudflare, PublicNode)
  - On-chain data: MITM impossible, no centralized API dependency
- Entropy warning threshold updated: `4/6` sources (was `4/5`)

---

## [1.0.1] - 2026-05-18

### Fixed
- `gauss()`: prevent `log(0)` crash when HashDRBG outputs `0.0` — rejection loop added to all three tiers (Light, Heavy, SuperHeavy)
- Fork safety: `os.register_at_fork(after_in_child=...)` forces DRBG reseed in child process after `os.fork()` — prevents identical sequences in prefork servers (Gunicorn, uWSGI)

---

## [1.0.0] - 2026-05-17

### Stable API Declaration

Public API is now frozen. Breaking changes require a new major version.

**Frozen API surface:**
- `coinrandom.random/uniform/randint/choice/choices/sample/shuffle/gauss`
- All async variants: `arandom/auniform/arandint/achoice/achoices/asample/ashuffle/agauss`
- `HeavyEngine` / `SuperHeavyEngine` — same methods
- `RandomProof` / `SuperProof` dataclass fields

**What this release includes (cumulative from 0.x):**
- Three-tier architecture: Light (~1ms) / Heavy (~2s) / SuperHeavy (~30s)
- Entropy sources: 3 exchanges (Binance, Upbit, Coinbase) + ETH + BTC block hashes
- Argon2id key stretching on all tiers
- Full async API via `asyncio.run_in_executor`
- `random_with_proof()` / `arandom_with_proof()` with verifiable audit trail
- Entropy quality warning when fewer than 4/5 sources respond
- No API keys required

---

## [0.3.0] - 2026-05-17

### Changed
- `RandomProof.block_hash: str` → `block_hashes: dict[str, str]` — structured access: `proof.block_hashes["ETH"]`, `proof.block_hashes["BTC"]`
- `SuperProof` same field rename
- README usage examples updated

---

## [0.2.2] - 2026-05-17

### Added
- Heavy/SuperHeavy: BTC block hash added as independent entropy source (Blockstream + mempool.space, race pattern)
- `proof.block_hash` now combines both chains: `"ETH:0x... | BTC:000..."`
- Entropy source count updated to 5 (3 exchanges + ETH + BTC); warning threshold raised to `< 4`

---

## [0.2.1] - 2026-05-17

### Changed
- Heavy/SuperHeavy: emit `warnings.warn` when fewer than 3 of 4 entropy sources (3 exchanges + ETH block hash) respond successfully
- README: fix `random_with_proof()` usage example (returns `RandomProof`, not a tuple)
- README: add proof JSON serialization example using `dataclasses.asdict()`

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
