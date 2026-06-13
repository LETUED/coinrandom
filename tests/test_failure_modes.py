"""Reliability contracts of _collect_entropy — no network.

Mocks the six source fetchers directly so the documented degradation behavior
(RuntimeError when no blockchain source responds; warning when <5/6 respond) is
actually exercised, which the live tests never reach.
"""
import warnings

import pytest

from coinrandom.standard import engine

SYMS = ["BTCUSDT", "ETHUSDT"]


def _patch(monkeypatch, *, binance=b"", upbit=b"", coinbase=b"",
           eth=b"", btc=b"", sol=b""):
    def mkt(name, sym, raw):
        return (raw, [{"exchange": name, "symbol": sym, "count": 1}] if raw else [])

    monkeypatch.setattr(engine, "_fetch_binance", lambda s: mkt("binance", "BTCUSDT", binance))
    monkeypatch.setattr(engine, "_fetch_upbit", lambda s: mkt("upbit", "KRW-BTC", upbit))
    monkeypatch.setattr(engine, "_fetch_coinbase", lambda s: mkt("coinbase", "BTC-USD", coinbase))
    monkeypatch.setattr(engine, "fetch_eth_entropy", lambda: (eth, "0xeth" if eth else ""))
    monkeypatch.setattr(engine, "fetch_btc_entropy", lambda: (btc, "btchash" if btc else ""))
    monkeypatch.setattr(engine, "fetch_sol_entropy", lambda: (sol, "solhash" if sol else ""))


def test_all_blockchain_fail_raises_runtimeerror(monkeypatch):
    # markets up, every blockchain source empty
    _patch(monkeypatch, binance=b"a", upbit=b"b", coinbase=b"c")
    with pytest.raises(RuntimeError):
        engine._collect_entropy(SYMS)


def test_degraded_sources_warn_but_return(monkeypatch):
    # only 1 of 6 sources active -> warn, but still produce entropy
    _patch(monkeypatch, eth=b"e")
    with pytest.warns(UserWarning):
        raw, records, block_hashes = engine._collect_entropy(SYMS)
    assert raw
    assert block_hashes["ETH"] == "0xeth"


def test_cex_down_chains_up_is_graceful(monkeypatch):
    # no market sources, all 3 chains up -> no crash, real block hashes
    _patch(monkeypatch, eth=b"e", btc=b"b", sol=b"s")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        raw, records, block_hashes = engine._collect_entropy(SYMS)
    assert raw
    assert block_hashes == {"ETH": "0xeth", "BTC": "btchash", "SOL": "solhash"}
    assert records == []  # no market exchanges contributed


def test_all_six_sources_no_warning(monkeypatch):
    _patch(monkeypatch, binance=b"a", upbit=b"b", coinbase=b"c",
           eth=b"e", btc=b"f", sol=b"g")
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # any warning becomes an error
        raw, records, block_hashes = engine._collect_entropy(SYMS)
    assert raw
    assert len(records) == 3
