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

이는 **Kerckhoffs의 원칙** 적용이다: 보안은 알고리즘의 비밀성이 아니라 시장의 예측 불가능성에 달려 있다. 모든 값에는 어떤 시장 데이터가 결과를 만들었는지 보여주는 `RandomProof`(검증 가능한 감사 기록)가 함께 제공된다.

**정직한 한계:** coinrandom은 *계산적 보안*(AES/RSA와 동일)을 제공하며, *정보이론적 보안*(Chainlink VRF 등)은 아니다. 신뢰 모델은 경제학적이지 수학적이지 않다. 암호화 키 생성에는 `secrets`를, 스마트컨트랙트 RNG에는 Chainlink VRF를 사용하라.

---

## 설치

```bash
pip install coinrandom                # Standard
pip install "coinrandom[heavy]"       # + Heavy (numpy, scipy 포함)
```

API 키 불필요. 별도 설정 없음.

---

## 2티어 구조

| 티어 | 속도 | entropy 소스 | 증명서 | 용도 |
|------|------|-------------|--------|------|
| **Standard** (기본) | ~2s | 3거래소 + ETH·BTC·SOL 블록데이터 + Argon2id | 있음 | 래플, NFT 민팅, DAO 투표 |
| **Heavy** | ~30s | 역포트폴리오 최적화로 선정된 코인 + Standard 파이프라인 | 있음 | 최대 entropy, 감사 가능 |

두 티어 모두 호출마다 전체 entropy 파이프라인을 실행하며, Python `random` 모듈과 동일한 API — 완전한 드롭인 교체.

---

## 사용법

### 함수 목록

| 함수 | 시그니처 | 설명 |
|------|----------|------|
| `random()` | `() → float` | [0.0, 1.0) 균등분포 실수 |
| `uniform(a, b)` | `(float, float) → float` | [a, b] 균등분포 실수 |
| `randint(a, b)` | `(int, int) → int` | [a, b] 균등분포 정수 (양 끝 포함) |
| `choice(seq)` | `(Sequence) → Any` | 시퀀스에서 1개 무작위 선택 |
| `choices(seq, k)` | `(Sequence, int) → list` | 복원 추출 k개 |
| `sample(seq, k)` | `(Sequence, int) → list` | 비복원 추출 k개 (중복 없음) |
| `shuffle(seq)` | `(MutableSequence) → None` | 제자리 셔플 |
| `gauss(mu, sigma)` | `(float, float) → float` | 정규분포 샘플 |
| `random_with_proof()` | `() → RandomProof` | 값 + 감사 기록 (Heavy는 `HeavyProof`) |

모든 함수는 `a` 접두사를 붙인 비동기 버전 제공: `arandom()`, `arandint()`, `arandom_with_proof()` 등.

---

### Standard (기본)

호출마다 3개 거래소(Binance·Upbit·Coinbase) + ETH·BTC·SOL 블록데이터를 실시간 수집 후 Argon2id(t=4, m=64MB) 적용. `RandomProof`에 전체 감사 기록 포함.

```python
import coinrandom

# 기본
coinrandom.random()                        # 0.7182818...  [0.0, 1.0) 실수
coinrandom.uniform(1.5, 9.5)              # 6.234...      [a, b] 실수
coinrandom.randint(1, 6)                  # 4             [a, b] 정수 (양 끝 포함)
coinrandom.gauss(mu=0.0, sigma=1.0)       # -0.312...     정규분포

# 시퀀스
coinrandom.choice(["가위", "바위", "보"])             # 1개 선택
coinrandom.choices(range(1, 7), k=5)                 # 주사위 5번 (복원 추출)
coinrandom.sample(range(1, 46), k=6)                 # 로또 번호 (중복 없음)

lst = list(range(1, 11))
coinrandom.shuffle(lst)                              # 제자리 셔플

# 실전: 감사 가능한 래플 — 참가자 중 당첨자 선정
participants = ["Alice", "Bob", "Carol", "Dave", "Eve"]
proof = coinrandom.random_with_proof()
winner = participants[int(proof.value * len(participants))]

print(winner)
print(proof.value)               # 0.3571428...
print(proof.block_hashes)        # {"ETH": "0xabc123...", "BTC": "000...", "SOL": "..."}
print(proof.exchanges)           # [{"exchange": "binance", "symbol": "BTCUSDT", ...}, ...]
print(proof.symbols)             # entropy에 쓰인 심볼 목록
print(proof.final_hash)          # Argon2 스트레칭 결과의 SHA-256
print(proof.timestamp)           # "2026-06-13T09:00:00.123456+00:00"
```

### Heavy — 포트폴리오 최적화 entropy

역 Markowitz 최적화로 **가장 상관관계가 낮은 코인**을 entropy 소스로 선정한 뒤 Standard 파이프라인을 실행한다. `[heavy]` extra 필요.

```python
from coinrandom import heavy  # 필요: pip install "coinrandom[heavy]"

val   = heavy.random()
proof = heavy.random_with_proof()

print(proof.value)
print(proof.selected_symbols)       # 역포트폴리오 최적화로 선정된 코인들
print(proof.candidate_count)        # 분석한 후보 코인 수
print(proof.correlation_matrix)     # 후보 코인 간 상관관계 행렬
print(proof.optimization_result)    # scipy SLSQP 최적화 결과
print(proof.block_hashes)           # {"ETH": "...", "BTC": "...", "SOL": "..."}
print(proof.final_hash)

# 실전: NFT 민팅 순서 셔플 — proof를 저장하면 결과를 누구나 검증 가능
token_ids = list(range(1, 10001))
heavy.shuffle(token_ids)
```

### 증명서 JSON 저장

`RandomProof`와 `HeavyProof`는 일반 dataclass — 표준 라이브러리로 바로 저장 가능:

```python
import dataclasses, json
import coinrandom

proof = coinrandom.random_with_proof()

with open("proof.json", "w") as f:
    json.dump(dataclasses.asdict(proof), f, indent=2, ensure_ascii=False)
```

### Async API

모든 함수는 `a` 접두사를 붙인 비동기 버전 제공.

```python
import asyncio
import coinrandom
from coinrandom import heavy  # heavy는 [heavy] extra 필요

async def main():
    # Standard
    val = await coinrandom.arandom()
    n   = await coinrandom.arandint(1, 100)
    c   = await coinrandom.achoice(["a", "b", "c"])
    lst = [1, 2, 3]
    await coinrandom.ashuffle(lst)
    proof = await coinrandom.arandom_with_proof()
    print(proof.block_hashes)

    # Heavy
    val   = await heavy.arandom()
    proof = await heavy.arandom_with_proof()
    print(proof.selected_symbols)

asyncio.run(main())
```

비동기 메서드는 `asyncio.run_in_executor`로 블로킹 I/O를 스레드풀에 위임 — 추가 의존성 없음.

---

## 설계 원칙

1. **API 키 없음** — `pip install` 한 줄로 바로 사용
2. **동일한 API** — 모든 티어가 `random`과 동일한 함수명 제공
3. **Mersenne Twister 미사용** — 자체 HashDRBG (SHA-512 카운터 방식), 코인 시장 데이터 + OS 하드웨어 entropy 결합
4. **오픈소스 안전** — Kerckhoffs의 원칙: 알고리즘 공개가 보안을 해치지 않음
5. **의도적으로 무거움** — 호출마다 전체 entropy 파이프라인 실행. "느리다 = 조작 비용이 높다"

---

## 내부 구조

```
coinrandom/
├── __init__.py          # Standard 티어를 기본 API로 export
├── core.py              # mix_entropy, bytes_to_float
├── proof.py             # RandomProof, HeavyProof 데이터클래스
├── chains/              # 블록체인 entropy 소스 (eth, btc, sol)
├── standard/            # 3거래소 + ETH·BTC·SOL + Argon2 (t=4, m=64MB)
└── heavy/               # 역포트폴리오 최적화(optimizer) → Standard 파이프라인
```

### HashDRBG

SHA-512 카운터 기반 자체 DRBG. 코드베이스 어디에도 `import random` 없음.

```python
# 단순화된 구조
state = argon2(mix_entropy(coin_data, os.urandom(32)))
output = sha512(state + counter)  # 호출마다
```

### 조작 저항성

Standard 모드를 조작하려면 Binance, Upbit, Coinbase의 여러 코인을 동시에 원하는 방향으로 움직이면서 ETH·BTC·SOL 블록까지 통제해야 한다 — 추정 필요 자금: 수천억~수조 원. Heavy는 최적화 실행 전까지 어떤 코인이 선정될지 알 수 없어 공격 대상을 사전 특정 불가.

---

## 다른 RNG와 비교

| | Python random | secrets | Random.org | Chainlink VRF | **coinrandom** |
|--|:-:|:-:|:-:|:-:|:-:|
| entropy 소스 | 시스템 시드 | OS pool | 대기 잡음 | 블록체인 | 코인 시장 |
| 암호학적 안전 | ✗ | ✓ | △ | ✓ | ✓ |
| 검증 가능 | ✗ | ✗ | △ | ✓ | ✓ |
| API 키 불필요 | ✓ | ✓ | ✗ | ✗ | **✓** |
| 무료 | ✓ | ✓ | 제한 | ✗ | **✓** |
| pip install | ✓ | ✓ | ✗ | ✗ | **✓** |

---

## 라이센스

MIT
