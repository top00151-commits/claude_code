# -*- coding: utf-8 -*-
"""z1209 검사 — 이음 회의 상태 답에 제목·참석자 세 칸(title · att_emps · att_ext).
사용: py q209_check.py <나무 폴더(app_base·app_new 가 들어 있는 곳)>
  app_base(지금 운영) = 8996 · app_new(z1209) = 8997 을 띄워 같은 질문을 던진다.
요약 줄: 「결과: 통과 N · 실패 N」"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")    # 회귀 묶음은 PYTHONIOENCODING 없이 부른다(cp949 로 ✅ 를 못 찍음)
ROOT = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
KEY = "q209-test-key"
P = F = 0


def ok(cond, name, info=""):
    global P, F
    if cond:
        P += 1
        print("  ✅", name)
    else:
        F += 1
        print("  ❌", name, ("· " + str(info)[:400]) if info else "")


def start(tree, port):
    app = os.path.join(ROOT, tree)
    log = open(os.path.join(ROOT, "srv09_%d.log" % port), "w", encoding="utf-8")
    pr = subprocess.Popen([PY, os.path.join(HERE, "run_q209_app.py"), app, str(port)], stdout=log, stderr=subprocess.STDOUT)
    for _ in range(240):
        time.sleep(0.5)
        try:
            if "READY" in open(os.path.join(ROOT, "srv09_%d.log" % port), encoding="utf-8").read():
                ids = json.load(open(os.path.join(app, "q209_ids.json"), encoding="utf-8"))
                return pr, ids
        except Exception:
            pass
    pr.kill()
    raise SystemExit("서버가 안 떴다: %s" % tree)


def call(port, path, body=None, key=KEY, method="POST", cookie=None):
    data = json.dumps(body or {}).encode("utf-8")
    rq = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path), data=data, method=method)
    rq.add_header("Content-Type", "application/json")
    if key is not None:
        rq.add_header("X-SSO-Service-Key", key)
    if cookie:
        rq.add_header("Cookie", "tuser=%s" % cookie)
    try:
        with urllib.request.urlopen(rq, timeout=20) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {}


def status(port, emp, ids):
    return call(port, "/api/meeting/msg/status", {"employee_no": emp, "msg_meeting_ids": ids})


pb, ib = start("app_base", 8996)
pn, inn = start("app_new", 8997)
try:
    NEWK = {"title", "att_emps", "att_ext"}
    print("== ① 지금 운영(바탕)에는 세 칸이 없다(반대 시험) ==")
    sb, jb = status(8996, "901", [801, 802, 803, 899])
    ok(sb == 200 and all(not (NEWK & set(v)) for v in jb["items"].values()), "바탕 답에 title·att_emps·att_ext 없음", jb)

    print("== ② 새 판 — 세 칸 ==")
    sn, jn = status(8997, "901", [801, 802, 803, 899])
    it = jn["items"]
    ok(sn == 200 and jn.get("ok") is True, "200 · ok")
    ok(it["801"].get("title") == "가상전기_검사설비 협의", "M1 제목", it["801"])
    ok(it["801"].get("att_emps") == ["901", "902"], "M1 att_emps = 계정 연결된 사람의 사번(적은 차례)", it["801"].get("att_emps"))
    ok(it["801"].get("att_ext") == ["가상고객 홍길동 부장"], "M1 att_ext = 계정 없는 이름만", it["801"].get("att_ext"))
    ok("박무사번" not in json.dumps(it["801"], ensure_ascii=False), "계정은 있는데 사번이 빈 사람은 어느 쪽에도 없음")
    ok(it["803"].get("title") == "참석 없는 회의" and it["803"].get("att_emps") == [] and it["803"].get("att_ext") == [],
       "참석 없는 회의 = 빈 배열 둘", it["803"])
    ok(set(it["899"].keys()) == {"stage", "can_view"} and it["899"]["stage"] == "none", "회의록 없는 회의 = 두 칸 그대로", it["899"])
    ok(all(isinstance(it[k].get("title"), str) and isinstance(it[k].get("att_emps"), list)
           and isinstance(it[k].get("att_ext"), list) for k in ("801", "802", "803")), "모양: 글 · 배열 · 배열")

    print("== ③ 볼 수 없는 사람이 물어도 칸은 실린다(서버끼리 답) · 회의록 주소는 여전히 안 준다 ==")
    so, jo = status(8997, "905", [802])
    o = jo["items"]["802"]
    ok(o["can_view"] is False and "url" not in o and "meeting_id" not in o, "비공개 회의 · 못 보는 사람 → 주소·번호 없음(그대로)", o)
    ok(o.get("title") == "비공개 시험 회의" and o.get("att_emps") == ["902"], "그래도 제목·참석 사번은 실림(요청대로)", o)
    su, ju = status(8997, "없는사번", [801])
    ok(ju["items"]["801"]["can_view"] is False and ju["items"]["801"].get("att_emps") == ["901", "902"], "모르는 사번이 물어도 실림")

    print("== ④ 열쇠 없으면 그대로 거절 ==")
    ok(call(8997, "/api/meeting/msg/status", {"msg_meeting_ids": [801]}, key=None)[0] == 403, "열쇠 없음 403")
    ok(call(8997, "/api/meeting/msg/status", {"msg_meeting_ids": [801]}, key="wrong-key")[0] == 403, "틀린 열쇠 403")

    print("== ⑤ 다른 칸은 바탕과 글자 그대로 ==")
    same = True
    for k in ("801", "802", "803", "899"):
        a = dict(jb["items"][k])
        b = {x: y for x, y in it[k].items() if x not in NEWK}
        if a != b:
            same = False
            print("    다름", k, a, b)
    ok(same, "stage·can_view·started_by·녹음·종료·삭제·주소 칸이 바탕과 같음")

    print("== ⑥ 이음웍스 회의록에서 고치면 다음 물음에 바로 보인다(대표 사례: 제목 오타 · 참석자 더하고 빼기) ==")
    mid = inn["meetings"]["M1"]
    sp, jp = call(8997, "/api/meeting/%d" % mid,
                  {"title": "가상전자_검사설비 협의", "attendees_text": "김한국, Nguyen Van A, 가상고객 홍길동 부장, 새고객 이몽룡"},
                  key=None, method="PUT", cookie=inn["users"]["me"])
    ok(sp == 200 and jp.get("ok"), "회의록 고쳐 저장 200", (sp, jp))
    s2, j2 = status(8997, "901", [801])
    m1 = j2["items"]["801"]
    ok(m1.get("title") == "가상전자_검사설비 협의", "고친 제목이 바로 실림", m1.get("title"))
    ok(m1.get("att_emps") == ["901", "VN903"], "최민수 빠지고 Nguyen(VN903 · 대문자 그대로) 들어감", m1.get("att_emps"))
    ok(m1.get("att_ext") == ["가상고객 홍길동 부장", "새고객 이몽룡"], "계정 없는 이름도 더해짐", m1.get("att_ext"))

    print("== ⑦ 이음에서 바꾼 명단(z1134 입구)도 같은 답에 그대로 보인다 ==")
    sa, ja = call(8997, "/api/meeting/msg/attendees",
                  {"msg_meeting_id": 803, "attendee_employee_nos": ["902", "905"], "externals": ["외부 손님"]})
    ok(sa == 200 and ja.get("result") == "synced", "이음 명단 맞추기 200", ja)
    s3, j3 = status(8997, "901", [803])
    m3 = j3["items"]["803"]
    ok(sorted(m3.get("att_emps") or []) == ["902", "905"] and m3.get("att_ext") == ["외부 손님"], "이음 쪽 변경이 답에 보임", m3)

    print("== ⑧ 50건 한도·순서 그대로 · 서버 오류 없음 ==")
    s4, j4 = status(8997, "901", list(range(800, 860)))
    ok(s4 == 200 and len(j4["items"]) == 50, "60건 물으면 50건만(그대로)", len(j4.get("items", {})))
    logs = open(os.path.join(ROOT, "srv09_8997.log"), encoding="utf-8").read()
    ok("Traceback" not in logs and " 500 " not in logs, "새 판 서버 기록에 오류 없음", logs[-500:])
finally:
    for pr in (pb, pn):
        pr.kill()
print()
print("결과: 통과 %d · 실패 %d" % (P, F))
sys.exit(1 if F else 0)
