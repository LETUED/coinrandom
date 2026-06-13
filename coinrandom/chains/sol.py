from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter

_ENDPOINTS = [
    "https://api.mainnet-beta.solana.com",
    "https://solana.publicnode.com",
]

_session = requests.Session()
_session.headers["User-Agent"] = "coinrandom/2.0 (+https://github.com/LETUED/coinrandom)"
_session.mount("https://", HTTPAdapter(pool_connections=1, pool_maxsize=3))


def _fetch_from(endpoint: str) -> tuple[bytes, str]:
    slot = _session.post(endpoint, json={
        "jsonrpc": "2.0", "method": "getSlot",
        "params": [{"commitment": "finalized"}], "id": 1,
    }, timeout=5).json()["result"]

    # Some keyless RPCs (e.g. solana.publicnode.com) lag ~50 slots behind the
    # finalized slot they report, so getBlock(slot-2) is "not available" there.
    # slot-150 (~60s old) is served by every endpoint, keeping real redundancy.
    block = _session.post(endpoint, json={
        "jsonrpc": "2.0", "method": "getBlock",
        "params": [slot - 150, {
            "transactionDetails": "accounts",
            "maxSupportedTransactionVersion": 0,
            "rewards": False,
        }],
        "id": 2,
    }, timeout=8).json().get("result", {})

    block_hash = block.get("blockhash", "")
    raw = block_hash.encode() if block_hash else b""
    for tx in block.get("transactions", [])[:30]:
        meta = tx.get("meta") or {}
        pre = meta.get("preBalances", [])[:8]
        post = meta.get("postBalances", [])[:8]
        for v in pre + post:
            try:
                raw += int(v).to_bytes(8, "big")
            except (OverflowError, ValueError, TypeError):
                continue  # skip an out-of-range/garbage balance

    return raw, block_hash


def fetch_entropy() -> tuple[bytes, str]:
    with ThreadPoolExecutor(max_workers=len(_ENDPOINTS)) as ex:
        futures = {ex.submit(_fetch_from, ep): ep for ep in _ENDPOINTS}
        for f in as_completed(futures):
            try:
                raw, block_hash = f.result()
                if raw:
                    return raw, block_hash
            except Exception:
                continue
    return b"", ""
