# -*- coding: utf-8 -*-
"""z1134 — 이음에서 참석자를 바꾸면 WORKS 회의록 명단도 따라가게

대표 지시(2026-09-29): 「이음에서 참석자를 나중에 바꿔도 WORKS 명단은 「회의 시작」을 누른 시점 값으로
남습니다 → 이거 맞춰」 · 대표 결정 3가지(「진행해」):
  ① 명단에서 빠진 사람은 그 뒤로 못 고친다(이미 올린 녹음·글은 남는다)
  ② 녹음 중인 사람은 명단에서 빠져도 녹음이 끊기지 않는다(그 회의 동안은 명단에 남긴다)
  ③ 참석자 칸 글(attendees_text)도 이음 명단대로 다시 적는다

바꾸는 것 (app/main.py 3곳):
  1) `_msg_sync_attendees(c, m, att_emps, externals)` 새 도우미 (`_msg_owner_disp` 앞)
  2) `POST /api/meeting/msg/attendees` 새 입구 (`msg/status` 앞) — 서버 전용·이음을 되부르지 않음
  3) `POST /api/meeting/msg/start` 가 **이미 있는 회의록**이면 같은 도우미로 다시 맞춤(안전망)

사용: python patch_z1134.py <바꿀 main.py 경로>
"""
import io
import os
import sys

HELPER = '''def _msg_sync_attendees(c, m, att_emps, externals) -> dict:
    """z1134: 이음 참석자 명단 → 그 회의의 WORKS 명단(meeting_attendees)을 그대로 맞춘다.
    - 사번은 `_msg_user_by_empno` 로 **정확히 1명**일 때만 연결(추측 연결 금지 · 사람 참조는 ID)
    - 계정 없는 참석자(externals)는 이름만(user_id=NULL)
    - 🔴 **녹음 중인 사람은 빼지 않는다**(대표 결정 2026-09-29) — 명단에서 빠져도 녹음이 끊기면 안 된다
    - 작성자(owner)·이음 등록 담당(msg_organizer_id)의 권한은 명단과 무관(권한 함수가 따로 본다)
    - `meetings.attendees_text` 도 같은 순서로 다시 적는다(대표 결정: 이음 명단이 기준)
    반환: {"added":[이름], "removed":[이름], "kept":그대로인 수, "held":[녹음 중이라 남긴 이름]}
    """
    out = {"added": [], "removed": [], "kept": 0, "held": []}
    mid = (m or {}).get("id")
    if not mid or c is None:
        return out
    # ① 받은 사번 → 계정(정확히 1명만) · 보낸 순서 유지 · 중복 제거
    want_users, want_uid = [], set()
    for e in (att_emps or []):
        au = _msg_user_by_empno(c, e)
        if au and au["id"] not in want_uid:
            want_uid.add(au["id"])
            want_users.append(au)
    want_ext, want_nm = [], set()
    for nm in (externals or []):
        nm = str(nm or "").strip()
        if nm and nm not in want_nm:
            want_nm.add(nm)
            want_ext.append(nm)
    # ② 지금 녹음 중인 사람(rec_json 의 by) 은 명단에서 빼지 않는다
    hold_uid = None
    if str((m.get("rec_state") or "")).strip() == "recording":
        try:
            hold_uid = (_rec_info(m) or {}).get("by") or None
        except Exception:
            hold_uid = None
    # ③ 지금 명단과 견줘 뺄 사람만 뺀다
    cur = [dict(r) for r in c.execute(
        "SELECT id, user_id, name FROM meeting_attendees WHERE meeting_id=? ORDER BY id", (mid,))]
    for r in cur:
        uid, nm = r.get("user_id"), str(r.get("name") or "")
        if uid:
            if uid in want_uid:
                out["kept"] += 1
                continue
            if hold_uid and uid == hold_uid:      # 녹음 중 — 그대로 둔다
                out["held"].append(nm)
                out["kept"] += 1
                continue
        elif nm and nm in want_nm:
            out["kept"] += 1
            continue
        c.execute("DELETE FROM meeting_attendees WHERE id=?", (r["id"],))
        out["removed"].append(nm)
    # ④ 새로 온 사람만 넣는다
    have_uid = set(r["user_id"] for r in cur if r.get("user_id"))
    have_nm = set(str(r.get("name") or "") for r in cur if not r.get("user_id"))
    for au in want_users:
        if au["id"] not in have_uid:
            c.execute("INSERT INTO meeting_attendees(meeting_id, user_id, name) VALUES(?,?,?)",
                      (mid, au["id"], au["name"]))
            out["added"].append(au["name"])
    for nm in want_ext:
        if nm not in have_nm:
            c.execute("INSERT INTO meeting_attendees(meeting_id, user_id, name) VALUES(?,?,?)",
                      (mid, None, nm))
            out["added"].append(nm)
    # ⑤ 참석자 칸 글도 같은 순서로(녹음 중이라 남긴 사람은 뒤에 붙인다)
    seen, uniq = set(), []
    for n in ([au["name"] for au in want_users] + want_ext + list(out["held"])):
        n = str(n or "").strip()
        if n and n not in seen:
            seen.add(n)
            uniq.append(n)
    c.execute("UPDATE meetings SET attendees_text=? WHERE id=?", (", ".join(uniq)[:1000], mid))
    return out


'''

ENDPOINT = '''@app.post("/api/meeting/msg/attendees")
async def api_meeting_msg_attendees(req: Request):
    """[서버 전용] z1134 — 이음에서 참석자를 바꿔 **저장한 뒤** 부르는 입구.
    그 회의의 WORKS 명단(meeting_attendees · 참석자 칸)을 이음 명단으로 맞춘다.
    body: {msg_meeting_id: 이음 회의 id, attendee_employee_nos: [사번...], externals: [계정 없는 이름...]}
    - 회의록이 아직 없으면(「▶ 회의 시작」 전) **아무것도 만들지 않는다** → {"ok":true,"result":"none"}
    - 🔴 이음을 되부르지 않는다(z1123 규칙 그대로).
    - 🔴 `attendee_employee_nos` 칸이 아예 없으면 거절한다 — 부르는 쪽 실수로 전원이 지워지지 않게."""
    if not _msg_service_key_ok(req):
        return JSONResponse({"ok": False, "error": "forbidden"}, 403)
    try:
        d = await req.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "json_required"}, 400)
    if not isinstance(d, dict):
        return JSONResponse({"ok": False, "error": "json_required"}, 400)
    try:
        msg_id = int(d.get("msg_meeting_id") or 0)
    except (TypeError, ValueError):
        msg_id = 0
    if msg_id <= 0:
        return JSONResponse({"ok": False, "error": "msg_meeting_id_required"}, 400)
    if not isinstance(d.get("attendee_employee_nos"), list):
        return JSONResponse({"ok": False, "error": "attendee_employee_nos_required"}, 400)
    att_emps = [str(x).strip() for x in d["attendee_employee_nos"] if str(x).strip()][:200]
    externals = [str(x).strip()[:80] for x in (d.get("externals") or []) if str(x).strip()][:30]
    with db_session() as c:
        row = c.execute("SELECT * FROM meetings WHERE msg_meeting_id=?", (msg_id,)).fetchone()
        if not row:
            return JSONResponse({"ok": True, "result": "none"})
        m = dict(row)
        r = _msg_sync_attendees(c, m, att_emps, externals)
    if r["added"] or r["removed"]:
        print("[MSG-ATT] 회의 %s 참석자 +%d -%d (그대로 %d)%s"
              % (m["id"], len(r["added"]), len(r["removed"]), r["kept"],
                 (" · 녹음 중이라 남김 %d" % len(r["held"])) if r["held"] else ""))
    return JSONResponse({"ok": True, "result": "synced", "meeting_id": m["id"],
                         "added": len(r["added"]), "removed": len(r["removed"]),
                         "kept": r["kept"], "held": len(r["held"])})


'''

RESYNC = '''        if not created and isinstance(d.get("attendee_employee_nos"), list):
            # z1134 안전망: 이미 있는 회의록이면 그때의 이음 명단으로 다시 맞춘다(그 사이 참석자가 바뀌었을 수 있다)
            try:
                _sr = _msg_sync_attendees(c, m, att_emps, externals)
                if _sr["added"] or _sr["removed"]:
                    print("[MSG-ATT] 회의 시작 때 명단 맞춤 — 회의 %s +%d -%d"
                          % (m["id"], len(_sr["added"]), len(_sr["removed"])))
                    m = dict(c.execute("SELECT * FROM meetings WHERE id=?", (m["id"],)).fetchone())
            except Exception as _se:
                print("[MSG-ATT] 회의 시작 때 명단 맞추기 실패(회의록은 그대로): %r" % (_se,))
'''


def main():
    if len(sys.argv) < 2:
        print("사용: python patch_z1134.py <main.py 경로>")
        return 2
    p = sys.argv[1]
    if not os.path.exists(p):
        print("없는 파일:", p)
        return 2
    src = io.open(p, encoding="utf-8").read()

    if "_msg_sync_attendees" in src:
        print("이미 z1134 가 들어 있음 — 건너뜀:", p)
        return 0

    steps = [
        ("① 도우미 _msg_sync_attendees", "def _msg_owner_disp(c, uid) -> str:", HELPER, "before"),
        ("② 입구 POST /api/meeting/msg/attendees", '@app.post("/api/meeting/msg/status")', ENDPOINT, "before"),
        ("③ msg/start 안전망",
         '        m = dict(row)\n        if org_id and not m.get("msg_organizer_id"):', RESYNC, "after-first-line"),
    ]
    for label, anchor, block, how in steps:
        n = src.count(anchor)
        if n != 1:
            print("자리 못 찾음(%d개): %s" % (n, label))
            return 3
        if how == "before":
            src = src.replace(anchor, block + anchor, 1)
        else:   # 'm = dict(row)' 줄 **뒤**에 끼워 넣는다
            head = "        m = dict(row)\n"
            i = src.index(anchor) + len(head)
            src = src[:i] + block + src[i:]
        print("적용:", label)

    bak = p + ".bak_z1134"
    if not os.path.exists(bak):
        io.open(bak, "w", encoding="utf-8", newline="").write(io.open(p, encoding="utf-8").read())
    tmp = p + ".tmp_z1134"
    io.open(tmp, "w", encoding="utf-8", newline="").write(src)
    os.replace(tmp, p)

    import py_compile
    py_compile.compile(p, doraise=True)
    print("문법 검사 통과 ·", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
