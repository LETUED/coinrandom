"""heavy/optimizer.py — inverse-portfolio selection with injected returns.

Pins the two correctness fixes: NaN from zero-variance coins must not select
the degenerate coin or leak into the (JSON) proof, and the <2-valid fallback
must pair eye() with the symbols that actually had data.
"""
import json

import numpy as np

from coinrandom.heavy import optimizer as opt


def _varied(seed):
    return [((i * (seed + 1)) % 5 - 2) / 100 for i in range(40)]


def patch_returns(monkeypatch, present, flat=()):
    def fake(sym, limit=60):
        if sym in flat:
            return sym, [0.0] * 40        # zero variance -> NaN row in corrcoef
        if sym in present:
            return sym, _varied(present.index(sym))
        return sym, []                    # no data
    monkeypatch.setattr(opt, "_fetch_returns", fake)


def test_corr_matrix_has_no_nan_with_flat_coin(monkeypatch):
    syms = ["A", "B", "C", "D"]
    patch_returns(monkeypatch, present=["A", "B", "C"], flat=["D"])
    corr, valid = opt._build_correlation_matrix(syms)
    assert np.isfinite(corr).all()
    assert corr.shape == (len(valid), len(valid))


def test_lt_two_valid_returns_eye_paired_with_valid(monkeypatch):
    # only one symbol has usable data -> eye(1) paired with that one symbol
    patch_returns(monkeypatch, present=["A"])
    corr, valid = opt._build_correlation_matrix(["A", "B", "C"])
    assert valid == ["A"]
    assert corr.shape == (1, 1)


def test_degenerate_coin_not_selected_and_proof_is_json(monkeypatch):
    candidates = opt.CANDIDATE_SYMBOLS
    flat = [candidates[0]]
    present = candidates[1:]
    patch_returns(monkeypatch, present=present, flat=flat)
    selected, corr_dict, info = opt.select_min_correlation_symbols(n=8)
    assert flat[0] not in selected
    assert len(selected) == 8
    # proof artifacts must be strictly valid JSON — allow_nan=False raises on NaN
    json.dumps({"corr": corr_dict, "info": info}, allow_nan=False)
    assert info["success"] is True
