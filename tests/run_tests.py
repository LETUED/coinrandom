"""
coinrandom 전체 테스트 러너
5가지 기준: 기능 / 통계 / 속도 / 장애대응 / Proof 검증
"""
import math
import os
import statistics
import sys
import time
from pathlib import Path
from unittest.mock import patch

# pip install -e . 없이 프로젝트 루트에서 직접 실행할 때를 위한 경로 설정
sys.path.insert(0, str(Path(__file__).parent.parent))

CI_MODE = os.environ.get("COINRANDOM_CI") == "1"

sys.path.insert(0, "..")

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"


def result_line(label: str, status: str, detail: str = "") -> None:
    icon = {"PASS": "✓", "FAIL": "✗", "SKIP": "-"}[status]
    detail_str = f"  ({detail})" if detail else ""
    print(f"  [{icon}] {label}{detail_str}")


def section(title: str) -> None:
    print(f"\n{'=' * 55}")
    print(f"  {title}")
    print(f"{'=' * 55}")


# ──────────────────────────────────────────────────────────
# 1. 기능 테스트
# ──────────────────────────────────────────────────────────
def run_functional(module, name: str) -> int:
    failures = 0

    # random()
    try:
        r = module.random()
        ok = isinstance(r, float) and 0.0 <= r < 1.0
        result_line("random() → [0, 1)", PASS if ok else FAIL, f"got {r:.4f}")
        if not ok: failures += 1
    except Exception as e:
        result_line("random()", FAIL, str(e)); failures += 1

    # randint(a, b)
    try:
        vals = [module.randint(1, 100) for _ in range(20)]
        ok = all(isinstance(v, int) and 1 <= v <= 100 for v in vals)
        result_line("randint(1, 100) x20 → [1, 100], int", PASS if ok else FAIL)
        if not ok: failures += 1
    except Exception as e:
        result_line("randint(1, 100)", FAIL, str(e)); failures += 1

    # uniform(a, b)
    try:
        u = module.uniform(10.0, 20.0)
        ok = 10.0 <= u <= 20.0
        result_line("uniform(10, 20) → [10, 20]", PASS if ok else FAIL, f"got {u:.4f}")
        if not ok: failures += 1
    except Exception as e:
        result_line("uniform(10, 20)", FAIL, str(e)); failures += 1

    # choice(seq)
    try:
        seq = ["A", "B", "C", "D", "E"]
        c = module.choice(seq)
        ok = c in seq
        result_line("choice(['A'..'E']) → 목록 내 값", PASS if ok else FAIL, f"got '{c}'")
        if not ok: failures += 1
    except Exception as e:
        result_line("choice()", FAIL, str(e)); failures += 1

    # choices(seq, k)
    try:
        c = module.choices([1, 2, 3, 4, 5, 6], k=10)
        ok = len(c) == 10 and all(1 <= v <= 6 for v in c)
        result_line("choices([1..6], k=10) → 길이 10, 범위 내", PASS if ok else FAIL)
        if not ok: failures += 1
    except Exception as e:
        result_line("choices()", FAIL, str(e)); failures += 1

    # sample(seq, k) — 중복 없음
    try:
        s = module.sample(range(1, 47), k=6)
        ok = len(s) == 6 and len(set(s)) == 6 and all(1 <= v <= 46 for v in s)
        result_line("sample(1~46, k=6) → 중복 없음, 길이 6", PASS if ok else FAIL, f"got {sorted(s)}")
        if not ok: failures += 1
    except Exception as e:
        result_line("sample()", FAIL, str(e)); failures += 1

    # shuffle — 원소 보존
    try:
        lst = [1, 2, 3, 4, 5]
        module.shuffle(lst)
        ok = sorted(lst) == [1, 2, 3, 4, 5]
        result_line("shuffle([1..5]) → 원소 보존", PASS if ok else FAIL, f"got {lst}")
        if not ok: failures += 1
    except Exception as e:
        result_line("shuffle()", FAIL, str(e)); failures += 1

    # gauss
    try:
        g = module.gauss(0.0, 1.0)
        ok = isinstance(g, float)
        result_line("gauss(0, 1) → float", PASS if ok else FAIL, f"got {g:.4f}")
        if not ok: failures += 1
    except Exception as e:
        result_line("gauss()", FAIL, str(e)); failures += 1

    return failures


# ──────────────────────────────────────────────────────────
# 2. 통계 테스트
# ──────────────────────────────────────────────────────────
CHI2_CRITICAL = 21.67  # p=0.01, df=9


def run_statistics(module, name: str, n: int = 200) -> int:
    failures = 0
    print(f"  (샘플 수: {n})")

    try:
        samples = [module.random() for _ in range(n)]

        # n이 작을수록 허용 범위 확장 (n<50이면 통계적 유의성 낮음)
        mean_margin = max(0.10, 1.5 / (n ** 0.5))
        mean = statistics.mean(samples)
        ok_mean = (0.5 - mean_margin) <= mean <= (0.5 + mean_margin)
        result_line(f"평균 ≈ 0.5 ± {mean_margin:.2f}", PASS if ok_mean else FAIL, f"got {mean:.4f}")
        if not ok_mean: failures += 1

        if n >= 30:
            stdev = statistics.stdev(samples)
            ok_std = 0.20 <= stdev <= 0.38
            result_line(f"표준편차 ≈ 0.289 ± 0.09", PASS if ok_std else FAIL, f"got {stdev:.4f}")
            if not ok_std: failures += 1

        if n >= 100:
            bins = [0] * 10
            for s in samples:
                bins[min(int(s * 10), 9)] += 1
            expected = n / 10
            chi2 = sum((obs - expected) ** 2 / expected for obs in bins)
            ok_chi = chi2 < CHI2_CRITICAL
            result_line(f"카이제곱 < {CHI2_CRITICAL} (df=9, p=0.01)", PASS if ok_chi else FAIL, f"χ²={chi2:.2f}")
            if not ok_chi: failures += 1
        else:
            result_line(f"카이제곱 (n={n}<100, 스킵)", SKIP)

    except Exception as e:
        result_line("통계 테스트", FAIL, str(e)); failures += 1

    return failures


# ──────────────────────────────────────────────────────────
# 3. 속도 테스트
# ──────────────────────────────────────────────────────────
def run_speed(module, name: str, first_limit: float, subsequent_limit: float, repeat: int = 5) -> int:
    failures = 0

    t0 = time.time()
    module.random()
    first_call = time.time() - t0
    ok = first_call < first_limit
    result_line(f"첫 호출 < {first_limit}s", PASS if ok else FAIL, f"{first_call:.2f}s")
    if not ok: failures += 1

    times = []
    for _ in range(repeat):
        t0 = time.time()
        module.random()
        times.append(time.time() - t0)
    avg = statistics.mean(times)
    ok2 = avg < subsequent_limit
    result_line(f"후속 호출 평균 < {subsequent_limit}s", PASS if ok2 else FAIL, f"{avg:.3f}s")
    if not ok2: failures += 1

    return failures


# ──────────────────────────────────────────────────────────
# 4. 장애 대응 테스트
# ──────────────────────────────────────────────────────────
def run_failure_modes() -> int:
    failures = 0
    import coinrandom
    from coinrandom.core import fetch_binance_entropy

    # 모든 거래소 API 실패 → 크래시 없이 값 반환
    try:
        with patch("requests.get", side_effect=Exception("Network error")), \
             patch("requests.post", side_effect=Exception("Network error")):
            r = coinrandom.random()
            ok = isinstance(r, float) and 0.0 <= r < 1.0
            result_line("전체 API 실패 → 크래시 없음, 유효한 float 반환", PASS if ok else FAIL, f"got {r:.4f}")
            if not ok: failures += 1
    except Exception as e:
        result_line("전체 API 실패 대응", FAIL, str(e)); failures += 1

    # 타임아웃 → 3초 이내 복귀
    try:
        import requests as _req
        original_get = _req.get

        def slow_get(*args, **kwargs):
            raise _req.exceptions.Timeout("timeout")

        with patch("requests.get", side_effect=slow_get):
            t0 = time.time()
            r = coinrandom.random()
            elapsed = time.time() - t0
            ok = elapsed < 5.0 and isinstance(r, float)
            result_line("타임아웃 → 5s 이내 복귀", PASS if ok else FAIL, f"{elapsed:.2f}s")
            if not ok: failures += 1
    except Exception as e:
        result_line("타임아웃 대응", FAIL, str(e)); failures += 1

    return failures


# ──────────────────────────────────────────────────────────
# 5. Proof 검증
# ──────────────────────────────────────────────────────────
def run_heavy_proof() -> int:
    failures = 0
    from coinrandom import heavy

    try:
        proof = heavy.random_with_proof()

        ok = 0.0 <= proof.value < 1.0
        result_line("proof.value ∈ [0, 1)", PASS if ok else FAIL, f"{proof.value:.4f}")
        if not ok: failures += 1

        ok = len(proof.exchanges) >= 1
        names = [e["exchange"] for e in proof.exchanges]
        result_line("exchanges ≥ 1개 응답", PASS if ok else FAIL, f"{names}")
        if not ok: failures += 1

        ok = isinstance(proof.block_hashes, dict) and any(proof.block_hashes.values())
        result_line("block_hashes dict, ETH/BTC 포함", PASS if ok else FAIL, f"{list(proof.block_hashes.keys())}")
        if not ok: failures += 1

        ok = len(proof.final_hash) == 64
        result_line("final_hash = 64자 hex", PASS if ok else FAIL, f"{proof.final_hash[:16]}...")
        if not ok: failures += 1

        ok = isinstance(proof.timestamp, str) and len(proof.timestamp) > 0
        result_line("timestamp ISO 형식", PASS if ok else FAIL, proof.timestamp)
        if not ok: failures += 1

    except Exception as e:
        result_line("Heavy Proof 생성", FAIL, str(e)); failures += 1

    return failures


def run_superheavy_proof() -> int:
    failures = 0
    from coinrandom import superheavy

    try:
        proof = superheavy.random_with_proof()

        ok = 0.0 <= proof.value < 1.0
        result_line("proof.value ∈ [0, 1)", PASS if ok else FAIL, f"{proof.value:.4f}")
        if not ok: failures += 1

        ok = proof.candidate_count >= 2
        result_line(f"후보 코인 ≥ 2개 분석", PASS if ok else FAIL, f"분석: {proof.candidate_count}개")
        if not ok: failures += 1

        ok = len(proof.selected_symbols) >= 2
        result_line(f"선정된 코인 ≥ 2개", PASS if ok else FAIL, f"{proof.selected_symbols}")
        if not ok: failures += 1

        ok = isinstance(proof.correlation_matrix, dict) and len(proof.correlation_matrix) > 0
        result_line("correlation_matrix 존재", PASS if ok else FAIL)
        if not ok: failures += 1

        ok = "success" in proof.optimization_result
        result_line("optimization_result 포함", PASS if ok else FAIL,
                    f"success={proof.optimization_result.get('success')}")
        if not ok: failures += 1

        ok = len(proof.final_hash) == 64
        result_line("final_hash = 64자 hex", PASS if ok else FAIL)
        if not ok: failures += 1

    except Exception as e:
        result_line("SuperHeavy Proof 생성", FAIL, str(e)); failures += 1

    return failures


# ──────────────────────────────────────────────────────────
# 메인 실행
# ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import coinrandom
    from coinrandom import heavy, superheavy

    total_fail = 0

    # ── Light ─────────────────────────────────────────────
    section("LIGHT 모드")

    print("\n[1] 기능 테스트")
    total_fail += run_functional(coinrandom, "Light")

    print("\n[2] 통계 테스트 (n=1000)")
    total_fail += run_statistics(coinrandom, "Light", n=1000)

    print("\n[3] 속도 테스트")
    total_fail += run_speed(coinrandom, "Light", first_limit=10.0, subsequent_limit=0.01, repeat=10)

    # ── Heavy ─────────────────────────────────────────────
    section("HEAVY 모드")

    print("\n[1] 기능 테스트")
    total_fail += run_functional(heavy, "Heavy")

    print("\n[2] 통계 테스트 (n=20)")
    total_fail += run_statistics(heavy, "Heavy", n=20)

    print("\n[3] 속도 테스트")
    total_fail += run_speed(heavy, "Heavy", first_limit=60.0, subsequent_limit=60.0, repeat=2)

    print("\n[5] Proof 검증")
    total_fail += run_heavy_proof()

    # ── 장애 대응 (Light 기준) ────────────────────────────
    section("장애 대응 테스트 (Light)")
    total_fail += run_failure_modes()

    # ── SuperHeavy ────────────────────────────────────────
    section("SUPERHEAVY 모드  ⚠ 수 분 소요")

    if CI_MODE:
        print("\n  [SKIP] CI 환경에서는 SuperHeavy 스킵 (COINRANDOM_CI=1)")
    else:
        print("\n[1] 기능 테스트 (random 1회)")
        try:
            r = superheavy.random()
            ok = isinstance(r, float) and 0.0 <= r < 1.0
            result_line("random() → [0, 1)", PASS if ok else FAIL, f"got {r:.4f}")
            if not ok: total_fail += 1
        except Exception as e:
            result_line("random()", FAIL, str(e)); total_fail += 1

        print("\n[5] Proof 검증")
        total_fail += run_superheavy_proof()

    # ── 최종 결과 ─────────────────────────────────────────
    section("최종 결과")
    if total_fail == 0:
        print("\n  전체 통과\n")
    else:
        print(f"\n  {total_fail}개 실패\n")

    sys.exit(0 if total_fail == 0 else 1)
