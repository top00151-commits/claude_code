# -*- coding: utf-8 -*-
"""z1191z119 (안지연 프로 11-23 「업로드가 두 번째부터 인식 안 됨 · 웍스 다시 켜면 됨」) — 글자 검사
   ① 프로젝트 상세 · 정보 수정 · 새 등록은 본문만 갈아 끼우지 않고 늘 새로 연다(spa_nav FULL_ONLY)
   ② 상세의 「전체 교체·값만 고치기」 파일 칸은 화면마다 새로 만든다(앞 화면 칸·수주 번호가 남지 않게) · 「확인함」 표시 다시 시작
   ③ 정보 수정의 「수주 있는 정보 수정」 표시(__so118)는 화면마다 0 에서 시작
   (실제 화면 순서 시험 = scratchpad sim_ow_spa · sim_qe_spa · sim_ajy_path — 안지연 프로 계정 · 운영 사본)"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(ROOT, "app", "templates")
def rd(*p): return open(os.path.join(T, *p), encoding="utf-8").read()
R = []
def check(l, c):
    R.append(bool(c)); print(("✅ " if c else "❌ ") + l)
spa = rd("_v5_partials", "spa_nav.html")
m = re.search(r"var FULL_ONLY = \[(.*?)\];", spa, re.S)
pats = [re.compile(x.strip()[1:-1].replace("\\/", "/")) for x in re.findall(r"/\^[^,\]]*?\$/", m.group(1))] if m else []
def full(path): return any(p.search(path) for p in pats)
for pth in ["/project/1146", "/project/1146/", "/projects/1022/quick-edit", "/projects/quick", "/consumables/12",
            "/sales/receipts-check", "/sales/quotations", "/qc/inspection-reports/new"]:   # z1191z120
    check("① 늘 새로 열기: %s" % pth, full(pth))
for pth in ["/sales/schedule", "/projects", "/project/1146/history", "/home", "/mail"]:
    check("① 본문만 바꾸기 그대로: %s" % pth, not full(pth))
pd = rd("project_detail.html")
seg = pd[pd.find("window.knkOwClick"):pd.find("window.knkOwClick") + 4000]
check("② 파일 칸 옛것 지우고 새로 만듦", "_oldF.remove()" in seg and "_owBound" not in pd)
check("② 「확인함」 표시 화면마다 false 로 시작", "window.__knkClosedOk117 = false;" in seg)
qf = rd("project_quick_form.html")
i0 = qf.find("window.__so118 = 0;"); i1 = qf.find("window.__so118 = 1;")
check("③ __so118 = 0 이 = 1 보다 앞(조건 밖)", 0 <= i0 < i1)
print("\n결과: %d 통과 / %d 실패" % (sum(R), len(R) - sum(R)))
sys.exit(0 if all(R) else 1)
