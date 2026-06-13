# coinrandom

[한국어](README.ko.md) | English

> True random numbers sourced from live cryptocurrency market data.

```python
import coinrandom

coinrandom.random()        # 0.7182818...
coinrandom.randint(1, 100) # 42
coinrandom.choice(["a", "b", "c"])
```

---

## Why coinrandom?

Cryptocurrency markets trade 24/7 globally. At the tick level — individual trade prices, quantities, timestamps, and buyer/seller direction — the data is highly unpredictable. The Efficient Market Hypothesis (EMH) says no one can consistently predict short-term market movements. **coinrandom uses this unpredictability as an entropy source.**

### Trust Model

> Even with the full source code published, no one can predict the output in advance — because no one can predict the coin market.

This is an application of **Kerckhoffs's principle**: security depends on the unpredictability of the market, not on keeping the algorithm secret. Every value comes with a `RandomProof` — a verifiable audit trail showing exactly which market data produced the result.

**Honest limits:** coinrandom provides *computational security* (like AES/RSA), not *information-theoretic security* (like Chainlink VRF). The trust model is economic, not mathematical. For cryptographic key generation, use `secrets`. For smart contract RNG, use Chainlink VRF.

---

## Installation

```bash
pip install coinrandom                # Standard
pip install "coinrandom[heavy]"       # + Heavy (numpy, scipy)
```

No API keys. No configuration.

---

## Two Tiers

| Tier | Speed | Entropy source | Proof | Use case |
|------|-------|---------------|-------|----------|
| **Standard** (default) | ~2s | 3 exchanges + ETH/BTC/SOL block data + Argon2id | Yes | Raffles, NFT mints, DAO votes |
| **Heavy** | ~30s | Portfolio-optimized coins + Standard pipeline | Yes | Maximum entropy, auditable |

Both tiers run the full entropy pipeline on every call and return the same API — a drop-in replacement for Python's `random` module.

---

## Usage

### Function Reference

| Function | Signature | Description |
|----------|-----------|-------------|
| `random()` | `() → float` | Uniform float in [0.0, 1.0) |
| `uniform(a, b)` | `(float, float) → float` | Uniform float in [a, b] |
| `randint(a, b)` | `(int, int) → int` | Uniform integer in [a, b] inclusive |
| `choice(seq)` | `(Sequence) → Any` | One random element from a sequence |
| `choices(seq, k)` | `(Sequence, int) → list` | k elements with replacement |
| `sample(seq, k)` | `(Sequence, int) → list` | k elements without replacement |
| `shuffle(seq)` | `(MutableSequence) → None` | In-place shuffle |
| `gauss(mu, sigma)` | `(float, float) → float` | Normal distribution sample |
| `random_with_proof()` | `() → RandomProof` | Value + audit trail (Heavy returns `HeavyProof`) |

All functions have async variants prefixed with `a`: `arandom()`, `arandint()`, `arandom_with_proof()`, etc.

---

### Standard (default)

Each call fetches live data from 3 exchanges (Binance, Upbit, Coinbase) + ETH/BTC/SOL block data, then applies Argon2id (t=4, m=64MB). Returns a `RandomProof` with a full audit trail.

```python
import coinrandom

# Basic
coinrandom.random()                        # 0.7182818...  float in [0.0, 1.0)
coinrandom.uniform(1.5, 9.5)              # 6.234...      float in [a, b]
coinrandom.randint(1, 6)                  # 4             integer in [a, b] inclusive
coinrandom.gauss(mu=0.0, sigma=1.0)       # -0.312...     normal distribution

# Sequences
coinrandom.choice(["rock", "paper", "scissors"])   # pick one
coinrandom.choices(range(1, 7), k=5)               # roll dice 5 times (with replacement)
coinrandom.sample(range(1, 46), k=6)               # lotto numbers (no duplicates)

lst = list(range(1, 11))
coinrandom.shuffle(lst)                            # in-place shuffle

# Practical: auditable raffle — pick a winner from participants
participants = ["Alice", "Bob", "Carol", "Dave", "Eve"]
proof = coinrandom.random_with_proof()
winner = participants[int(proof.value * len(participants))]

print(winner)
print(proof.value)               # 0.3571428...
print(proof.block_hashes)        # {"ETH": "0xabc123...", "BTC": "000...", "SOL": "..."}
print(proof.exchanges)           # [{"exchange": "binance", "symbol": "BTCUSDT", ...}, ...]
print(proof.symbols)             # symbols used as entropy
print(proof.final_hash)          # SHA-256 of the Argon2-stretched entropy
print(proof.timestamp)           # "2026-06-13T09:00:00.123456+00:00"
```

### Heavy — portfolio-optimized entropy

Runs inverse Markowitz optimization to select the **least-correlated coins** as entropy sources before executing the Standard pipeline. Requires the `[heavy]` extra.

```python
from coinrandom import heavy  # requires: pip install "coinrandom[heavy]"

val   = heavy.random()
proof = heavy.random_with_proof()

print(proof.value)
print(proof.selected_symbols)       # coins selected by inverse portfolio optimization
print(proof.candidate_count)        # number of candidate coins analyzed
print(proof.correlation_matrix)     # correlation matrix of candidates
print(proof.optimization_result)    # scipy SLSQP result
print(proof.block_hashes)           # {"ETH": "...", "BTC": "...", "SOL": "..."}
print(proof.final_hash)

# Practical: NFT mint order — save proofs so anyone can verify the shuffle
token_ids = list(range(1, 10001))
heavy.shuffle(token_ids)
```

### Saving proof as JSON

`RandomProof` and `HeavyProof` are plain dataclasses — serialize with the standard library:

```python
import dataclasses, json
import coinrandom

proof = coinrandom.random_with_proof()

with open("proof.json", "w") as f:
    json.dump(dataclasses.asdict(proof), f, indent=2)
```

### Async API

All functions have async variants prefixed with `a`.

```python
import asyncio
import coinrandom
from coinrandom import heavy  # heavy requires the [heavy] extra

async def main():
    # Standard
    val = await coinrandom.arandom()
    n   = await coinrandom.arandint(1, 100)
    c   = await coinrandom.achoice(["a", "b", "c"])
    lst = [1, 2, 3]
    await coinrandom.ashuffle(lst)
    proof = await coinrandom.arandom_with_proof()
    print(proof.block_hashes)

    # Heavy
    val   = await heavy.arandom()
    proof = await heavy.arandom_with_proof()
    print(proof.selected_symbols)

asyncio.run(main())
```

Async methods offload blocking I/O to a thread pool via `asyncio.run_in_executor` — no new dependencies.

---

## Design Principles

1. **No API keys** — works out of the box with `pip install`
2. **Uniform API** — every tier exposes the same functions as `random`
3. **No Mersenne Twister** — custom HashDRBG (SHA-512 counter-based) seeded from coin market data and OS hardware entropy
4. **Open-source safe** — Kerckhoffs's principle: publishing the algorithm doesn't compromise security
5. **Intentionally heavy** — each call runs the full entropy pipeline. "Slow = costly to manipulate."

---

## Internals

```
coinrandom/
├── __init__.py          # Standard tier as default API
├── core.py              # mix_entropy, bytes_to_float
├── proof.py             # RandomProof, HeavyProof dataclasses
├── chains/              # blockchain entropy sources (eth, btc, sol)
├── standard/            # 3 exchanges + ETH/BTC/SOL + Argon2 (t=4, m=64MB)
└── heavy/               # inverse portfolio optimization → Standard pipeline
```

### HashDRBG

Custom SHA-512 counter-based DRBG. No `import random` anywhere in the codebase.

```python
# Simplified
state = argon2(mix_entropy(coin_data, os.urandom(32)))
output = sha512(state + counter)  # per call
```

### Manipulation resistance

Manipulating Standard mode requires simultaneously moving multiple coins across Binance, Upbit, and Coinbase in the exact direction needed while also controlling ETH/BTC/SOL blocks — estimated cost: billions of dollars. Heavy additionally hides the target coins until optimization runs.

---

## License

MIT
