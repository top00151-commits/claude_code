# -*- coding: utf-8 -*-
"""z1191z152 (대표 11-25 「사용자가 확정하지 않은 데이터를 마음대로 연결해서 입력한 걸 자꾸 틀어 버리면 신뢰할 수 없어」 · 원칙 4개 · 1단계):
   수주가 2개 이상인 관리번호 = 정보 수정의 고객사·2차·거래구분·형태·통화·PO유형·모델·장비는 고른 수주에만 저장 ·
   프로젝트 대표값·첫 수주·다른 수주는 그대로 · 수주 1개는 예전 흐름 · 일정표 수주 칸 → 프로젝트 대표값 안 바꿈 · 일정표 금액 칸 막음."""
import os, re, sqlite3, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
R = []


def check(l, c, g=""):
    R.append(bool(c)); print(("✅ " if c else "❌ ") + l + ("" if c else "  → " + str(g)[:300]))


import app.main as M

c = sqlite3.connect(":memory:"); c.row_factory = sqlite3.Row
c.executescript("""
CREATE TABLE customers(id INTEGER PRIMARY KEY, name TEXT, alias TEXT);
INSERT INTO customers VALUES(9,'삼성전자(주)','삼성전자'),(58,'KNK VINA CO LTD','KNK VINA');
CREATE TABLE projects(id INTEGER PRIMARY KEY, customer_id INTEGER, customer_name TEXT, secondary_customer TEXT, is_export INTEGER,
  shipment_form TEXT, currency TEXT, po_type TEXT, model_name TEXT, equip_name TEXT, project_type TEXT);
INSERT INTO projects VALUES(1,58,'KNK VINA CO LTD','SEV',1,'PARTS','USD','추가','MA-1','부착기','NEW_EQUIP');
INSERT INTO projects VALUES(2,58,'KNK VINA CO LTD','SEV',1,'PARTS','USD','추가','MA-1','부착기','NEW_EQUIP');
CREATE TABLE orders(id INTEGER PRIMARY KEY, project_id INTEGER, order_no TEXT, status TEXT, customer_id INTEGER, end_customer TEXT,
  currency TEXT, so_form TEXT, so_type TEXT, po_type TEXT, model_name TEXT, equip_name TEXT, updated_at TEXT);
INSERT INTO orders VALUES(11,1,'M-1','CONFIRMED',58,NULL,'USD',NULL,'','신규',NULL,NULL,NULL);
INSERT INTO orders VALUES(12,1,'M-2','CONFIRMED',58,NULL,'USD',NULL,'','추가',NULL,NULL,NULL);
INSERT INTO orders VALUES(13,1,'M-3','CONFIRMED',9,NULL,'KRW','ASSEMBLY','','추가','MA-1','부착기',NULL);
INSERT INTO orders VALUES(21,2,'S-1','CONFIRMED',58,NULL,'USD',NULL,'','추가',NULL,NULL,NULL);
CREATE TABLE order_items(id INTEGER PRIMARY KEY, order_id INTEGER, is_export INTEGER, currency TEXT, unit_status TEXT, unit_label TEXT);
INSERT INTO order_items VALUES(1,11,1,NULL,'',''),(2,12,1,'USD','',''),(3,13,0,NULL,'','');
CREATE TABLE receipts_payment(id INTEGER PRIMARY KEY, order_id INTEGER);
CREATE TABLE project_history(id INTEGER PRIMARY KEY, project_id INTEGER, changed_at TEXT, changed_by INTEGER, field TEXT, old_value TEXT, new_value TEXT, note TEXT);
""")
U = {"id": 86, "name": "안지연"}
P1 = dict(c.execute("SELECT * FROM projects WHERE id=1").fetchone())


def so(i):
    return dict(c.execute("SELECT * FROM orders WHERE id=?", (i,)).fetchone())


check("수주 2개 이상 판정", M._z152_multi(c, 1) and not M._z152_multi(c, 2))

# 화면 값 = 고른 수주 값
v = M._z152_form_view(c, 1, P1, "M-3")
check("화면: M-3 고객사 = 삼성전자 · 통화 KRW · 형태 완제품", v["eff"]["customer_id"] == 9 and v["eff"]["currency"] == "KRW" and v["eff"]["shipment_form"] == "ASSEMBLY", v)
check("화면: 다른 고객사 수주는 2차 고객 = 빈칸(상세와 같은 규칙)", (v["eff"]["secondary_customer"] or "") == "", v["eff"])
check("화면 알림: 다른 수주 M-1·M-2 고객사 KNK VINA", len(v["notes"]) == 2 and "KNK VINA" in v["notes"][0]["diff"], v["notes"])
v1 = M._z152_form_view(c, 1, P1, "M-1")
check("화면: M-1(칸 비움) = 프로젝트 값을 따라 보임(KNK VINA · USD · 상품 · SEV · 수출)",
      v1["eff"]["customer_id"] == 58 and v1["eff"]["currency"] == "USD" and v1["eff"]["secondary_customer"] == "SEV"
      and str(v1["eff"]["is_export"]) == "1", v1["eff"])

# 고른 수주에만 저장
E1 = v1["eff"]   # 화면이 보여 준 값 그대로 보내고(실제 화면과 같음) 고객사만 바꿈
form = {"target_so": "M-1", "customer_id": "9", "customer_name": "삼성전자(주)", "secondary_customer": E1["secondary_customer"] or "",
        "is_export": str(E1["is_export"]), "shipment_form": E1["shipment_form"] or "", "currency": E1["currency"], "po_type": E1["po_type"],
        "model": E1["model"] or "", "equip_name": E1["equip_name"] or ""}
ch = M._z152_save_so_fields(c, 1, form, P1, U)
check("고객사만 바꿈 → M-1 고객사 = 삼성전자 · 바뀐 칸 1개", so(11)["customer_id"] == 9 and len(ch) == 1 and ch[0][0] == "고객사", ch)
check("M-2·M-3·프로젝트 그대로", so(12)["customer_id"] == 58 and so(13)["customer_id"] == 9
      and c.execute("SELECT customer_id FROM projects WHERE id=1").fetchone()[0] == 58)
check("안 바꾼 빈칸은 비워 둠(대표 「빈칸 고정 안 함」)", so(11)["end_customer"] is None and so(11)["model_name"] is None and so(11)["so_form"] is None, so(11))
h = c.execute("SELECT field, old_value, new_value, note FROM project_history ORDER BY id DESC LIMIT 1").fetchone()
check("이력: 고객사 KNK VINA → 삼성전자 · 수주 M-1 만", h and h[0] == "고객사" and "KNK VINA" in h[1] and "삼성전자" in h[2] and "M-1" in h[3], tuple(h) if h else None)

form2 = dict(form, target_so="M-2", currency="KRW", is_export="0", shipment_form="ASSEMBLY", po_type="추가", customer_id="58", customer_name="KNK VINA CO LTD")
M._z152_save_so_fields(c, 1, form2, P1, U)
check("M-2 통화 KRW · 품목 USD 줄도 KRW · 빈 통화 줄은 그대로(수주 따름)",
      so(12)["currency"] == "KRW" and c.execute("SELECT currency FROM order_items WHERE id=2").fetchone()[0] == "KRW")
check("M-2 거래구분 = 품목 줄 내수 · 형태 = so_form ASSEMBLY", c.execute("SELECT is_export FROM order_items WHERE id=2").fetchone()[0] == 0
      and so(12)["so_form"] == "ASSEMBLY")
check("M-1 은 그대로(USD · 수출)", so(11)["currency"] == "USD" and c.execute("SELECT is_export FROM order_items WHERE id=1").fetchone()[0] == 1)

c.execute("UPDATE orders SET status='INVOICED' WHERE id=13")
ch3 = M._z152_save_so_fields(c, 1, {"target_so": "M-3", "currency": "USD", "customer_id": "9"}, P1, U)
check("계산서 수주 통화는 그대로 + 알림 글", so(13)["currency"] == "KRW" and ch3 and "그대로" in ch3[0][2], ch3)
check("수주 1개 관리번호 = None(예전 흐름)", M._z152_save_so_fields(c, 2, {"target_so": "S-1", "customer_id": "9"}, dict(c.execute("SELECT * FROM projects WHERE id=2").fetchone()), U) is None)

# 코드 구조: 첫 수주 퍼뜨리기·수주→대표값 맞추기 = 수주 2개 이상이면 안 함 · 정보 수정 meta cascade 통화 = 옛 값
src = open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
fs = src[src.index("def _z1191_cascade_first_so"):src.index("def _z1191_hist")]
check("_z1191_cascade_first_so 맨 앞 = 수주 2개 이상이면 return", "if _z152_multi(c, pid):\n        return" in fs)
fy = src[src.index("def _z1191_sync_project_from_so"):src.index("def _z1191_cascade_first_so")]
check("_z1191_sync_project_from_so = 수주 2개 이상이면 return", "if _z152_multi(c, pid):\n        return" in fy)
check("정보 수정: 고른 수주 저장 뒤 대표값을 옛 값으로 · 첫 수주 맞추기 끔", "_so152 = _z152_save_so_fields(" in src and "_old1191 = None   # 첫 수주 맞추기" in src)
check("정보 수정: 통화 퍼뜨리기 = 옛 통화", 'if _so152 is not None:   # z1191z152: 통화는 고른 수주에만' in src)
check("일정표 금액 칸: 수주 2개 이상 + 수주 줄 = 막고 안내", "여기서 금액을 고치면 다른 수주까지 바뀝니다" in src)

# 화면 틀: 알림·(이 수주)·저장 전 확인 · 스크립트 문법
t = open(os.path.join(ROOT, "app", "templates", "project_quick_form.html"), encoding="utf-8").read()
check("화면: 다른 수주 값 알림 · (이 수주) · 저장 전 확인", "v152-warn" in t and "(이 수주)" in t and "만 바뀝니다" in t)
check("화면: 수주 2개 이상이면 z130 통화 알림 끔(맞지 않는 말)", "length > 1 and not v152 %}" in t)
js = "\n;\n".join(re.sub(r"\{\{.*?\}\}", "0", re.sub(r"\{%.*?%\}", "", re.sub(r"\{#.*?#\}", "", x, flags=re.S), flags=re.S), flags=re.S)
                  for x in re.findall(r"<script(?![^>]*src=)[^>]*>(.*?)</script>", t, re.S))
fp = os.path.join(tempfile.gettempdir(), "z152_quick.js"); open(fp, "w", encoding="utf-8").write(js)
try:
    r = subprocess.run(["node", "--check", fp], capture_output=True, text=True, encoding="utf-8")
    check("정보 수정 화면 스크립트 문법(node)", r.returncode == 0, r.stderr[-300:])
except FileNotFoundError:
    print("· node 없음 — 문법 검사 건너뜀")

print("\n결과: %d 통과 / %d 실패" % (sum(R), len(R) - sum(R)))
sys.exit(0 if all(R) else 1)
