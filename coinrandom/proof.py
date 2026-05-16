from dataclasses import dataclass
from typing import Any


@dataclass
class RandomProof:
    value: float
    timestamp: str
    exchanges: list[dict]
    symbols: list[str]
    block_hash: str
    argon2_params: dict
    final_hash: str


@dataclass
class SuperProof:
    value: float
    timestamp: str
    exchanges: list[dict]
    block_hash: str
    argon2_params: dict
    candidate_count: int
    selected_symbols: list[str]
    correlation_matrix: dict[str, dict[str, float]]
    optimization_result: dict[str, Any]
    final_hash: str
