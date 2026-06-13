from dataclasses import dataclass
from typing import Any


@dataclass
class RandomProof:
    value: float
    timestamp: str
    exchanges: list[dict]
    symbols: list[str]
    block_hashes: dict[str, str]   # {"ETH": "0x...", "BTC": "000...", "SOL": "..."}
    argon2_params: dict
    final_hash: str


@dataclass
class HeavyProof:
    value: float
    timestamp: str
    exchanges: list[dict]
    block_hashes: dict[str, str]   # {"ETH": "0x...", "BTC": "000...", "SOL": "..."}
    argon2_params: dict
    candidate_count: int
    selected_symbols: list[str]
    correlation_matrix: dict[str, dict[str, float]]
    optimization_result: dict[str, Any]
    final_hash: str
