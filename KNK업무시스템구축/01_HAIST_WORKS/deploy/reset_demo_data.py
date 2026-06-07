#!/usr/bin/env python3
# ============================================================
# HAIST WORKS — 데모/시드 데이터 초기화 (운영 시작 전 1회)
# v5H226z135 (2026-05-31)
# ------------------------------------------------------------
# 안전 설계:
#   · 기본 = 미리보기(dry-run): 무엇이 지워질지 출력만, 변경 0
#   · 실제 실행 = --apply --yes (이중 확인)
#   · --apply 시 자동 백업 먼저
#   · 보존(KEEP) 테이블 명시. 그 외 트랜잭션/데모 테이블만 비움
#   · 사용자: '사번(employee_no) 없는 + ceo 아닌' 데모/시드 계정만 삭제
#            (실제 직원·대표 계정은 절대 보존)
#   · demo_seed_off=1 설정 → 재시작 시 데모 재생성 차단
#
# 사용법 (NAS 컨테이너 안):
#   python3 deploy/reset_demo_data.py              # 미리보기(변경 0)
#   python3 deploy/reset_demo_data.py --apply --yes  # 실제 실행(백업 후)
# DB 경로 override: KNK_DB_PATH=/opt/knk_haist/data/knk.db
# ============================================================
import os, sys, shutil, sqlite3, datetime

DB = os.environ.get("KNK_DB_PATH", "/opt/knk_haist/data/knk.db")

# 보존할 구조/마스터 테이블 (절대 비우지 않음)
KEEP = {
    "teams", "app_settings",
    "permissions", "permission_groups", "group_permissions", "user_groups",
    "countries_master", "payment_terms", "exchange_rates",
    "workflow_nodes_master", "workflow_template_nodes", "workflow_templates",
    "boards",            # 게시판 구조 (글/댓글은 비움)
    "shared_contacts",   # 전사 주소록 — 유지 (초기화 대상 아님)
    "user_mail_creds",   # 메일 인증 (실사용자용)
    "sqlite_sequence",   # 시스템
    "users",             # 특별 처리(아래) — 데모/시드 계정만 삭제
}

# 데모/시드 사용자 판정: 사번 없음 + ceo 아님
DEMO_USER_WHERE = "(employee_no IS NULL OR TRIM(employee_no)='') AND COALESCE(role,'') <> 'ceo'"


def log(s=""): print(s)


def main():
    apply = "--apply" in sys.argv
    yes = "--yes" in sys.argv

    if not os.path.exists(DB):
        log(f"[ERROR] DB 없음: {DB}")
        sys.exit(1)

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("PRAGMA foreign_keys=OFF")

    tables = [r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()]
    clear_tables = sorted(t for t in tables if t not in KEEP)

    log("============================================================")
    log(f" HAIST WORKS 데모 초기화 — {'실제 실행(APPLY)' if apply else '미리보기(DRY-RUN)'}")
    log(f" DB: {DB}")
    log("============================================================")

    # 1) 비울 테이블 + 현재 행수
    log("\n[1] 비워질 테이블 (트랜잭션/데모):")
    total = 0
    nonempty = []
    for t in clear_tables:
        try:
            n = cur.execute(f"SELECT COUNT(*) FROM \"{t}\"").fetchone()[0]
        except Exception:
            n = 0
        total += n
        if n:
            nonempty.append((t, n))
    for t, n in sorted(nonempty, key=lambda x: -x[1]):
        log(f"    {t:34s} {n:>7,} 행")
    log(f"    (비어있는 표 {len(clear_tables)-len(nonempty)}개 생략) — 총 {total:,} 행 삭제 예정")

    # 2) 삭제될 데모/시드 사용자 — employee_no(사번) 컬럼 필수
    has_empno = any(r[1] == "employee_no" for r in cur.execute("PRAGMA table_info(users)").fetchall())
    user_delete_ok = has_empno
    log("\n[2] 삭제될 데모/시드 사용자 (사번 없음 + ceo 아님):")
    demo_users = []
    if not has_empno:
        log("    [건너뜀] users.employee_no 컬럼 없음 — z109 마이그레이션 후 가능. 사용자는 삭제 안 함.")
    else:
        demo_users = cur.execute(
            f"SELECT id, name, login_id, role, employee_no FROM users WHERE {DEMO_USER_WHERE} ORDER BY id"
        ).fetchall()
        for u in demo_users:
            log(f"    #{u['id']:<4} {(u['name'] or ''):10s} login={u['login_id'] or '-':12s} role={u['role'] or '-':8s} 사번={u['employee_no'] or '-'}")
        log(f"    → {len(demo_users)}명 삭제 예정")

    if has_empno:
        keep_users = cur.execute(f"SELECT COUNT(*) FROM users WHERE NOT ({DEMO_USER_WHERE})").fetchone()[0]
    else:
        keep_users = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    log(f"\n[3] 보존될 사용자(실제 직원·대표 등 사번보유/ceo): {keep_users}명")
    log(f"    보존 테이블: {', '.join(sorted(KEEP - {'users','sqlite_sequence'}))}")

    if not apply:
        log("\n[미리보기] 변경하지 않았습니다.")
        log("실제 실행: python3 deploy/reset_demo_data.py --apply --yes")
        con.close(); return

    if not yes:
        log("\n[중단] 실제 실행하려면 --yes 도 함께: --apply --yes")
        con.close(); sys.exit(2)

    # ── 실제 실행 ──
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = f"{DB}.bak_reset_{ts}"
    shutil.copy2(DB, bak)
    log(f"\n[백업] {bak}")

    deleted_rows = 0
    for t in clear_tables:
        try:
            cur.execute(f"DELETE FROM \"{t}\"")
            deleted_rows += cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
            # 자동증가 시퀀스 초기화 (완전 비운 표만)
            cur.execute("DELETE FROM sqlite_sequence WHERE name=?", (t,))
        except Exception as e:
            log(f"    [경고] {t} 삭제 실패: {e}")
    # 데모/시드 사용자 삭제 (사번 컬럼 있을 때만 — 안전)
    if user_delete_ok:
        cur.execute(f"DELETE FROM users WHERE {DEMO_USER_WHERE}")
        udel = cur.rowcount
    else:
        udel = 0
        log("    [건너뜀] users.employee_no 없음 — 사용자 삭제 안 함")
    # 운영 모드 — 데모 재시드 차단
    cur.execute(
        "INSERT INTO app_settings(key, value) VALUES('demo_seed_off','1') "
        "ON CONFLICT(key) DO UPDATE SET value='1'"
    )
    con.commit()
    try:
        con.execute("VACUUM")
    except Exception:
        pass
    con.close()

    log(f"\n[완료] 트랜잭션/데모 테이블 비움 · 데모 사용자 {udel}명 삭제 · demo_seed_off=1")
    log(f"[백업 위치] {bak}  (문제 시: cp '{bak}' '{DB}' 후 재시작)")
    log("[다음] supervisorctl restart knk-works")


if __name__ == "__main__":
    main()
