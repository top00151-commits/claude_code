"""v5H226z455 (대표 지시): 형태 4종 도입(완제품/제품/상품/기타)에 따른 form_type 재동기화.

배경: 기존 매핑은 제품=ASSEMBLY 였으나, z455 부터 완제품=ASSEMBLY · 제품=SEMI(반제품) 로 분리.
      기존 프로젝트는 form_type 에 옛 라벨('제품')이 저장돼 있어, 그대로 두면
      (1) 작업일정표가 옛 라벨을 보여주고 (2) 편집 재저장 시 resolve_form_ship 이 '제품'→SEMI 로
      잘못 매핑한다. → form_type 을 shipment_form(행동의 단일 진실)에서 새 라벨로 재동기화.

대표 결정: 기존 ASSEMBLY = '완제품' (호기 유지). idempotent — 불일치 행만 갱신.
"""
import sqlite3

SHIP_TO_FORM_NEW = {"ASSEMBLY": "완제품", "SEMI": "제품", "PARTS": "상품", "ETC": "기타"}


def migrate(db_path: str) -> dict:
    out = {"updated": 0}
    try:
        c = sqlite3.connect(db_path)
        cols = {r[1] for r in c.execute("PRAGMA table_info(projects)").fetchall()}
        if "form_type" not in cols or "shipment_form" not in cols:
            c.close()
            return out
        n = 0
        for sf, ft in SHIP_TO_FORM_NEW.items():
            cur = c.execute(
                "UPDATE projects SET form_type=? "
                "WHERE UPPER(COALESCE(shipment_form,'ASSEMBLY'))=? AND COALESCE(form_type,'')<>?",
                (ft, sf, ft),
            )
            n += cur.rowcount
        c.commit()
        c.close()
        out["updated"] = n
    except Exception as e:
        out["error"] = str(e)
    return out
