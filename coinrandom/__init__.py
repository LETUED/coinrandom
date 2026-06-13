from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("coinrandom")
except PackageNotFoundError:
    __version__ = "unknown"

# Standard 티어를 기본 API로 export
from .standard import (
    random, uniform, randint, choice, choices, sample, shuffle, gauss, random_with_proof,
    arandom, auniform, arandint, achoice, achoices, asample, ashuffle, agauss, arandom_with_proof,
)

__all__ = [
    "__version__",
    # sync
    "random", "uniform", "randint", "choice", "choices", "sample", "shuffle", "gauss",
    "random_with_proof",
    # async
    "arandom", "auniform", "arandint", "achoice", "achoices", "asample", "ashuffle", "agauss",
    "arandom_with_proof",
]
