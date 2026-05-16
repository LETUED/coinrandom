from .engine import HeavyEngine

_engine = HeavyEngine()

random = _engine.random
uniform = _engine.uniform
randint = _engine.randint
choice = _engine.choice
choices = _engine.choices
sample = _engine.sample
shuffle = _engine.shuffle
gauss = _engine.gauss
random_with_proof = _engine.random_with_proof

__all__ = [
    "random", "uniform", "randint", "choice", "choices",
    "sample", "shuffle", "gauss", "random_with_proof",
]
