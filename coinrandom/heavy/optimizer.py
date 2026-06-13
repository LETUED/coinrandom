"""
역 포트폴리오 최적화로 최소 상관관계 코인 조합을 선정한다.
Markowitz 최대 분산화 포트폴리오와 동일한 수식:
    maximize  Σᵢ Σⱼ wᵢwⱼ(1 - ρᵢⱼ)
    s.t.      Σwᵢ = 1,  wᵢ >= 0
"""
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import requests
from requests.adapters import HTTPAdapter
from scipy.optimize import minimize

_session = requests.Session()
_session.headers["User-Agent"] = "coinrandom/2.0 (+https://github.com/LETUED/coinrandom)"
_session.mount("https://", HTTPAdapter(pool_connections=1, pool_maxsize=25))

CANDIDATE_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XMRUSDT", "LINKUSDT",
    "DOGEUSDT", "ATOMUSDT", "AVAXUSDT", "DOTUSDT", "LTCUSDT",
    "UNIUSDT", "AAVEUSDT", "MKRUSDT", "CRVUSDT", "MATICUSDT",
    "INJUSDT", "SUIUSDT", "SEIUSDT", "TIAUSDT", "RENDERUSDT",
]
# data-api.binance.vision is Binance's public market-data mirror — it is NOT
# geo-451-blocked from US/cloud IPs, unlike api.binance.com. Try it first so the
# Heavy optimizer keeps working everywhere; fall back to the main API.
KLINE_HOSTS = [
    "https://data-api.binance.vision",
    "https://api.binance.com",
]
TOP_N = 8


def _fetch_returns(symbol: str, limit: int = 60) -> tuple[str, list[float]]:
    for host in KLINE_HOSTS:
        try:
            resp = _session.get(
                host + "/api/v3/klines",
                params={"symbol": symbol, "interval": "1m", "limit": limit},
                timeout=5,
            )
            klines = resp.json()
            if not isinstance(klines, list) or len(klines) < 2:
                continue  # e.g. a 451 error body is a dict, not a kline list
            closes = [float(k[4]) for k in klines]
            returns = [closes[i] / closes[i - 1] - 1 for i in range(1, len(closes))]
            return symbol, returns
        except Exception:
            continue
    return symbol, []


def _build_correlation_matrix(symbols: list[str]) -> tuple[np.ndarray, list[str]]:
    returns_map: dict[str, list[float]] = {}

    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(_fetch_returns, s): s for s in symbols}
        for f in as_completed(futures):
            sym, rets = f.result()
            if len(rets) >= 30:
                returns_map[sym] = rets

    valid = list(returns_map.keys())
    if len(valid) < 2:
        # Not enough klines to measure correlation. Fall back to a non-empty
        # symbol set (assume independence) so the downstream pipeline still runs
        # — returning an empty selection would crash _collect_entropy.
        fallback = valid or symbols
        return np.eye(len(fallback)), fallback

    min_len = min(len(returns_map[s]) for s in valid)
    matrix = np.array([returns_map[s][:min_len] for s in valid])
    with np.errstate(invalid="ignore", divide="ignore"):
        corr = np.corrcoef(matrix)
    # A flat-return coin produces a NaN row/col; np.argsort would rank NaN last
    # and thus SELECT the degenerate coin, and NaN would leak into the proof JSON.
    # Treat unknown correlation as fully correlated (1.0) so it is de-prioritized.
    corr = np.nan_to_num(corr, nan=1.0)
    return corr, valid


def select_min_correlation_symbols(n: int = TOP_N) -> tuple[list[str], dict, dict]:
    print(f"  [Heavy] 후보 {len(CANDIDATE_SYMBOLS)}개 코인 수익률 데이터 수집 중...", flush=True)
    corr, valid = _build_correlation_matrix(CANDIDATE_SYMBOLS)
    print(f"  [Heavy] {len(valid)}개 유효, 상관관계 행렬 완성 → 최적화 시작", flush=True)
    k = len(valid)

    if k <= n:
        corr_dict = {valid[i]: {valid[j]: float(corr[i, j]) for j in range(k)} for i in range(k)}
        return valid, corr_dict, {"method": "all_selected", "n_candidates": k}

    def objective(w):
        return -float(w @ (1 - corr) @ w)

    def jac(w):
        return -2 * (1 - corr) @ w

    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
    bounds = [(0, 1)] * k
    w0 = np.ones(k) / k

    result = minimize(objective, w0, jac=jac, method="SLSQP",
                      bounds=bounds, constraints=constraints,
                      options={"ftol": 1e-9, "maxiter": 1000})

    top_idx = np.argsort(result.x)[-n:]
    selected = [valid[i] for i in top_idx]

    corr_dict = {
        valid[i]: {valid[j]: round(float(corr[i, j]), 4) for j in range(k)}
        for i in range(k)
    }
    opt_info = {
        "method": "SLSQP",
        "n_candidates": k,
        "success": bool(result.success),
        "objective_value": float(-result.fun),
        "weights": {valid[i]: round(float(result.x[i]), 4) for i in range(k)},
    }
    return selected, corr_dict, opt_info
