"""
m_z108n11_fix_sys_links.py
─────────────────────────────────────────────────────────────────
v5H226z108n11 (2026-05-18): system_link_template 깨진 URL 교정
  - /quotations  → /orders/new       (견적/주문 관련, 임시)
  - /orders      → /orders/new
  - /orders/po   → /materials/requests
  - /stocks      → /parts            (자재 카탈로그)
  - /work-orders → NULL              (해당 화면 미구현 — 버튼 숨김)
  - /customers   → /customers        (그대로 OK)
  - /catalog     → /catalog          (그대로 OK)
"""
from __future__ import annotations
import sqlite3
from pathlib import Path


URL_FIXES = {
    '/quotations':  '/orders/new',
    '/orders':      '/orders/new',
    '/orders/po':   '/materials/requests',
    '/stocks':      '/parts',
    '/work-orders': None,
}


def migrate(db_path: str) -> dict:
    out = {'updated': 0, 'cleared': 0}
    if not Path(db_path).exists():
        return out
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    c = con.cursor()
    try:
        # 컬럼 존재 확인
        cols = [r[1] for r in c.execute("PRAGMA table_info(workflow_nodes_master)")]
        if 'system_link_template' not in cols:
            return out

        for bad, good in URL_FIXES.items():
            # 정확히 일치하는 것과 쿼리스트링 포함된 것 모두 처리
            if good is None:
                # 해당 URL 사용 노드는 NULL 처리
                n = c.execute(
                    "UPDATE workflow_nodes_master SET system_link_template=NULL WHERE system_link_template=?",
                    (bad,)
                ).rowcount
                out['cleared'] += n
            else:
                n = c.execute(
                    "UPDATE workflow_nodes_master SET system_link_template=? WHERE system_link_template=?",
                    (good, bad)
                ).rowcount
                out['updated'] += n
        con.commit()
    finally:
        con.close()
    return out
