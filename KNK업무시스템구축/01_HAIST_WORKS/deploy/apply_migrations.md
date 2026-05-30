# 마이그레이션 패키지 — z109 / z110 / z115 적용 가이드

> **작성**: 빅터(01) · 2026-05-31 (v5H226z116)
> **목적**: 3종 마이그레이션 SQL을 NAS DB에 안전 일괄 적용
> **소요**: ~2분 (백업·적용·검증)

---

## 적용 대상 (3종)

| SQL | 추가 항목 | 발주 |
|---|---|---|
| `v5H226z109_employee_no.sql` | users 테이블 사번 컬럼 8개 + 인덱스 3개 | 메신저 사번 SSO Phase 2 |
| `v5H226z110_groupware_rename.sql` | app_settings `hiworks_*` → `groupware_*` 키 복사 (값 보존) | 외부 브랜드 익명화 후속 |
| `v5H226z115_task_photo.sql` | tasks 테이블 photo_path 컬럼 | daily 사진 첨부 (v3+) |

→ 세 마이그레이션은 **서로 독립** — 적용 순서 무관, 부분 적용도 안전.

---

## 적용 방법 (NAS 컨테이너 안)

### 1단계 — 상태 확인 (변경 0)
```bash
ssh -p 31201 root@o.knknara.co.kr
cd /opt/knk_haist
git pull   # 최신 코드 + SQL 파일 받기
bash deploy/apply_migrations.sh --check
```
→ 각 마이그레이션이 이미 적용됐는지만 확인. DB 변경 X.

### 2단계 — dry-run (시뮬레이션)
```bash
bash deploy/apply_migrations.sh --dry-run
```
→ 트랜잭션 시작 후 rollback. 실제 변경 X, 오류 가능성 사전 점검.

### 3단계 — 실제 적용
```bash
bash deploy/apply_migrations.sh
```
→ 자동 백업 → 3종 순차 적용 → 사후 검증. **2분 이내**.

### 4단계 — 서비스 재시작
```bash
supervisorctl restart knk-works
```
→ 코드가 새 컬럼 사용 시작.

---

## 안전 보장

| 단계 | 보장 |
|---|---|
| 0. 환경 점검 | sqlite3 / DB 파일 / 3개 SQL 모두 존재 확인 |
| 1. 상태 점검 | 이미 적용된 마이그레이션은 자동 skip |
| 2. 백업 | `data/backups/main.db.bak_z109z110z115_<TIMESTAMP>` |
| 3. 적용 | 실패 시 즉시 중단 + 백업 위치 안내 |
| 4. 검증 | PRAGMA table_info + 키 존재 검사 |

---

## 롤백 (긴급 시)

```bash
supervisorctl stop knk-works
cp /opt/knk_haist/data/backups/main.db.bak_z109z110z115_<TIMESTAMP> /opt/knk_haist/data/main.db
supervisorctl start knk-works
```

**5분 이내 완전 원복**. 백업 파일은 30일 보관 권장.

---

## 적용 후 효과

### z109 — 사번 컬럼 활성화
- `/login` 에서 사번(`5`, `VN001`) 로그인 가능
- 130명 일괄 import 가능: `python deploy/import_employees_from_excel.py ...`
- 메신저 SSO 연동 준비 완료

### z110 — 외부 그룹웨어 익명화 완성
- DB의 `hiworks_*` 키 값이 `groupware_*` 로 복사됨 (값 보존)
- 코드는 `groupware_*` 우선 조회 + `hiworks_*` fallback
- 사용자 입력 손실 0

### z115 — daily 사진 첨부 활성화
- 업무 카드에 사진 드래그앤드롭 + 클립보드(Ctrl+V) + 클릭 업로드
- `/uploads/tasks/user_{uid}/task_{tid}_{ts}.{ext}` 저장
- 단일 사진 (1 task = 1 photo), 10MB 이하, JPG/PNG/WebP/GIF

---

## 자주 묻는 질문

**Q. dry-run 후 실제 적용 안 했는데 안전한가?**
A. ✅ 트랜잭션 rollback 으로 DB 변경 0. 안전.

**Q. 일부만 적용 가능?**
A. ❌ 스크립트는 3종 일괄 처리. 개별 적용은 직접 sqlite3 호출:
```bash
sqlite3 data/main.db < migrations/v5H226z109_employee_no.sql
```

**Q. 이미 적용된 마이그레이션 다시 적용?**
A. 자동 skip. ALTER TABLE은 `IF NOT EXISTS` 미지원이지만 스크립트가 PRAGMA로 미리 검사.

**Q. 백업 파일 크기?**
A. 현재 DB 크기와 동일. `du -h data/main.db` 로 사전 확인 가능.

**Q. NAS 디스크 부족 시?**
A. 백업 안 만들고 적용은 위험. 먼저 디스크 정리:
```bash
df -h /opt
du -sh /opt/knk_haist/data/backups/  # 옛 백업 정리 후보
```

---

## 참조

- 마이그레이션 SQL: `01_HAIST_WORKS/migrations/`
- 작업기록: `작업기록/작업기록_2026-05-29_NAS배포_완료.md` §16 자산 인벤토리
- 비상복구 키트: `_재해복구키트_HAIST_WORKS/`

*작성: 빅터(Claude) · 2026-05-31*
