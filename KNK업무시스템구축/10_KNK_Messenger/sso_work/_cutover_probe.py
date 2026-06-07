#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cutover 사전 탐지 — 운영 users 현황(읽기 전용). argv[1]=DB 경로."""
import sqlite3, sys
db = sys.argv[1]
c = sqlite3.connect(db)
cols = [r[1] for r in c.execute("PRAGMA table_info(users)")]
print("users_total =", c.execute("SELECT COUNT(*) FROM users").fetchone()[0])
print("staff_nonguest =", c.execute("SELECT COUNT(*) FROM users WHERE COALESCE(is_guest,0)=0").fetchone()[0])
print("guest =", c.execute("SELECT COUNT(*) FROM users WHERE is_guest=1").fetchone()[0])
print("has_employee_no =", "employee_no" in cols)
print("has_entity =", "entity" in cols)
print("has_password_version =", "password_version" in cols)
print("sample staff usernames (현재 로그인ID 형태):")
for r in c.execute("SELECT username, employee_no, display_name FROM users "
                   "WHERE COALESCE(is_guest,0)=0 AND username!='_deleted_user' LIMIT 10"):
    print("   username=%r  emp=%r  name=%r" % (r[0], r[1], r[2]))
c.close()
