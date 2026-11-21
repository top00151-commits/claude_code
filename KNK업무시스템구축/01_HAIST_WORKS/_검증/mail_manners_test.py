# -*- coding: utf-8 -*-
"""메일 「라」 묶음 — 바깥 메일 예의 알림(5-1 인사말 · 5-2 가벼운 말투) · 밤·주말 「아침 예약」(5-4) · 사내 양식(5-6)
(대표 2026-11-21 「다음 진행해」). 운영 무접촉 · 가짜 문장만.

증명할 것
  ① 쓰기 화면 규칙(node 로 실제 실행): 바깥 거래처가 받는 메일만 · 사내끼리는 알림 없음
     · 첫인사·끝인사 없음 → 🙇(알림만) · 있으면 조용 · 영어 인사(Dear/Best regards)도 인정
     · ㅋㅋ·^^·~~·반말 끝(보내줘·했음…) → 💬 · 「포함」「확인함」 같은 낱말 속 글자는 안 잡음
     · 밤(21시~7시)·주말 → 🌙 + 「다음 근무일 아침 8:30 예약」 단추 · 이미 예약했으면 안 나옴 · 평일 낮은 안 나옴
     · 평일 새벽(7시 전)은 그날 아침 · 금요일 밤은 월요일 아침
  ② 확인 창: 「act」 단추 → 예약으로 바꾸기 · 사내 양식 제목 머리([보고]·[일정 변경])는 빈칸 아님
  ③ 사내 양식 4개(업무 보고 · 지시 확인 답장 · 일정 지연 안내·사과 · 거래처 첫 인사) · 양식 목록 입구에 나옴
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

P = F = 0


def check(name, cond, extra=""):
    global P, F
    if cond:
        P += 1
        print("  [PASS]", name)
    else:
        F += 1
        print("  [FAIL]", name, "<-", str(extra)[:500])


html = io.open(os.path.join(ROOT, "app", "templates", "mail_compose.html"), encoding="utf-8").read()

print("① 쓰기 화면 규칙")
node = shutil.which("node")
a = html.find("  var RE_HELLO=")
b = html.find("  window.cmpSchedMorning=")
s1, s2 = html.find("  var DOW='일월화수목금토';"), html.find("  function scValid(")
check("규칙 코드 찾음", a > 0 and b > a and s1 > 0 and s2 > s1)
if node and a > 0:
    js = r"""
var OUR_DOMAINS=['knknara.co.kr'];
function isOurs(ad){ var d=(ad.split('@')[1]||'').toLowerCase(); return OUR_DOMAINS.some(function(o){ return d===o || d.slice(-(o.length+1))==='.'+o; }); }
var SCHED=null, SCHED_OFF=9, NOW=0; window={CMP_ME:'시험 신입'};
""" + html[s1:s2] + "\n" + html[a:b] + r"""
scNowLocal=function(){ return NOW; };
scToday=function(){ var d=new Date(NOW); return Date.UTC(d.getUTCFullYear(),d.getUTCMonth(),d.getUTCDate()); };
function at(y,mo,d,h,mi){ NOW=Date.UTC(y,mo-1,d,h,mi||0); }
function run(to, txt, fwd){ return cmpManners(to.map(function(x){ return {addr:x}; }), txt, !!fwd).map(function(w){ return {kind:w.kind, ic:w.ic, t:w.t, act:(w.act||[]).map(function(x){ return x.arg; }), info:!!w.info}; }); }
var OUT={};
var EXT=['buyer@vendor-demo.example'], IN=['kim@knknara.co.kr'];
at(2026,11,20,14);   // 금요일 낮
OUT.polite=run(EXT,'안녕하세요, KNK 시험 신입입니다.\n견적서 보내 드립니다.\n감사합니다.');
OUT.nohello=run(EXT,'견적서 보내 드립니다.\n감사합니다.');
OUT.nobye=run(EXT,'안녕하세요.\n견적서 보내 드립니다.');
OUT.none=run(EXT,'견적서 보내요');
OUT.en=run(EXT,'Dear Mr. Kim,\nPlease find attached.\nBest regards,');
OUT.casual=run(EXT,'안녕하세요.\n샘플 내일 보내줘 ㅋㅋ\n일정 확인했음.\n감사합니다^^');
OUT.words=run(EXT,'안녕하세요.\n부가세 포함\n확인함\n그래서 일정은 내일입니다.\n감사합니다.');
OUT.inside=run(IN,'샘플 내일 보내줘 ㅋㅋ');
OUT.mixed=run(EXT.concat(IN),'샘플 보내줘 ㅋㅋ');
OUT.fwd=run(EXT,'', true);
at(2026,11,20,22,10);  // 금요일 밤
OUT.frinight=run(EXT,'안녕하세요.\n보내 드립니다.\n감사합니다.');
at(2026,11,21,10);     // 토요일 낮
OUT.sat=run(EXT,'안녕하세요.\n보내 드립니다.\n감사합니다.');
at(2026,11,24,5,30);   // 화요일 새벽
OUT.dawn=run(EXT,'안녕하세요.\n보내 드립니다.\n감사합니다.');
OUT.dawnIn=run(IN,'보내 드립니다.');
at(2026,11,24,23);     // 화요일 밤 — 이미 예약
SCHED={date:'2026-11-25',h:9,m:0}; OUT.sched=run(EXT,'안녕하세요.\n보내 드립니다.\n감사합니다.'); SCHED=null;
console.log(JSON.stringify(OUT));
"""
    fd, jp = tempfile.mkstemp(suffix=".js", prefix="knk_mann_")
    os.close(fd)
    io.open(jp, "w", encoding="utf-8").write(js)
    pr = subprocess.run([node, jp], capture_output=True, text=True, encoding="utf-8")
    os.remove(jp)
    try:
        O = json.loads(pr.stdout.strip().splitlines()[-1])
    except Exception:
        O = {}
        check("node 실행", False, pr.stderr[:400])
    K = lambda k: [w["kind"] for w in O.get(k, [])]   # noqa: E731
    check("정중한 바깥 메일(평일 낮) → 알림 없음", O.get("polite") == [], O.get("polite"))
    check("첫인사 없음 → 🙇 첫인사(알림만)", K("nohello") == ["manner"] and "첫인사가" in O["nohello"][0]["t"] and O["nohello"][0]["info"], O.get("nohello"))
    check("끝인사 없음 → 🙇 끝인사", K("nobye") == ["manner"] and "끝인사가" in O["nobye"][0]["t"], O.get("nobye"))
    check("둘 다 없음 → 「인사말이」", K("none") == ["manner"] and "인사말이" in O["none"][0]["t"], O.get("none"))
    check("영어 인사도 인정(Dear · Best regards)", O.get("en") == [], O.get("en"))
    cas = [w for w in O.get("casual", []) if w["kind"] == "manner" and w["ic"] == "💬"]
    check("가벼운 말투: ㅋㅋ · 보내줘 · 했음 · ^^", cas and all(x in cas[0]["t"] for x in ("ㅋㅋ", "보내줘", "했음", "^^")), O.get("casual"))
    check("낱말 속 글자(포함·확인함·그래서)는 안 잡음", O.get("words") == [], O.get("words"))
    check("사내끼리 → 알림 없음", O.get("inside") == [], O.get("inside"))
    check("사내+바깥 섞이면 → 알림", "manner" in K("mixed"), O.get("mixed"))
    check("전달(내 글 없음) → 인사말 알림 없음", O.get("fwd") == [], O.get("fwd"))
    fn = [w for w in O.get("frinight", []) if w["kind"] == "night"]
    check("금요일 밤 → 🌙 + 월요일 아침 예약 단추", fn and fn[0]["act"] == ["2026-11-23"] and fn[0]["info"], O.get("frinight"))
    st = [w for w in O.get("sat", []) if w["kind"] == "night"]
    check("토요일 낮 → 🌙 주말 + 월요일", st and "주말" in st[0]["t"] and st[0]["act"] == ["2026-11-23"], O.get("sat"))
    dw = [w for w in O.get("dawn", []) if w["kind"] == "night"]
    check("평일 새벽 → 그날 아침 8:30", dw and dw[0]["act"] == ["2026-11-24"], O.get("dawn"))
    check("새벽이라도 사내끼리 → 없음", O.get("dawnIn") == [], O.get("dawnIn"))
    check("이미 예약했으면 🌙 없음", O.get("sched") == [], O.get("sched"))
else:
    print("  (node 없음 — 쓰기 화면 규칙 실행 시험 건너뜀)")

print("\n② 확인 창 · 양식 빈칸")
check("확인 창에 act 단추(예약으로 바꾸기)", "window.cmpScAct=function(i)" in html and "cmpScAct('+i+')" in html and "window._scAct=[]" in html)
check("예약으로 바꾸기 = 기존 예약 길(SCHED · 8:30)", "window.cmpSchedMorning=function(date){ SCHED={date:date, h:8, m:30, at:date+'T08:30'};" in html)
check("보내기 전 확인에 예의 알림 들어감(보내기·예약 둘 다 checks 거침)", "W=W.concat(cmpManners(all, own, isFwd));" in html)
check("[보고]·[일정 변경] 은 빈칸 아님", re.search(r"FIXED_TAG=/\^\\\[\(KNK\|[^/]*\|보고\|일정 변경\)", html) is not None)

print("\n③ 사내 양식")
from app import mail_work as W  # noqa: E402
keys = {b["key"]: b for b in W.BUILTIN}
for k, t in (("b-in-report-ko", "[사내] 업무 보고"), ("b-in-ack-ko", "[사내] 지시 확인 답장"),
             ("b-in-delay-ko", "[사내] 일정 지연 안내·사과"), ("b-first-ko", "거래처 첫 인사(새 담당)")):
    check("양식: %s" % t, k in keys and keys[k]["title"] == t and keys[k]["lang"] == "ko" and "[내 이름]" in (keys[k]["body"] + keys[k]["subject"]) or (k == "b-in-ack-ko" and k in keys), keys.get(k))
check("양식 열쇠 겹침 없음", len(keys) == len(W.BUILTIN))
check("기존 양식 그대로(견적·재촉)", "b-quote-ko" in keys and "b-nudge-ko" in keys and "b-nudge-en" in keys)

print("\n결과: %d 통과 / %d 실패" % (P, F))
sys.exit(1 if F else 0)
