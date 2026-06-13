"""
Standard / Heavy 단계별 타이밍 측정
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def ts(label: str):
    class _T:
        def __enter__(self):
            self._s = time.perf_counter()
            return self
        def __exit__(self, *_):
            elapsed = time.perf_counter() - self._s
            print(f"  {elapsed:6.3f}s  {label}")
    return _T()


def bench_standard():
    print("\n=== STANDARD 단계별 타이밍 ===")
    from coinrandom.standard.engine import (
        _fetch_binance, _fetch_upbit, _fetch_coinbase,
        _argon2_stretch, STANDARD_SYMBOLS,
    )
    from coinrandom.chains.eth import fetch_entropy as fetch_eth
    from coinrandom.chains.btc import fetch_entropy as fetch_btc
    from coinrandom.chains.sol import fetch_entropy as fetch_sol
    from coinrandom.core import mix_entropy

    with ts("Binance (15 심볼 병렬)"):
        raw_b, _ = _fetch_binance(STANDARD_SYMBOLS)
    with ts("Upbit   (8 심볼 병렬)"):
        raw_u, _ = _fetch_upbit(STANDARD_SYMBOLS)
    with ts("Coinbase(9 심볼 병렬)"):
        raw_c, _ = _fetch_coinbase(STANDARD_SYMBOLS)
    with ts("ETH 블록 (PREVRANDAO + Uniswap)"):
        fetch_eth()
    with ts("BTC 블록해시"):
        fetch_btc()
    with ts("SOL 블록 잔액"):
        fetch_sol()

    mixed = mix_entropy(raw_b + raw_u + raw_c)
    salt = os.urandom(16)
    with ts("Argon2  (t=4, 64MB)"):
        _argon2_stretch(mixed, salt)


def bench_heavy():
    print("\n=== HEAVY 단계별 타이밍 ===")
    import numpy as np
    from scipy.optimize import minimize
    from coinrandom.heavy.optimizer import (
        _build_correlation_matrix, CANDIDATE_SYMBOLS,
    )

    with ts(f"Klines 수집 ({len(CANDIDATE_SYMBOLS)}개 병렬)"):
        corr, valid = _build_correlation_matrix(CANDIDATE_SYMBOLS)

    print(f"         유효 코인: {len(valid)}개")
    k = len(valid)

    def objective(w): return -float(w @ (1 - corr) @ w)
    def jac(w): return -2 * (1 - corr) @ w

    with ts("SLSQP 최적화"):
        minimize(
            objective, np.ones(k) / k, jac=jac, method="SLSQP",
            bounds=[(0, 1)] * k,
            constraints=[{"type": "eq", "fun": lambda w: np.sum(w) - 1}],
            options={"ftol": 1e-9, "maxiter": 1000},
        )

    print("         → 이후 Standard 파이프라인 (위 측정값 합산)")


if __name__ == "__main__":
    bench_standard()
    bench_heavy()
    print()
