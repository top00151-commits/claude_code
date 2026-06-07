#!/usr/bin/env python3
"""sync_employees_messenger_to_works.py
메신저 DB 직원 → HAIST WORKS DB **1회 동기화** (Excel 경유 없이 DB→DB).

배경: 로그인은 메신저 SSO 로만 이뤄지고, "메신저에 등록된 직원 = WORKS 에도 동일 등록"
      하기 위한 1회성(이후 신규자도 재실행 가능) 동기화. (대표 지시 2026-06-01)

읽기: 메신저  /opt/knk_messenger/data/messenger.db  (users, 게스트 제외)
쓰기: WORKS    /opt/knk_haist/data/main.db          (users)

매칭/업서트: WORKS 기존 importer(import_employees_from_excel.py)의 apply_employee 와 동일 규칙
  1) (이름+이메일) 또는 (이름+전화) 매칭 → 갱신(COALESCE: 기존값 보존, 빈 값만 채움)
  2) 동명이인 아닌 단일 이름 매칭 → 갱신
  3) 미매칭 → 신규 INSERT (초기비번: 본사=휴대폰숫자 / VN=9999, must_change_pw=1)
  4) WORKS 에만 있고 메신저엔 없는 사람 → 출력만 (수동 판단)

비대화형(프롬프트 없음). --dry-run 은 아무 것도 변경하지 않음(rollback).

사용:
  python3 - --dry-run    < 이 파일        # 미리보기(읽기 전용)
  python3 - --apply      < 이 파일        # 실제 반영 (백업 후 실행 권장)
"""
import argparse
import hashlib
import os
import re
import sqlite3
import sys


def hash_pw_pbkdf2(password, salt=None, iterations=200_000):
    """WORKS pbkdf2 형식: pbkdf2$200000$<salt_hex>$<hash_hex>"""
    if salt is None:
        salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2${iterations}${salt.hex()}${dk.hex()}"


def initial_pw_kor(phone):
    if not phone:
        return "0000"
    return re.sub(r"\D", "", str(phone)) or "0000"


def initial_pw_vn():
    return "9999"


def read_messenger_employees(msg_db):
    conn = sqlite3.connect(msg_db)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT id, employee_no, username, display_name, display_name_en, display_name_vn,
                  department, title, entity, email, phone,
                  COALESCE(active, 1) AS active
             FROM users
            WHERE COALESCE(is_guest, 0) = 0
            ORDER BY (employee_no IS NULL) ASC, id ASC"""
    ).fetchall()
    conn.close()
    emps = []
    for r in rows:
        ent = (r["entity"] or "").strip().upper()
        if ent not in ("KOR", "VN"):
            # entity 미지정 추정: 베트남어 이름 있으면 VN, 아니면 KOR
            ent = "VN" if (r["display_name_vn"] and str(r["display_name_vn"]).strip()) else "KOR"
        name = (r["display_name"] or "").strip() or (r["username"] or "").strip()
        emp_no = None
        if r["employee_no"] and str(r["employee_no"]).strip():
            emp_no = str(r["employee_no"]).strip()
        elif r["username"] and str(r["username"]).strip():
            emp_no = str(r["username"]).strip()
        emps.append({
            "entity": ent,
            "employee_no": emp_no,
            "name": name,
            "name_en": ((r["display_name_en"] or "").strip() or None),
            "name_vi": ((r["display_name_vn"] or "").strip() or None),
            "email": ((r["email"] or "").strip() or None),
            "phone": ((r["phone"] or "").strip() or None),
            "position": ((r["title"] or "").strip() or None),     # → WORKS rank
            "dept_code": ((r["department"] or "").strip() or None),  # 메신저는 부서 '이름'
            "active": int(r["active"]),
        })
    return emps


def find_existing_user(c, name, email=None, phone=None):
    if email:
        r = c.execute("SELECT * FROM users WHERE name=? AND email=?", (name, email)).fetchone()
        if r:
            return r
    if phone:
        r = c.execute("SELECT * FROM users WHERE name=? AND phone=?", (name, phone)).fetchone()
        if r:
            return r
    rows = c.execute("SELECT * FROM users WHERE name=?", (name,)).fetchall()
    if len(rows) == 1:
        return rows[0]
    return None


def apply_employee(c, emp, dry_run=True):
    existing = find_existing_user(c, emp["name"], emp.get("email"), emp.get("phone"))
    if existing:
        if dry_run:
            return "updated"
        c.execute(
            """UPDATE users SET
                   employee_no = COALESCE(?, employee_no),
                   entity      = COALESCE(?, entity),
                   login_id    = COALESCE(?, login_id),
                   email       = COALESCE(?, email),
                   phone       = COALESCE(?, phone),
                   name_en     = COALESCE(?, name_en),
                   name_vi     = COALESCE(?, name_vi),
                   dept_code   = COALESCE(?, dept_code),
                   rank        = COALESCE(?, rank)
                 WHERE id = ?""",
            (emp["employee_no"], emp["entity"], emp["employee_no"],
             emp.get("email"), emp.get("phone"), emp.get("name_en"), emp.get("name_vi"),
             emp.get("dept_code"), emp.get("position"), existing["id"]))
        return "updated"
    else:
        if dry_run:
            return "inserted"
        init_pw = initial_pw_kor(emp.get("phone", "")) if emp["entity"] == "KOR" else initial_pw_vn()
        c.execute(
            """INSERT INTO users
                   (name, login_id, password, email, phone, employee_no, entity,
                    name_en, name_vi, dept_code, rank, role, is_active, must_change_pw,
                    password_version, lang)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1,1,1,?)""",
            (emp["name"], emp["employee_no"], hash_pw_pbkdf2(init_pw),
             emp.get("email"), emp.get("phone"), emp["employee_no"], emp["entity"],
             emp.get("name_en"), emp.get("name_vi"), emp.get("dept_code"), emp.get("position"),
             "member", "ko" if emp["entity"] == "KOR" else "vi"))
        return "inserted"


def main():
    ap = argparse.ArgumentParser(description="메신저 직원 → WORKS 1회 동기화")
    ap.add_argument("--msg-db", default="/opt/knk_messenger/data/messenger.db")
    ap.add_argument("--works-db", default="/opt/knk_haist/data/main.db")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true", help="DB 변경 X — 미리보기만")
    g.add_argument("--apply", action="store_true", help="실제 반영 (백업 후 권장)")
    a = ap.parse_args()

    for p in (a.msg_db, a.works_db):
        if not os.path.exists(p):
            sys.exit(f"[ERROR] DB 없음: {p}")

    emps = read_messenger_employees(a.msg_db)
    print(f"[INFO] 메신저 직원(게스트 제외): {len(emps)}명")
    print(f"[INFO] WORKS DB: {a.works_db}  / 모드: {'DRY-RUN' if a.dry_run else 'APPLY'}")

    conn = sqlite3.connect(a.works_db)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    cols = [r[1] for r in c.execute("PRAGMA table_info(users)").fetchall()]
    required = ["name", "login_id", "password", "email", "phone", "employee_no", "entity",
                "name_en", "name_vi", "dept_code", "rank", "role", "is_active",
                "must_change_pw", "password_version", "lang"]
    missing = [x for x in required if x not in cols]
    if missing:
        sys.exit(f"[ERROR] WORKS users 컬럼 없음: {missing} (migration 먼저 적용)")

    stats = {"updated": 0, "inserted": 0, "skipped": 0}
    sample = {"updated": [], "inserted": []}
    for emp in emps:
        try:
            res = apply_employee(c, emp, dry_run=a.dry_run)
            stats[res] += 1
            if len(sample[res]) < 10:
                sample[res].append(f"[{emp['employee_no']}] {emp['name']}({emp['entity']})")
        except Exception as e:
            stats["skipped"] += 1
            print(f"  [ERR] {emp.get('name')}: {e}")

    # WORKS 에만 있고 메신저엔 없는 사람
    msg_names = {e["name"] for e in emps if e["name"]}
    works_only = []
    if msg_names:
        ph = ",".join("?" * len(msg_names))
        works_only = c.execute(
            f"SELECT id, name, login_id, email FROM users WHERE name NOT IN ({ph})",
            tuple(msg_names)).fetchall()

    if a.apply:
        conn.commit()
        mode = "APPLIED (반영 완료)"
    else:
        conn.rollback()
        mode = "DRY-RUN (변경 없음)"
    conn.close()

    print(f"\n=== {mode} ===")
    print(f"  갱신(기존 직원 정보 보강): {stats['updated']}")
    print(f"  신규(WORKS 에 새로 추가):  {stats['inserted']}")
    print(f"  스킵(오류):               {stats['skipped']}")
    print(f"  WORKS 에만 있음(메신저 미등재): {len(works_only)}  (수동 판단)")
    if sample["inserted"]:
        print("  신규 예시:", " · ".join(sample["inserted"]))
    if sample["updated"]:
        print("  갱신 예시:", " · ".join(sample["updated"]))
    if works_only:
        print("  WORKS-only:", " · ".join(f"{u['name']}({u['login_id']})" for u in works_only[:15]))


if __name__ == "__main__":
    main()
