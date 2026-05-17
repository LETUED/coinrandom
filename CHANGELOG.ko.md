# 변경 이력

[English](CHANGELOG.md) | 한국어

이 프로젝트의 주요 변경사항을 버전별로 기록합니다.

형식: [Semantic Versioning](https://semver.org/)

---

## [미출시]

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
