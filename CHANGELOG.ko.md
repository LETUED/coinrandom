# 변경 이력

[English](CHANGELOG.md) | 한국어

이 프로젝트의 주요 변경사항을 버전별로 기록합니다.

형식: [Semantic Versioning](https://semver.org/)

---

## [미출시]

---

## [2.0.1] - 2026-06-13

### 수정
- 죽은 `rpc.ankr.com` ETH/SOL 엔드포인트(이제 API 키 필수 → 조용한 401/403) 제거, 검증된 keyless RPC로 교체하고 불안정한 `eth.llamarpc.com`/`cloudflare-eth.com` 제외. 블록체인 entropy 티어의 다중 엔드포인트 이중화를 복구.
- Heavy optimizer가 `api.binance.com` 지역 차단(US/클라우드 IP에서 HTTP 451) 시 조용히 no-op으로 퇴화하던 문제 수정: klines를 keyless 공개 미러 `data-api.binance.vision`에서 먼저 가져오고 `api.binance.com`을 폴백으로 사용. Standard 티어의 Binance trades도 동일 미러 사용.
- Heavy optimizer: 분산이 0인(수익률이 평평한) 코인이 `NaN`을 만들어 우선 선정되거나 proof JSON에 유효하지 않은 `NaN`이 새어 들어가던 문제 수정(`np.nan_to_num`). `<2` 유효 코인 폴백이 항등행렬을 실제 데이터가 있는 심볼과 짝지음.
- `random()`/`uniform()`/`gauss()`가 문서화된 `[0.0, 1.0)` 구간을 보장 — `bytes_to_float`가 64비트를 `2**64`로 나눠 정확히 `1.0`으로 반올림될 수 있던 것을 53비트 매핑(CPython 방식)으로 변경.
- `random` 드롭인 호환: `randint(a, b)`에서 `a > b`는 `ValueError`, `choice([])`는 `IndexError`, `sample(seq, k)`에서 `k > len`/`k < 0`은 `ValueError` — 모두 entropy 파이프라인 실행 전에 검증(기존엔 모호한 `ZeroDivisionError` 또는 조용히 틀린 값).
- 체인 파서가 잘못된 데이터 하나(잘못된 hex 로그 / 범위 초과 Solana 잔액) 때문에 소스 전체를 버리지 않고 건너뜀.

### 변경
- 모든 외부 요청에 설명적 `User-Agent` 추가 — WAF/Cloudflare 오탐 차단 감소.
- `requests` floor를 `>=2.32.4`로 상향(CVE-2024-47081, CVE-2024-35195 해결); `numpy`/`scipy` floor를 검증된 버전으로 정렬.
- CI를 결정론 오프라인 테스트 게이트(pytest, Python 3.10–3.13 매트릭스)와 비차단 라이브 스모크 잡으로 분리 — 외부 서비스 장애가 더 이상 빌드를 깨지 않음. Heavy optimizer가 이제 오프라인 단위 테스트로 커버됨.

---

## [2.0.0] - 2026-06-13

### 변경 (호환성 파괴)
- 티어 재구성 — 저보안 `Light` 티어를 제거하고 나머지 티어를 한 단계씩 내림:
  - `Heavy` → **`Standard`**, 이제 기본 API (`coinrandom.random()`). 호출마다 전체 entropy 파이프라인(3거래소 + ETH/BTC/SOL 블록데이터 + Argon2id t=4, m=64MB) 실행.
  - `SuperHeavy` → **`Heavy`** (`coinrandom.heavy`). 역포트폴리오 최적화 + Standard 파이프라인. `[heavy]` extra 필요.
- `SuperProof` 데이터클래스를 **`HeavyProof`**로 개명.
- optional-dependency 그룹 `[superheavy]` → **`[heavy]`** (numpy, scipy)로 개명.
- `coinrandom.random_with_proof()`를 최상위(Standard 티어)에서 바로 호출 가능 — `RandomProof` 반환.

### 제거 (호환성 파괴)
- `Light` 티어 및 `coinrandom.light` 모듈 — ~1ms Binance 전용 / Argon2(t=1, m=8MB) 티어 제거. 이제 보안 전체 파이프라인이 기본.
- `coinrandom.superheavy` 모듈 — `coinrandom.heavy` 사용.

### 마이그레이션
- `pip install "coinrandom[superheavy]"` → `pip install "coinrandom[heavy]"`
- `from coinrandom import superheavy` → `from coinrandom import heavy`
- 기존 `from coinrandom import heavy`(전체 파이프라인) → `coinrandom` 최상위 또는 `from coinrandom import standard` 사용
- `Light`(`coinrandom.random()` 1ms 티어) → 직접 대체 없음. 기본값이 보안 파이프라인으로 바뀜
- `SuperProof` → `HeavyProof`

---

## [1.2.0] - 2026-05-18

### 추가
- Solana 블록 데이터를 7번째 entropy 소스로 추가 (`coinrandom/chains/sol.py`)
  - `getBlock` + `transactionDetails: "accounts"` — 최대 30개 트랜잭션의 preBalances + postBalances
  - 공개 RPC 3개 동시 경쟁 (Solana mainnet-beta, Ankr, PublicNode)
  - ETH/BTC validator 집합과 완전 독립
  - `RandomProof.block_hashes`에 `"SOL"` 키 추가
- `chains/` 패키지 구조 — 체인 추가 시 파일 하나만 추가하는 확장 가능한 구조
  - `chains/eth.py` — ETH PREVRANDAO (EIP-4399 `mixHash`) + Uniswap V3 swap 로그
  - `chains/btc.py` — BTC 블록 해시
  - `chains/sol.py` — SOL 블록 잔액 데이터
- ETH entropy 개선: `block.hash` → `block.mixHash` (PREVRANDAO) — validator RANDAO 흡수

### 변경
- entropy 소스 티어 분리: 블록체인 소스(ETH/BTC/SOL)는 tier 1(가용성 보장), CEX 소스는 tier 2(품질 향상)
- 블록체인 소스 전체 실패 시 `warnings.warn` 대신 `RuntimeError` 발생
- 경고 임계값 업데이트: `5/6` 미만 (기존 `4/6`)

### 제거
- `coinrandom/dex.py` — 로직을 `coinrandom/chains/eth.py`로 통합

---

## [1.1.0] - 2026-05-18

### 추가
- Uniswap V3 온체인 Swap 데이터를 6번째 entropy 소스로 추가 (`coinrandom/dex.py`)
  - 풀: USDC/ETH, WBTC/ETH, ETH/USDT (0.05% 티어)
  - raw JSON-RPC로 Swap 이벤트 로그 직접 읽기 — 신규 의존성 없음
  - 공개 RPC 엔드포인트 4개 동시 경쟁 (LlamaNodes, Ankr, Cloudflare, PublicNode)
  - 온체인 데이터: MITM 불가, 중앙화 거래소 API 의존성 없음
- entropy 경고 임계값 업데이트: `4/6` 소스 (기존 `4/5`)

---

## [1.0.1] - 2026-05-18

### 수정
- `gauss()`: HashDRBG가 `0.0`을 반환할 때 `log(0)` 크래시 방지 — 전 티어(Light, Heavy, SuperHeavy) rejection loop 추가
- Fork Safety: `os.register_at_fork(after_in_child=...)` 추가 — `os.fork()` 후 자식 프로세스에서 DRBG 강제 재시드, prefork 서버(Gunicorn, uWSGI) 동일 시퀀스 생성 방지

---

## [1.0.0] - 2026-05-17

### 안정 API 선언

공개 API가 동결됩니다. 이후 호환성 파괴 변경은 새로운 메이저 버전이 필요합니다.

**동결된 API:**
- `coinrandom.random/uniform/randint/choice/choices/sample/shuffle/gauss`
- 전체 async 버전: `arandom/auniform/arandint/achoice/achoices/asample/ashuffle/agauss`
- `HeavyEngine` / `SuperHeavyEngine` — 동일 메서드
- `RandomProof` / `SuperProof` 데이터클래스 필드

**이 릴리스 포함 내용 (0.x 전체 누적):**
- 3티어 아키텍처: Light (~1ms) / Heavy (~2s) / SuperHeavy (~30s)
- Entropy 소스: 3거래소 (Binance, Upbit, Coinbase) + ETH + BTC 블록 해시
- 전 티어 Argon2id 키 스트레칭
- `asyncio.run_in_executor` 기반 전체 async API
- `random_with_proof()` / `arandom_with_proof()` — 검증 가능한 감사 기록
- 5개 소스 중 4개 미만 응답 시 엔트로피 품질 경고
- API 키 불필요

---

## [0.3.0] - 2026-05-17

### 변경
- `RandomProof.block_hash: str` → `block_hashes: dict[str, str]` — 구조적 접근: `proof.block_hashes["ETH"]`, `proof.block_hashes["BTC"]`
- `SuperProof` 동일 필드명 변경
- README 사용 예시 업데이트

---

## [0.2.2] - 2026-05-17

### 추가
- Heavy/SuperHeavy: BTC 블록 해시를 독립 entropy 소스로 추가 (Blockstream + mempool.space, 경쟁 패턴)
- `proof.block_hash`가 두 체인을 포함: `"ETH:0x... | BTC:000..."`
- entropy 소스 수 5개로 증가 (3거래소 + ETH + BTC); 경고 threshold `< 4`로 상향

---

## [0.2.1] - 2026-05-17

### 변경
- Heavy/SuperHeavy: 4개 entropy 소스(3거래소 + ETH 블록해시) 중 3개 미만 응답 시 `warnings.warn` 발생
- README: `random_with_proof()` 사용 예시 오류 수정 (튜플이 아닌 `RandomProof` 단일 객체 반환)
- README: `dataclasses.asdict()`를 이용한 증명서 JSON 저장 예시 추가

---

## [0.2.0] - 2026-05-17

### 추가
- 전 티어 async API — `arandom()`, `auniform()`, `arandint()`, `achoice()`, `achoices()`, `asample()`, `ashuffle()`, `agauss()`
- Heavy/SuperHeavy: `arandom_with_proof()` 비동기 버전 추가
- 모든 async 함수는 `asyncio.run_in_executor` 기반 — 새 의존성 없음, FastAPI/aiohttp 등 모든 asyncio 프레임워크와 호환

---

## [0.1.3] - 2026-05-17

### 변경
- 전 티어: Light (`core.py`)와 SuperHeavy optimizer (`optimizer.py`)에 `requests.Session` + `HTTPAdapter` 커넥션 풀 적용
- Light: Binance entropy fetch 병렬화 (3심볼 동시 수집)
- SuperHeavy klines 수집: ~1.94s → ~1.04s (46% 개선)
- GitHub Actions: `checkout@v4→v5`, `setup-python@v5→v6`
- CI: Python 매트릭스(3.10/3.11/3.12/3.13) → 3.13 단일화 (빠른 피드백)
- CI: `paths-ignore` 추가 — `.md`, `.gitignore`, `.gitattributes`, `LICENSE` 변경 시 CI 스킵

### 추가
- `coinrandom.__version__` — `importlib.metadata`로 런타임 버전 확인 가능
- `coinrandom/py.typed` — PEP 561 마커 (mypy/pyright 타입 체커 지원)

### 제거
- `coinrandom/functions.py` — 미사용 레거시 파일 삭제

---

## [0.1.2] - 2026-05-17

### 변경
- Heavy: 거래소별 모듈 레벨 `requests.Session` + `HTTPAdapter` 커넥션 풀 도입
- 반복 호출 시 TCP+TLS 핸드셰이크 오버헤드 감소 (연속 처리량 약 44% 개선)
- entropy 출력 및 증명서(Proof) 구조 변경 없음

---

## [0.1.1] - 2026-05-16

### 변경
- Heavy: 각 거래소 내 심볼 fetch 병렬화 (`_fetch_binance`, `_fetch_upbit`, `_fetch_coinbase`)
- Heavy: ETH 블록해시를 거래소 데이터와 동시 수집 (기존: 거래소 완료 후 순차)
- Heavy: ETH RPC 엔드포인트 4개 동시 경쟁 — 첫 성공 응답 사용
- Heavy 총 소요시간: ~17s → ~2s
- SuperHeavy 총 소요시간: ~30s → ~4s
- `tests/benchmark.py` 추가 — 단계별 타이밍 측정 스크립트

---

## [0.1.0] - 2026-05-16

### 추가
- 최초 릴리즈
- 3티어 구조: Light / Heavy / SuperHeavy
- Light: Binance tick + Argon2 (t=1, m=8MB), ~1ms
- Heavy: 3거래소 + ETH 블록해시 + Argon2 (t=4, m=64MB), RandomProof 포함
- SuperHeavy: 역 Markowitz 포트폴리오 최적화 → Heavy 파이프라인, SuperProof 포함
- Python `random` 모듈 완전 호환 API (`random`, `randint`, `uniform`, `choice`, `choices`, `sample`, `shuffle`, `gauss`)
- HashDRBG (SHA-512 카운터 방식), 코드베이스 내 stdlib `random` 미사용
- 한국어/영어 이중 README (한국어 주, 영어 부)
- CI: Python 3.10 / 3.11 / 3.12 / 3.13 매트릭스
- CD: 태그 `v*` 푸시 → PyPI 자동 배포 (OIDC Trusted Publisher)