from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter

_ENDPOINTS = [
    "https://blockstream.info/api/blocks/tip/hash",
    "https://mempool.space/api/blocks/tip/hash",
]

_session = requests.Session()
_session.mount("https://", HTTPAdapter(pool_connections=1, pool_maxsize=2))


def _fetch_from(endpoint: str) -> tuple[bytes, str]:
    h = _session.get(endpoint, timeout=5).text.strip()
    return h.encode(), h


def fetch_entropy() -> tuple[bytes, str]:
    with ThreadPoolExecutor(max_workers=len(_ENDPOINTS)) as ex:
        futures = {ex.submit(_fetch_from, ep): ep for ep in _ENDPOINTS}
        for f in as_completed(futures):
            try:
                raw, h = f.result()
                if raw:
                    return raw, h
            except Exception:
                continue
    return b"", ""
