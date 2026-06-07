#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cutover 사후 검증 — 마이그레이션 결과. argv[1]=DB 경로."""
import sqlite3, sys, re
db = sys.argv[1]
c = sqlite3.connect(db); c.row_factory = sqlite3.Row
staff = "COALESCE(is_guest,0)=0 AND username!='_deleted_user'"
n_null = c.execute(f"SELECT COUNT(*) FROM users WHERE {staff} AND (employee_no IS NULL OR employee_no='')").fetchone()[0]
n_mism = c.execute(f"SELECT COUNT(*) FROM users WHERE {staff} AND employee_no IS NOT NULL AND username!=employee_no").fetchone()[0]
n_staff = c.execute(f"SELECT COUNT(*) FROM users WHERE {staff}").fetchone()[0]
print("staff_total =", n_staff)
print("employee_no_NULL_staff =", n_null, " (0 이어야 정상, DB-only 직원 수만큼 나올 수 있음)")
print("username_neq_employee_no =", n_mism, " (0 이어야 정상)")
bad_kor = bad_vn = 0
for r in c.execute(f"SELECT employee_no, entity FROM users WHERE {staff} AND employee_no IS NOT NULL"):
    e = r["employee_no"] or ""
    if r["entity"] == "VN":
        if not re.fullmatch(r"VN\d{3}", e): bad_vn += 1
    else:
        if not re.fullmatch(r"\d+", e): bad_kor += 1
print("bad_KOR_pattern =", bad_kor, " bad_VN_pattern =", bad_vn)
print("핵심 사번 표본:")
for r in c.execute(f"SELECT username, employee_no, entity, display_name, role FROM users WHERE employee_no IN ('5','43','VN001')"):
    print("  ", dict(r))
print("DB-only 후보(엑셀 미등재 추정 = employee_no NULL staff):")
for r in c.execute(f"SELECT id, username, display_name, role, active FROM users WHERE {staff} AND (employee_no IS NULL OR employee_no='')"):
    print("  ", dict(r))
c.close()
