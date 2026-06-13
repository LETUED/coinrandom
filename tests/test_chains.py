"""chains/* parsers with canned responses — no network.

Covers the happy path and graceful handling of malformed payloads (the most
likely silent-breakage point when a public API changes its JSON shape).
"""
from coinrandom.chains import btc, eth, sol


class FakeResp:
    def __init__(self, data=None, text=""):
        self._data = data
        self.text = text
        self.status_code = 200

    def json(self):
        return self._data


def test_btc_parse(monkeypatch):
    monkeypatch.setattr(btc._session, "get", lambda url, timeout=5: FakeResp(text="0000abc\n"))
    raw, h = btc.fetch_entropy()
    assert h == "0000abc"
    assert raw == b"0000abc"


def _eth_post(block_result, logs_result):
    def fake_post(url, json=None, timeout=5):
        if json["method"] == "eth_getBlockByNumber":
            return FakeResp({"result": block_result})
        return FakeResp({"result": logs_result})
    return fake_post


def test_eth_parse(monkeypatch):
    monkeypatch.setattr(
        eth._session, "post",
        _eth_post({"number": "0x10", "mixHash": "0xabcd"}, [{"data": "0x1234"}]),
    )
    raw, ident = eth.fetch_entropy()
    assert ident == "0xabcd"
    assert raw.startswith(b"0xabcd")
    assert raw.endswith(bytes.fromhex("1234"))


def test_eth_falls_back_to_hash_when_no_mixhash(monkeypatch):
    monkeypatch.setattr(
        eth._session, "post",
        _eth_post({"number": "0x10", "hash": "0xdead"}, []),
    )
    raw, ident = eth.fetch_entropy()
    assert ident == "0xdead"


def test_eth_malformed_log_is_skipped_not_fatal(monkeypatch):
    # odd-length / non-hex log data must not drop the whole source
    monkeypatch.setattr(
        eth._session, "post",
        _eth_post({"number": "0x10", "mixHash": "0xabcd"}, [{"data": "0xZZZ"}, {"data": "0x12"}]),
    )
    raw, ident = eth.fetch_entropy()
    assert ident == "0xabcd"
    assert raw.startswith(b"0xabcd")
    assert raw.endswith(bytes.fromhex("12"))


def _sol_post(block_result):
    def fake_post(url, json=None, timeout=8):
        if json["method"] == "getSlot":
            return FakeResp({"result": 100})
        return FakeResp({"result": block_result})
    return fake_post


def test_sol_parse(monkeypatch):
    block = {"blockhash": "solhash", "transactions": [
        {"meta": {"preBalances": [1, 2], "postBalances": [3, 4]}},
    ]}
    monkeypatch.setattr(sol._session, "post", _sol_post(block))
    raw, bh = sol.fetch_entropy()
    assert bh == "solhash"
    assert raw.startswith(b"solhash")
    # 4 balances * 8 bytes after the hash
    assert raw == b"solhash" + b"".join(int(v).to_bytes(8, "big") for v in (1, 2, 3, 4))


def test_sol_out_of_range_balance_is_skipped(monkeypatch):
    block = {"blockhash": "h", "transactions": [
        {"meta": {"preBalances": [2**70, -5, 7], "postBalances": []}},
    ]}
    monkeypatch.setattr(sol._session, "post", _sol_post(block))
    raw, bh = sol.fetch_entropy()
    assert bh == "h"
    # only the valid 7 is encoded; 2**70 (overflow) and -5 (negative) skipped
    assert raw == b"h" + (7).to_bytes(8, "big")
