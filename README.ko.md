# coinrandom

> 코인 시장 데이터를 entropy source로 쓰는 Python 랜덤 라이브러리

[English](README.md) | 한국어

```python
import coinrandom

coinrandom.random()        # 0.7182818...
coinrandom.randint(1, 100) # 42
coinrandom.choice(["a", "b", "c"])
```

---

## 왜 coinrandom인가?

암호화폐 시장은 24시간 365일 전 세계에서 거래된다. 개별 체결(tick) 수준 — 정확한 가격, 수량, 타임스탬프, 매수/매도 방향 — 에서의 데이터는 고도로 예측 불가능하다.

효율적 시장 가설(EMH)은 "아무도 단기 시장을 일관되게 예측할 수 없다"고 말한다. **coinrandom은 이 예측 불가능성을 entropy source로 사용한다.**

### 신뢰 모델

> 소스코드가 전부 공개되어도, 코인 시장은 사전에 예측할 수 없으므로 출력값은 예측 불가능하다.

이는 **Kerckhoffs의 원칙** 적용이다: 보안은 알고리즘의 비밀성이 아니라 시장의 예측 불가능성에 달려 있다. Heavy/SuperHeavy의 각 값에는 어떤 시장 데이터가 결과를 만들었는지 보여주는 `RandomProof`(검증 가능한 감사 기록)가 함께 제공된다.

**정직한 한계:** coinrandom은 *계산적 보안*(AES/RSA와 동일)을 제공하며, *정보이론적 보안*(Chainlink VRF 등)은 아니다. 신뢰 모델은 경제학적이지 수학적이지 않다. 암호화 키 생성에는 `secrets`를, 스마트컨트랙트 RNG에는 Chainlink VRF를 사용하라.

---

## 설치

```bash
pip install coinrandom                     # Light + Heavy
pip install "coinrandom[superheavy]"       # + SuperHeavy (numpy, scipy 포함)
```

API 키 불필요. 별도 설정 없음.

---

## 3티어 구조

| 티어 | 속도 | entropy 소스 | 증명서 | 용도 |
|------|------|-------------|--------|------|
| **Light** | ~1ms | Binance tick + Argon2 | 없음 | 대량 생성 |
| **Heavy** | ~2s | 3거래소 + ETH + BTC 블록해시 + Argon2 | 있음 | 래플, NFT 민팅, DAO 투표 |
| **SuperHeavy** | ~30s | 포트폴리오 최적화로 선정된 코인 + Heavy 파이프라인 (ETH + BTC) | 있음 | 최대 entropy, 감사 가능 |

모든 티어는 Python `random` 모듈과 동일한 API — 완전한 드롭인 교체.

---

## 사용법

### Light (기본)

```python
import coinrandom

coinrandom.random()              # float in [0.0, 1.0)
coinrandom.uniform(1.5, 9.5)
coinrandom.randint(1, 100)
coinrandom.choice(["a", "b", "c"])
coinrandom.choices(["a", "b", "c"], k=5)
coinrandom.sample(range(100), k=10)

lst = [1, 2, 3, 4, 5]
coinrandom.shuffle(lst)

coinrandom.gauss(mu=0.0, sigma=1.0)
```

### Heavy — 증명서 포함

```python
from coinrandom.heavy import HeavyEngine

engine = HeavyEngine()
proof = engine.random_with_proof()

print(proof.value)              # 0.3571428...
print(proof.exchanges)          # [{"exchange": "binance", "symbol": "BTCUSDT", ...}, ...]
print(proof.block_hashes)       # {"ETH": "0xabc123...", "BTC": "000000000000..."}
print(proof.block_hashes["ETH"])
print(proof.block_hashes["BTC"])
print(proof.final_hash)         # Argon2 스트레칭 결과의 SHA-256
```

### SuperHeavy — 포트폴리오 최적화 entropy

```python
from coinrandom.superheavy import SuperHeavyEngine

engine = SuperHeavyEngine()
proof = engine.random_with_proof()

print(proof.selected_symbols)       # 역포트폴리오 최적화로 선정된 코인들
print(proof.correlation_matrix)     # 후보 코인 간 상관관계 행렬
print(proof.optimization_result)    # scipy SLSQP 최적화 결과
```

### 증명서 JSON 저장

`RandomProof`와 `SuperProof`는 일반 dataclass — 표준 라이브러리로 바로 저장 가능:

```python
import dataclasses, json

proof = engine.random_with_proof()

with open("proof.json", "w") as f:
    json.dump(dataclasses.asdict(proof), f, indent=2, ensure_ascii=False)
```

SuperHeavy는 역 Markowitz 포트폴리오 최적화를 실행해 **가장 상관관계가 낮은 코인**을 entropy source로 선정한다 — entropy 다양성을 수학적으로 극대화.

### Async API

모든 티어는 모든 함수의 비동기 버전을 제공한다 — 이름 앞에 `a`를 붙인 형태.

```python
import asyncio
import coinrandom
from coinrandom import heavy, superheavy  # superheavy는 [superheavy] extra 필요

async def main():
    # Light
    val = await coinrandom.arandom()
    n   = await coinrandom.arandint(1, 100)
    c   = await coinrandom.achoice(["a", "b", "c"])
    lst = [1, 2, 3]
    await coinrandom.ashuffle(lst)

    # Heavy
    val   = await heavy.arandom()
    proof = await heavy.arandom_with_proof()
    print(proof.block_hash)

    # SuperHeavy
    val   = await superheavy.arandom()
    proof = await superheavy.arandom_with_proof()
    print(proof.selected_symbols)

asyncio.run(main())
```

비동기 메서드는 `asyncio.run_in_executor`로 블로킹 I/O를 스레드풀에 위임한다 — 추가 의존성 없음.

---

## 설계 원칙

1. **API 키 없음** — `pip install` 한 줄로 바로 사용
2. **동일한 API** — 모든 티어가 `random`과 동일한 함수명 제공
3. **stdlib random 미사용** — 자체 HashDRBG (SHA-512 카운터 방식), Mersenne Twister 완전 배제
4. **오픈소스 안전** — Kerckhoffs의 원칙: 알고리즘 공개가 보안을 해치지 않음
5. **의도적으로 무거움** — Heavy/SuperHeavy는 호출마다 전체 entropy 파이프라인 실행. "느리다 = 조작 비용이 높다"

---

## 내부 구조

```
coinrandom/
├── __init__.py          # Light 티어를 기본 API로 export
├── core.py              # fetch_binance_entropy, mix_entropy
├── proof.py             # RandomProof, SuperProof 데이터클래스
├── light/               # HashDRBG + Argon2 (t=1, m=8MB) reseed 캐싱
├── heavy/               # 3거래소 병렬 + ETH 블록해시 + Argon2 (t=4, m=64MB)
└── superheavy/          # 역포트폴리오 최적화 → Heavy 파이프라인
```

### HashDRBG

SHA-512 카운터 기반 자체 DRBG. 코드베이스 어디에도 `import random` 없음.

```python
# 단순화된 구조
state = argon2(mix_entropy(coin_data, os.urandom(32)))
output = sha512(state + counter)  # 호출마다
```

### 조작 저항성

Heavy 모드를 조작하려면 Binance, Upbit, Coinbase의 32개 이상 코인을 동시에 원하는 방향으로 움직여야 한다 — 추정 필요 자금: 수천억~수조 원. SuperHeavy는 최적화 실행 전까지 어떤 코인이 선정될지 알 수 없어 공격 대상을 사전 특정 불가.

---

## 다른 RNG와 비교

| | Python random | secrets | Random.org | Chainlink VRF | **coinrandom Heavy** |
|--|:-:|:-:|:-:|:-:|:-:|
| entropy 소스 | 시스템 시드 | OS pool | 대기 잡음 | 블록체인 | 코인 시장 |
| 암호학적 안전 | ✗ | ✓ | △ | ✓ | ✓ |
| 검증 가능 | ✗ | ✗ | △ | ✓ | ✓ |
| API 키 불필요 | ✓ | ✓ | ✗ | ✗ | **✓** |
| 무료 | ✓ | ✓ | 제한 | ✗ | **✓** |
| pip install | ✓ | ✓ | ✗ | ✗ | **✓** |

---

## 버전 정책

[Semantic Versioning](https://semver.org/) 준수:

- `PATCH` — 버그 수정, 내부 개선
- `MINOR` — 하위 호환 기능 추가
- `MAJOR` — 안정 API 선언 또는 호환성 파괴 변경

현재 `0.x` — API 안정화 진행 중. `1.0.0` 이전까지 MINOR에서 API 변경 가능.

---

## 라이센스

MIT
