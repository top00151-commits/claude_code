# -*- coding: utf-8 -*-
"""z1191z136 (대표 11-24): 웍스 홈 인사말 — 회사 시간 · 휴일 · 창립기념일 · 직급 호칭 · 생일(이음 birth_md)"""
import os, sqlite3, sys
from datetime import datetime
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app import greeting as G
R = []
def check(l, c, g=""):
    R.append(bool(c)); print(("✅ " if c else "❌ ") + l + ("" if c else "  → " + str(g)[:200]))
KR = {"2026-12-25": "기독탄신일"}
VN = {"2026-09-02": "국경일"}
def b(h, m=0, d="2026-11-24", name="김정락", rank="대표이사", ent="KOR", bmd=None):
    return G.build(name, rank, ent, bmd, datetime.strptime("%s %02d:%02d" % (d, h, m), "%Y-%m-%d %H:%M"), KR, VN)
# 호칭
check("대표이사 → 「김정락 대표님」(z139)", G.title_of("김정락", "대표이사") == "김정락 대표님")
check("매니저 → 「허동준 매니저님」", G.title_of("허동준", "매니저") == "허동준 매니저님")
check("괄호 직책 → 「팀장님」", G.title_of("홍길동", "매니저(팀장)") == "홍길동 팀장님")
check("z139 임원 괄호 = 임원 직급(이사(팀장) → 이사님)", G.title_of("홍길동", "이사(팀장)") == "홍길동 이사님")
check("z139 과장(팀장)·차장(팀장) = 팀장님", G.title_of("홍길동", "과장(팀장)") == "홍길동 팀장님" and G.title_of("홍길동", "차장(팀장)") == "홍길동 팀장님")
check("z139 괄호 없는 직급 그대로(상무이사·전무이사·매니저·프로)", [G.title_of("가", x) for x in ("상무이사", "전무이사", "매니저", "프로")] == ["가 상무님", "가 전무님", "가 매니저님", "가 프로님"])
check("직급 없으면 「이름님」", G.title_of("홍길동", "") == "홍길동님" and G.title_of("홍길동", None) == "홍길동님")
# 시간대(화요일 11-24 · 본사)
t = {h: b(h) for h in (5, 8, 10, 12, 13, 15, 17, 19, 22)}
check("09시 전 = 좋은 아침", "좋은 아침" in t[8][0] and t[8][1] == "morning", t[8])
check("09~12 = 오전 업무 힘내세요", "오전 업무 힘내세요" in t[10][0], t[10])
check("12~13 = 점심·마무리 말 없음(오전 막바지)", "막바지" in t[12][0] and "점심" not in t[12][0] and "마무리" not in t[12][0], t[12])
check("13~14 = 점심시간", "점심시간" in t[13][0] and t[13][1] == "lunch", t[13])
check("14~17 = 오후도 힘내세요", "오후도 힘내세요" in t[15][0], t[15])
check("17시대 = 퇴근·마무리 말 없음", "남은 오후" in t[17][0] and "마무리" not in t[17][0] and "퇴근" not in t[17][0], t[17])
check("18시 이후 = 수고 많으셨습니다", "수고 많으셨습니다" in t[19][0] and t[19][1] == "evening", t[19])
check("밤 = 너무 늦지 않게", "너무 늦지 않게" in t[22][0] and "너무 늦지 않게" in t[5][0], (t[22], t[5]))
check("모든 문구에 「김정락 대표님」", all("김정락 대표님" in v[0] for v in t.values()))
# 베트남 = 한국 −2시간 · 베트남 공휴일
v = b(14, 30, ent="VN", name="Nguyen", rank="")
check("베트남 직원 한국 14:30 = 베트남 12:30 → 오전 막바지", "막바지" in v[0] and v[0].split(G.SEP)[0].endswith("Nguyen님"), v)
check("베트남 공휴일(9/2)은 베트남 직원만 쉬는 날 문구", "국경일에도 나오셨네요" in b(10, d="2026-09-02", ent="VN")[0] and "오전 업무" in b(10, d="2026-09-02")[0])
# 주말·한국 공휴일
check("토요일 = 주말에도 나오셨네요", "주말에도 나오셨네요" in b(10, d="2026-11-28")[0], b(10, d="2026-11-28"))
check("한국 공휴일 = 그 이름", "기독탄신일에도 나오셨네요" in b(10, d="2026-12-25")[0])
# 창립기념일(소속별)
check("본사 6/1 = KNK 창립기념일(본사 직원)", "KNK 창립기념일" in b(10, d="2026-06-01")[0] and b(10, d="2026-06-01")[1] == "anniversary")
check("베트남 10/15 = KNK VINA 창립기념일(베트남 직원만)", "KNK VINA 창립기념일" in b(10, d="2026-10-15", ent="VN")[0] and "창립" not in b(10, d="2026-10-15")[0])
# 생일(하루 종일 · 시간대별)
bd = {h: b(h, d="2026-06-20", bmd="06-20") for h in (8, 12, 13, 15, 19)}
check("생일 = 하루 종일 생일 축하", all(x[0].startswith("생일 축하드립니다, 김정락 대표님!") and x[1] == "birthday" for x in bd.values()), bd)
check("생일 12시 = 점심 말 없음 · 13시 = 점심 · 저녁 = 수고", "점심" not in bd[12][0] and "점심" in bd[13][0] and "수고" in bd[19][0], bd)
check("생일이 주말·창립기념일보다 먼저", b(10, d="2026-06-01", bmd="06-01")[1] == "birthday")
check("생일 아닌 날은 평소 문구", b(10, bmd="06-20")[1] == "morning")
# 음력 생일(대표 「음력 2월 9일」) · 음력 계산 = 공휴일 표(설날·부처님오신날·추석 2024~2036 · 윤달 해 포함)
from app import lunar_kr as L
import holidays as _H
_kr = _H.KR(years=range(2024, 2037), language="ko")
_bad = []
for _d, _n in _kr.items():
    for _part in str(_n).split("; "):
        _m = {"설날": (1, 1), "부처님오신날": (4, 8), "추석": (8, 15)}.get(_part)
        if _m and L.lunar_to_solar(_d.year, *_m) != _d:
            _bad.append((_d, _part, L.lunar_to_solar(_d.year, *_m)))
check("음력 계산 = 공휴일 표 39건 모두 같음(2033년 윤11월 포함)", not _bad, _bad)
check("음력 2월 9일 = 2026-03-27 · 2027-03-16", str(L.lunar_to_solar(2026, 2, 9)) == "2026-03-27" and str(L.lunar_to_solar(2027, 2, 9)) == "2027-03-16")
lb = G.build("김정락", "대표이사", "KOR", "06-20", datetime(2026, 3, 27, 10, 0), KR, VN, birth_lunar_md="02-09")
check("음력 생일날(2026-03-27) = 생일 축하", lb[1] == "birthday" and "김정락 대표님" in lb[0], lb)
lb2 = G.build("김정락", "대표이사", "KOR", "06-20", datetime(2026, 6, 20, 10, 0), KR, VN, birth_lunar_md="02-09")
check("음력 생일이 있으면 이음 양력 생일(06-20)은 안 씀", lb2[1] != "birthday", lb2)
# 이음 birth_md 저장(월·일만)
from app import sso_client as S
c = sqlite3.connect(":memory:")
c.execute("CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT)"); c.execute("INSERT INTO users VALUES(1,'a')")
S._save_birth_md_z136(c, 1, {"name": "a"})
check("birth_md 안 보내면 칸도 안 만듦", "birth_md" not in [r[1] for r in c.execute("PRAGMA table_info(users)")])
S._save_birth_md_z136(c, 1, {"birth_md": "06-20"})
check("「06-20」 저장", c.execute("SELECT birth_md FROM users WHERE id=1").fetchone()[0] == "06-20")
S._save_birth_md_z136(c, 1, {"birth_md": "1981-06-20"})
check("태어난 해 붙은 값은 받지 않음(그대로)", c.execute("SELECT birth_md FROM users WHERE id=1").fetchone()[0] == "06-20")
S._save_birth_md_z136(c, 1, {"birth_md": ""})
check("빈 글자 = 지움", c.execute("SELECT birth_md FROM users WHERE id=1").fetchone()[0] is None)
# z1191z137 짧은 제목(대표 「멘트가 너무 길어 정신없다」)
_all = [b(h) for h in range(24)] + [b(10, d="2026-11-28"), b(10, d="2026-06-01"), b(19, d="2026-06-20", bmd="06-20")]
_heads = [x[0].split(G.SEP)[0] for x in _all]
check("큰 제목은 모두 짧게(30자 이하)", all(len(h) <= 30 for h in _heads), [h for h in _heads if len(h) > 30])
check("호칭은 큰 제목에(창립기념일 빼고)", all("김정락 대표님" in x[0].split(G.SEP)[0] for x in _all if x[1] != "anniversary"))
# z1191z143 이음 v1029 — 음력 생일 사람 birth_md = 그해 양력 · birth_lunar · 받은 해 저장 · 홈은 올해 값만
import datetime as _dt143
_yr = (_dt143.datetime.utcnow() + _dt143.timedelta(hours=9)).year
S._save_birth_md_z136(c, 1, {"birth_md": "03-27", "birth_lunar": True})
_r = c.execute("SELECT birth_md, birth_lunar, birth_md_year FROM users WHERE id=1").fetchone()
check("z143 음력 사람 저장 = 03-27 · 음력 1 · 받은 해 올해", tuple(_r) == ("03-27", 1, _yr), _r)
S._save_birth_md_z136(c, 1, {"birth_md": "03-27"})
check("z143 birth_lunar 안 보내면 음력 표시 그대로", c.execute("SELECT birth_lunar FROM users WHERE id=1").fetchone()[0] == 1)
S._save_birth_md_z136(c, 1, {"birth_md": "06-20", "birth_lunar": False})
check("z143 양력 사람 = 음력 0", c.execute("SELECT birth_lunar FROM users WHERE id=1").fetchone()[0] == 0)
_src = open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
check("z143 홈 인사말 = 음력 사람은 올해 받은 값만(작년 값이면 생일 문구 안 씀)",
      'if u.get("birth_lunar") and str(u.get("birth_md_year") or "") != str(datetime.now().year):' in _src and "_bmd143 = None" in _src)
def _home_bmd(u, year):
    b = u.get("birth_md")
    if u.get("birth_lunar") and str(u.get("birth_md_year") or "") != str(year):
        b = None
    return b
check("z143 같은 규칙 — 음력·작년 값 = 안 씀 · 음력·올해 = 씀 · 양력(옛 값 해 없음) = 씀",
      _home_bmd({"birth_md": "03-16", "birth_lunar": 1, "birth_md_year": 2026}, 2027) is None
      and _home_bmd({"birth_md": "03-16", "birth_lunar": 1, "birth_md_year": 2027}, 2027) == "03-16"
      and _home_bmd({"birth_md": "06-20", "birth_lunar": None, "birth_md_year": None}, 2027) == "06-20")
print("\n결과: %d 통과 / %d 실패" % (sum(R), len(R) - sum(R)))
sys.exit(0 if all(R) else 1)
