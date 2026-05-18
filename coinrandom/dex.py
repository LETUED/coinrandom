from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter

_RPC_ENDPOINTS = [
    "https://eth.llamarpc.com",
    "https://rpc.ankr.com/eth",
    "https://cloudflare-eth.com",
    "https://ethereum.publicnode.com",
]

_POOLS = [
    "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",  # USDC/ETH 0.05%
    "0x4585FE77225b41b697C938B018E2ac67Ac5a20c0",  # WBTC/ETH 0.05%
    "0x11b815efB8f581194ae79006d24E0d814B7697F6",  # ETH/USDT 0.05%
]

# keccak256("Swap(address,address,int256,int256,uint160,uint128,int24)")
_SWAP_TOPIC = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"


def _make_session() -> requests.Session:
    s = requests.Session()
    a = HTTPAdapter(pool_connections=1, pool_maxsize=4)
    s.mount("https://", a)
    return s


_session = _make_session()


def _fetch_from(endpoint: str) -> bytes:
    r = _session.post(endpoint, json={
        "jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1
    }, timeout=5)
    block_num = int(r.json()["result"], 16)

    r = _session.post(endpoint, json={
        "jsonrpc": "2.0",
        "method": "eth_getLogs",
        "params": [{
            "address": _POOLS,
            "topics": [_SWAP_TOPIC],
            "fromBlock": hex(block_num - 5),
            "toBlock": hex(block_num),
        }],
        "id": 2,
    }, timeout=5)

    logs = r.json().get("result", [])
    raw = b""
    for log in logs:
        data = log.get("data", "")
        if len(data) > 2:
            raw += bytes.fromhex(data[2:])
    return raw


def fetch_uniswap_entropy() -> bytes:
    with ThreadPoolExecutor(max_workers=len(_RPC_ENDPOINTS)) as ex:
        futures = {ex.submit(_fetch_from, ep): ep for ep in _RPC_ENDPOINTS}
        for f in as_completed(futures):
            try:
                result = f.result()
                if result:
                    return result
            except Exception:
                continue
    return b""
