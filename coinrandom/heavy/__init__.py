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

arandom = _engine.arandom
auniform = _engine.auniform
arandint = _engine.arandint
achoice = _engine.achoice
achoices = _engine.achoices
asample = _engine.asample
ashuffle = _engine.ashuffle
agauss = _engine.agauss
arandom_with_proof = _engine.arandom_with_proof

__all__ = [
    "random", "uniform", "randint", "choice", "choices",
    "sample", "shuffle", "gauss", "random_with_proof",
    "arandom", "auniform", "arandint", "achoice", "achoices",
    "asample", "ashuffle", "agauss", "arandom_with_proof",
]
