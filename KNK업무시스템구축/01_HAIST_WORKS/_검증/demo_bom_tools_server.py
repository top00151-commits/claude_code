#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
WP-04 BOM 도구 공장 — 화면 보기용 로컬 서버
============================================
⛔ 실제 DB 를 열지 않는다 — 임시 폴더 복사본만. 보관함도 임시 폴더.
   z425 SSO 때문에 로컬 로그인이 안 되므로 입장 경로(/demo)만 따로 붙인다.
사용법:  python _검증/demo_bom_tools_server.py   →  http://127.0.0.1:8896/demo
"""
import os
import shutil
import sys
import tempfile

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import app.database as D                                    # noqa: E402

REAL_DB = os.path.abspath(D.DB_PATH)
TMP = tempfile.mkdtemp(prefix="knk_bomtools_demo_")
DEMO_DB = os.path.join(TMP, "demo.db")
if not os.path.exists(REAL_DB):
    print(f"[중단] 원본 DB 없음: {REAL_DB}")
    sys.exit(1)
shutil.copy2(REAL_DB, DEMO_DB)
for ext in ("-wal", "-shm"):
    if os.path.exists(REAL_DB + ext):
        shutil.copy2(REAL_DB + ext, DEMO_DB + ext)
D.DB_PATH = DEMO_DB
assert os.path.abspath(D.DB_PATH).startswith(os.path.abspath(TMP)), "복사본 전환 실패"
print(f"  원본(안 건드림): {REAL_DB}\n  복사본(여기만): {DEMO_DB}")

D.init_db()
with D.db_session() as c:
    c.execute("INSERT OR REPLACE INTO users(id, name, login_id, password, role, rank, "
              "can_use_logistics, can_view_logistics) VALUES(9902,'구매 시험','DEMO9902','x','member','프로',1,1)")

import uvicorn                                              # noqa: E402
from fastapi import Request                                 # noqa: E402
from fastapi.responses import RedirectResponse              # noqa: E402
import app.main as M                                        # noqa: E402

M._BT_STORE = os.path.join(TMP, "store")                    # 보관함도 임시
os.makedirs(M._BT_STORE, exist_ok=True)


@M.app.get("/demo")
@M.app.get("/demo/{uid}")
async def _demo_enter(req: Request, uid: int = 9902):
    req.session["user_id"] = uid
    return RedirectResponse("/bom/tools", 303)


if __name__ == "__main__":
    print("\n  → http://127.0.0.1:8896/demo\n")
    uvicorn.run(M.app, host="127.0.0.1", port=8896, log_level="warning")
