from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter

_RPC_ENDPOINTS = [
    "https://eth.llamarpc.com",
    "https://rpc.ankr.com/eth",
    "https://ethereum.publicnode.com",
    "https://cloudflare-eth.com",
]

_UNISWAP_POOLS = [
    "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",  # USDC/ETH 0.05%
    "0x4585FE77225b41b697C938B018E2ac67Ac5a20c0",  # WBTC/ETH 0.05%
    "0x11b815efB8f581194ae79006d24E0d814B7697F6",  # ETH/USDT 0.05%
]
# keccak256("Swap(address,address,int256,int256,uint160,uint128,int24)")
_SWAP_TOPIC = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"

_session = requests.Session()
_session.mount("https://", HTTPAdapter(pool_connections=1, pool_maxsize=4))


def _fetch_from(endpoint: str) -> tuple[bytes, str]:
    block = _session.post(endpoint, json={
        "jsonrpc": "2.0", "method": "eth_getBlockByNumber",
        "params": ["latest", False], "id": 1,
    }, timeout=5).json()["result"]

    block_num = block["number"]
    # mixHash = PREVRANDAO after EIP-4399 (The Merge)
    identifier = block.get("mixHash") or block.get("hash", "")

    logs = _session.post(endpoint, json={
        "jsonrpc": "2.0", "method": "eth_getLogs",
        "params": [{"address": _UNISWAP_POOLS, "topics": [_SWAP_TOPIC],
                    "fromBlock": hex(int(block_num, 16) - 5), "toBlock": block_num}],
        "id": 2,
    }, timeout=5).json().get("result", [])

    raw = identifier.encode()
    for log in logs:
        data = log.get("data", "")
        if len(data) > 2:
            raw += bytes.fromhex(data[2:])

    return raw, identifier


def fetch_entropy() -> tuple[bytes, str]:
    with ThreadPoolExecutor(max_workers=len(_RPC_ENDPOINTS)) as ex:
        futures = {ex.submit(_fetch_from, ep): ep for ep in _RPC_ENDPOINTS}
        for f in as_completed(futures):
            try:
                raw, identifier = f.result()
                if raw:
                    return raw, identifier
            except Exception:
                continue
    return b"", ""
