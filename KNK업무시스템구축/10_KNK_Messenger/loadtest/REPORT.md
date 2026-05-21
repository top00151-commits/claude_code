# KNK 메신저 75명 부하 테스트 결과 보고서

> 대표 지시 2026-05-20 / 빅터 작성

## 1. 테스트 환경
- **서버**: Synology NAS Docker (가정: CPU 4코어, RAM 4~8GB, HDD)
- **WSGI**: gunicorn + eventlet 단일 worker
- **DB**: SQLite (WAL 모드 적용 — Phase 2 보강 `3d3862a`)
- **격리**: `loadtest_001~075@knktest.local` 계정 + `[LOADTEST]` 방
- **클라이언트**: PowerShell wrapper + Python ThreadPoolExecutor (대표 PC, HTTPS)

## 2. 결과 요약

| 시나리오 | 성공률 | p50 | p95 | wall | 평가 |
|---|---|---|---|---|---|
| 5MB × 1 | 100% | 20.87s | 20.87s | 20.87s | ⚠️ cold start 지연 |
| 5MB × 5 | 80% (4/5) | 1.39s | 1.47s | 1.50s | ⚠️ 1건 실패 |
| 5MB × 20 | 100% | 4.70s | 5.38s | 5.44s | ✅ 안정 |
| 5MB × 75 | **100%** | 17.99s | 20.49s | 20.67s | ✅ **75명 사진 OK** |
| 30MB × 75 | **0%** | 30.07s | 30.83s | 32.16s | 🔴 **전부 실패** |
| 100MB × 75 | **0%** | 30.96s | 32.07s | 38.20s | 🔴 **전부 실패** |

## 3. 핵심 결론

### ✅ 안전 영역
- **75명 × 5MB 사진** — 100% 성공, 응답시간 p95 20초 이내
- 처리량 ~18 MB/s (1Gbps 라인의 14.5% 사용)
- 현장 사진 다량 업로드 시나리오는 안정

### 🔴 한계 영역
- **75명 × 30MB+ 도면** — 100% 실패
- 응답시간이 정확히 30초 근처에 clustering → **gunicorn worker_timeout 30초 cut 명백**
- 7.5GB 동시 (100MB×75) 는 NAS HDD + 단일 worker 가 처리 불가

## 4. 결정적 병목

**1순위 — gunicorn worker_timeout (기본 30초)**
- 75개 30MB 파일을 단일 eventlet worker 가 30초 내 처리 못함
- SIGKILL 후 모든 요청 동시 실패

**2순위 — 단일 eventlet worker**
- in-memory state (presence, rate_buckets) 가 worker 단일 가정
- 멀티 worker 로 가려면 Redis 도입 별건 작업 필요

**3순위 — NAS HDD I/O**
- 75개 동시 디스크 쓰기 = head thrash
- SSD 면 큰 향상 기대

## 5. 권장 보강 (우선순위)

### 즉시 적용 (Phase 4 — 빅터가 만들고 대표 OK 시 sync)
1. **gunicorn --timeout 300 --graceful-timeout 60** 추가
   - 단일 fix 로 30MB×75 통과 가능성 큼
   - `run_gunicorn.sh` 수정 필요 (NAS 안에 있어 대표님이 SSH 로 내용 확인 필요)

### 중기 검토
2. **gunicorn worker 수 늘림** (4-8개) + **Redis 도입**
   - in-memory state 를 Redis 로 이관
   - 멀티 worker → 75명 × 30MB 안정 가능
3. **NAS HDD → SSD 업그레이드**
   - 가장 큰 효과지만 비용 발생

### 사용자 운영 가이드
- 사진(5MB 내외): 75명 동시 OK
- 일반 문서(10MB 내외): 보강 전엔 30~50명 권장
- 도면(30MB+): 보강 전엔 5~10명 동시 권장. 큰 도면은 시간차 업로드

## 6. 부가 관찰

### 5MB × 1 단독이 20초 걸린 이유
- cold start 비용 (SSL handshake + session setup + 첫 INSERT)
- 이후 5MB × 75 도 비슷한 ~20초 → 5MB 업로드 자체가 NAS HDD 한계로 ~20초 걸림
- 의미: **개별 파일 업로드 자체가 매우 느림** (HDD 라면 1.5 Gbps NAS LAN 보다 디스크 쓰기가 병목일 수 있음)

### 5MB × 5 에서 1건 실패
- 80% 성공률 (4/5)
- 빠른 응답시간(1.5초) 에 실패 — DB 또는 디스크 락 일시 충돌 추정
- 통계적 의미는 미미하지만 안정성 측면에서 추가 조사 가치 있음

## 7. 빅터가 준비한 보강 도구

- `cleanup_only.ps1` / `CLEANUP.bat` — 잔존 테스트 데이터 정리 (대표님 메신저에서 loadtest_* 계정 보이면 사용)
- `retest_30mb.bat` — gunicorn 보강 후 30MB×75 만 재실측 (별도 작성 예정)

## 8. 다음 단계 (대표님 확인 후)

1. NAS 의 `run_gunicorn.sh` 내용 빅터에게 공유
2. 빅터가 timeout 추가 + 재배포
3. `retest_30mb.bat` 으로 재실측
4. 결과 비교 → 추가 보강 필요 여부 판단
