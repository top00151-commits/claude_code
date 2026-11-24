# -*- coding: utf-8 -*-
"""z1191z127 · z1191z128 (안지연 프로 11-24 요청 · 대표 「만들어」)
   z127 정보 수정 · 제품 한 줄 수주 = 「1개 단가」 칸 → 그 줄 수량(= 작업일정표 수량)·단가·금액 + 수주 합계 + 프로젝트 수주액 + 이력
   z128 작업일정표 「연기」 → 창(사유 저장 · 처음 납기 고치기 · 지우기 = 사유 필수) · 모두 관리번호 이력 ·
        판정 = 호기마다 자기 처음 납기 < 자기 지금 납기(예전 = 관리번호 가장 이른 처음 납기 → 새 호기만 더해도 연기로 보임)
   (실제 화면 확인 = 시험 서버 안지연 계정: 작업일정표 → 프로젝트 상세 → 정보 수정 · 연기 글자 누름 · 이력)"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = []
def check(l, c, g=""):
    R.append(bool(c)); print(("✅ " if c else "❌ ") + l + ("" if c else "  → " + str(g)[:300]))
T = os.path.join(ROOT, "app", "templates")
m = open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
qf = open(os.path.join(T, "project_quick_form.html"), encoding="utf-8").read()
sb = open(os.path.join(T, "schedule_board.html"), encoding="utf-8").read()
# ── z127
check("z127 화면: 제품·한 줄일 때만 1개 단가 칸(semi_line) · 두 줄 이상은 안내", "tso117.semi_line" in qf and "줄별 단가는 프로젝트 상세 수주 카드" in qf)
check("z127 화면: 입금 완료·계산서 수주 = 칸 잠금(semi_price_seen 0)", "{{ 0 if _sl127.closed else 1 }}" in qf and "{% if _sl127.closed %}readonly" in qf)
check("z127 화면: 제품 칸 보이기 목록에 단가 칸", "'qSemiPriceCell'" in qf)
check("z127 화면: 금액 = 작업일정표 수량 × 단가 바로 계산", "box.textContent=qMoney103(Math.round((bq>0?bq:1)*pr*100)/100" in qf)
check("z127 화면: 단가 비면 저장 전 알림(무상 = 0)", "1개 단가를 숫자로 적어 주세요(무상이면 0)." in qf)
i = m.index("# z1191z127 (안지연 프로 11-24 「정보 수정에서 수량/단가를 고치고 싶은데")
blk = m[i:i + 6000]
check("z127 서버: 고른 수주 · 품목 한 줄 · INVOICED/PAID/CANCELLED 아님만", "_n127 == 1 and _r127[5] not in (\"INVOICED\", \"PAID\", \"CANCELLED\")" in blk)
check("z127 서버: 수량 = 작업일정표 수량 · 금액 = 수량 × 단가(소수 둘째)", "_q127 = float(_bq127) if _bq127 > 0" in blk and "_a127 = round(_q127 * _p127, 2)" in blk)
check("z127 서버: 수주 합계 다시 · 프로젝트 수주액 다시(_recalc_project_amount)", "UPDATE orders SET total_amount=(SELECT COALESCE(SUM(amount),0)" in blk and "_recalc_project_amount(_c127, pid)" in blk)
check("z127 서버: 수주 이력 + 관리번호 이력", "INSERT INTO order_status_history" in blk and "log_project_change(_c127" in blk)
check("z127 서버: 저장 함수 맨 끝(다른 저장에 안 덮임)", m.index("# z1191z127 (안지연 프로 11-24 「정보 수정에서") < m.index('_z61_attach(pid, form.get("quote_tok"), _u, note="z1191z62 수정 화면'))
# ── z128
check("z128 판정: 호기마다 자기 처음 납기 < 자기 지금 납기", "_dl128 = [i for i in _scope128 if _oi_orig_iid.get(i) and _oi_due128.get(i) and _oi_orig_iid[i] < _oi_due128[i]]" in m
      and "_orig = min(_oi_orig_iid[i] for i in _dl128) if _dl128 else None" in m)
check("z129 판정: 호기 없는 줄 = 그 줄 수주번호 호기만(관리번호 전체 빌려 오지 않음)",
      "list(_so_iids129.get(_row.get(\"so_no\") or \"\") or []) if _row.get(\"so_no\")" in m)
check("z129 판정: 출하·취소·보류 끝난 호기는 연기 판정에서 뺌", "_scope128 = [i for i in _scope128 if i not in _done129]" in m and 'if _r[6] in ("출하", "취소", "보류"):' in m)
check("z128 판정: 옛 「관리번호 가장 이른 처음 납기」 대체 안 씀", "_orig = min(_origs) if _origs else _proj_orig.get" not in m)
e = m[m.index('@app.post("/sales/schedule/due-delay")'):]
e = e[:e.index('@app.post("/sales/schedule/cell")')]
check("z128 저장: 매출 권한만", "if not can_use_sales(u):" in e)
check("z128 저장: 지우기는 사유 필수", 'if act == "clear" and not reason:' in e)
check("z128 저장: 이 관리번호 호기만(남의 호기 막음)", "WHERE o.project_id=? AND COALESCE(o.status,'')<>'CANCELLED' AND oi.id IN" in e and "if len(rows) != len(iids):" in e)
check("z128 저장: 세 동작 모두 관리번호 이력", e.count("_logi.log_project_change(") == 3 and "납기 연기 지움" in e and "지운 사유: %s" in e)
check("z128 저장: 지우기 = 처음 납기를 지금 납기로(다음에 또 미루면 다시 연기)", "SET due_date_orig=?, due_delay_reason=NULL WHERE id=?" in e)
check("z128 화면: 연기 글자 = 누를 수 있음 · 사유 있으면 밑줄 · 마우스 = 사유", 'delay-mark{% if r.delay_reason %} has-rsn{% endif %}' in sb and "· 사유: {{ r.delay_reason }}" in sb)
check("z128 화면: 누르면 창(openDelay128) · 줄에 대상 호기", "openDelay128(dm.closest('tr'))" in sb and 'data-delay-iids="{{ r.delay_iids }}"' in sb)
check("z128 화면: 지우기 = 사유 없으면 막고 한 번 묻기", "연기 표시를 지우는 사유를 적어 주세요." in sb and "연기 표시를 지울까요?" in sb)
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader(T))
errs = []
for f in ("project_quick_form.html", "schedule_board.html"):
    try:
        env.parse(open(os.path.join(T, f), encoding="utf-8").read())
    except Exception as ex:
        errs.append("%s: %s" % (f, ex))
check("템플릿 문법 정상", not errs, errs)
print("\n결과: %d 통과 / %d 실패" % (sum(R), len(R) - sum(R)))
sys.exit(0 if all(R) else 1)
