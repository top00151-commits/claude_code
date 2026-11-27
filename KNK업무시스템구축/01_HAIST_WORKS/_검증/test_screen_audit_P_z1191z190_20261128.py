# -*- coding: utf-8 -*-
"""z1191z190 화면 전수 점검(04 지시문 11-27 21:00 최종) 묶음 P — 글자·그리기 검사
   P-1 좁은 창(768~1023)에서 맨 위 막대가 넘쳐 🚪 가 안 보임 → 「이전 페이지」 글자·이름 글자만 뺌(단추는 그대로)
   P-2 브라우저·휴대폰 「뒤로」에서 목록 위치를 잃음 → 저장 열쇠 = 그 화면을 보기 시작할 때의 주소·본문 · 복원 중 저장 안 함
   P-3 수주 상세 두 칸 배치 → minmax(0,1fr) · 1100px 이하 한 칸
   P-4 진행 매트릭스·진행 상세 → PHASE_DEFS 묶음 값(코드, 이름, 순서)을 풀어 읽음 · 상세는 DB 칸 이름(phase_code)
   P-5 처리 안 된 오류 화면 → 오류 번호와 안내만(자세한 내용은 서버 기록)
   (실제 화면 시험 = scratchpad z190 · 시험 서버 두 대(원래 판·고친 판) · PC 1440·892 · 휴대폰 412·360 · 폴드 768~1023)"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(ROOT, "app", "templates")
def rd(*p): return open(os.path.join(*p), encoding="utf-8").read()
R = []
def check(l, c):
    R.append(bool(c)); print(("✅ " if c else "❌ ") + l)

# ── P-1 ─────────────────────────────────────────────
ch = rd(T, "_v5_partials", "chrome.html")
m = re.search(r"@media \(min-width: 768px\) and \(max-width: 1023px\) \{(.*?)\n\}", ch, re.S)
blk = m.group(1) if m else ""
check("P-1 좁은 창(768~1023) 규칙 있음", bool(m))
check("P-1 「이전 페이지」 글자만 숨김(← 단추는 그대로)", "#knkBackBtn > span + span { display: none" in blk and not re.search(r"#knkBackBtn\s*\{[^}]*display:\s*none", blk))
check("P-1 이름 글자만 숨김(동그라미·내 정보 단추는 그대로)", ".top-user > div:not(.avatar) { display: none" in blk and not re.search(r"\.top-user\s*\{[^}]*display:\s*none", blk))
check("P-1 없애는 단추 0(아이콘·🚪·AI 를 숨기는 줄 없음)", not re.search(r"(\.top-icon|logout|#victorToggleBtn|#knkTopRight)[^{]*\{[^}]*display:\s*none", blk))

# ── P-2 ─────────────────────────────────────────────
i0 = ch.find("v5H226z984b (대표 지시): 화면 위치 복원"); seg = ch[i0:ch.find("</script>", i0)]
sv = seg[seg.find("function save(){"):seg.find("var t = null;", seg.find("function save(){"))]
check("P-2 저장 열쇠 = 화면 시작 때 주소(viewKey) · 지금 주소(key()) 로 쓰지 않음",
      "sessionStorage.setItem(viewKey" in sv and "sessionStorage.removeItem(viewKey)" in sv and "setItem(key()" not in sv and "removeItem(key())" not in sv)
check("P-2 본문이 바뀌었는데 새 화면 시작 전이면 저장 안 함", "mainEl() !== viewMain) return" in sv)
check("P-2 복원 중에는 저장 안 함(맨 위 0 이 복원 값을 덮지 않게)", "if (restoring) return" in sv and "restoring = true" in seg and "restoring = false; }" in seg)
nv = seg[seg.find("document.addEventListener('knk:navigated'"):]
check("P-2 새 화면 시작(knk:navigated)·처음 열기 때 viewStart()", "viewStart();" in nv[:900] and seg.count("viewStart(); setTimeout(restore, 0)") == 2)
spa = rd(T, "_v5_partials", "spa_nav.html")
check("P-2 FULL_ONLY 안전장치 그대로(/project/ · /sales/quotations · /sales/receipts-check)",
      all(x in spa for x in [r"/^\/project\/\d+\/?$/", r"/^\/sales\/quotations\/?$/", r"/^\/sales\/receipts-check\/?$/"]))

# ── P-3 ─────────────────────────────────────────────
so = rd(T, "sales_order_detail.html")
check("P-3 송장·수금 두 칸 = minmax(0,1fr)", ".so-2col { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }" in so)
check("P-3 1100px 이하 한 칸", re.search(r"@media \(max-width: 1100px\) \{\s*\.so-2col \{ grid-template-columns: minmax\(0, 1fr\) !important; \}", so) is not None)
check("P-3 옛 `1fr 1fr`·`repeat(4,1fr)` 칸 없음", "grid-template-columns: 1fr 1fr" not in so and "repeat(4,1fr)" not in so and "repeat(2, 1fr)" not in so)

# ── P-4 ─────────────────────────────────────────────
sys.path.insert(0, ROOT)
src_db = rd(ROOT, "app", "database.py")
pm = re.search(r"PHASE_DEFS = \[(.*?)\n\]", src_db, re.S)
PHASE_DEFS = eval("[" + pm.group(1) + "]") if pm else []
check("P-4 PHASE_DEFS 12공정 · (코드, 이름, 순서) 묶음", len(PHASE_DEFS) == 12 and all(len(x) == 3 for x in PHASE_DEFS))
import jinja2
mx = rd(T, "progress_matrix.html")
tb = mx[mx.find('<table class="mtx">'):mx.find("</table>") + 8]
env = jinja2.Environment()
rows = [{"id": 1, "mgmt_code": "T-1", "name": "시험", "phases": {"order": {"status": "완료", "progress_pct": 100}, "design": {"status": "진행", "progress_pct": 40}}},
        {"id": 2, "mgmt_code": "T-2", "name": "자료 없음", "phases": {}}]
html = env.from_string(tb).render(matrix=rows, PHASE_DEFS=PHASE_DEFS)
ths = re.findall(r"<th[^>]*>(.*?)</th>", html, re.S)
check("P-4 매트릭스 칸 이름 12개 모두 글자(빈칸 0)", len(ths) == 13 and all(x.strip() for x in ths[1:]) and ths[1] == "수주" and ths[12] == "KNKVN 이관")
cells = re.findall(r'<span class="cell (cell-[^"]*)">(.*?)</span>', html, re.S)
dash = sum(1 for c in cells if c[1].strip() == "—")
check("P-4 「—」 = 자료 없는 칸만(24칸 중 22)", len(cells) == 24 and dash == 22)
check("P-4 자료 있는 칸 = 상태 글자(완료·진행)", any(c[0] == "cell-완료" for c in cells) and any(c[0] == "cell-진행" and "40%" in c[1] for c in cells))
pd = re.sub(r"\{#.*?#\}", "", rd(T, "progress_detail.html"), flags=re.S)   # 설명 글(주석) 빼고 본다
check("P-4 진행 상세 = phase_code 로 공정 이름 · 옛 phase.code/start_date 없음",
      "PHASE_CODE_TO_LABEL.get(phase.phase_code" in pd and "phase.code" not in pd and "phase.start_date" not in pd)
check("P-4 진행 상세 상태 색 = 한글 상태(완료·진행·지연)도", "('DONE','완료')" in pd and "('PROGRESS','진행')" in pd and "('DELAY','지연')" in pd)

# ── P-5 ─────────────────────────────────────────────
mn = rd(ROOT, "app", "main.py")
h0 = mn.find("@app.exception_handler(Exception)"); h1 = mn.find("@app.on_event", h0)
hd = mn[h0:h1]
resp = hd[hd.find("return HTMLResponse("):]
check("P-5 오류 화면에 내부 내용 안 씀(_tb_str · _err_msg · 요청 주소)", "{_tb_str}" not in resp and "{_err_msg}" not in resp and "request.url.path}" not in resp and "<pre>" not in resp)
check("P-5 개발 문구 없음", "KNK_시작.bat" not in resp and "빅터" not in resp)
check("P-5 오류 번호를 화면과 서버 기록에 같이", "{_eid}" in resp and re.search(r'print\(f"\[v5H158 GLOBAL EXC\] \{_eid\}', hd) is not None)
check("P-5 자세한 내용은 서버 기록에(print 유지)", "print(_tb_str)" in hd)
check("P-5 뒤로·다시 시도·홈 단추", "history.back()" in resp and "location.reload()" in resp and 'href="/home"' in resp)

print("\n결과: %d 통과 / %d 실패" % (sum(R), len(R) - sum(R)))
sys.exit(0 if all(R) else 1)
