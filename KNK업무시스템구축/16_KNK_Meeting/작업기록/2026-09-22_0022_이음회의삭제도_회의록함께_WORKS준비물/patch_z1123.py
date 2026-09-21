# -*- coding: utf-8 -*-
"""z1123 — 이음 🗓 회의에서 지워도 WORKS 회의록까지 함께 (대표 결정 2026-09-22 00시)
  ① 새 서버 전용 입구 POST /api/meeting/msg/delete — 이음이 자기 회의를 지우기 **전에** 부른다
     (회의록 작성자·관리자일 때만 지움 · 아니면 남기고 까닭 · 🔴 여기서 이음을 다시 부르지 않음)
  ② msg/status 에 can_delete — 이음 🗓 「삭제」 확인 창이 「📋 WORKS 회의록도 함께 지워집니다 / 남습니다」를 미리
  ③ WORKS 🗑 삭제 → 이음이 시작 전 회의 참석자에게 취소 알림을 보냈으면(notified) 몇 명인지 알림
사용: py patch_z1123.py <앱 사본 폴더(app/ 가 들어 있는 곳)>
기준: 운영 z1122(main e7321fa1 · sso_client b22ca107 · meeting_form 4053dd7a)"""
import hashlib
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = sys.argv[1]
BASE = {"app/main.py": "e7321fa1", "app/sso_client.py": "b22ca107", "app/templates/meeting_form.html": "4053dd7a"}


def rd(rel):
    raw = open(os.path.join(ROOT, rel), "rb").read()
    h = hashlib.sha256(raw).hexdigest()[:8]
    assert h == BASE[rel], f"{rel} 기준이 다름: {h} (기대 {BASE[rel]})"
    s = raw.decode("utf-8")
    assert "\r\n" not in s, f"{rel} 줄바꿈 CRLF — 확인 필요"
    return s


def wr(rel, s):
    p = os.path.join(ROOT, rel)
    tmp = p + ".tmp_z1123"
    with io.open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(s)
    os.replace(tmp, p)
    print(f"  [OK] {rel} → {hashlib.sha256(s.encode('utf-8')).hexdigest()[:8]}")


def rep(s, old, new, name, count=1):
    n = s.count(old)
    assert n == count, f"{name}: 기준 글 {n}곳(기대 {count})"
    return s.replace(old, new)


# ─────────────────────────── main.py ───────────────────────────
s = rd("app/main.py")

# ③ WORKS 🗑 삭제 결과에 notified(이음이 취소 알림을 보낸 참석자 수) — 없으면 칸 자체를 싣지 않는다(모양 그대로)
s = rep(s,
        '        msg = {"linked": True, "deleted": kind in ("deleted", "already"), "reason": kind}\n',
        '        msg = {"linked": True, "deleted": kind in ("deleted", "already"), "reason": kind}\n'
        '        if res.get("notified"):   # z1123: 시작 전 회의면 이음이 참석자에게 「회의가 취소되었습니다」 — 몇 명에게 갔나(대표 결정 2026-09-22)\n'
        '            msg["notified"] = res["notified"]\n',
        "삭제 결과 notified")

# ② msg/status 에 can_delete (모아보기 msg-cards 는 보기 전용이라 그대로)
s = rep(s,
        '                  #   「🎙 이어서 녹음」으로(대표 지시 2026-09-21 · 세션 10). WORKS 회의 화면의 REC.mine(z1120)과 같은 판단.\n'
        '                  "rec_mine": _rv["state"] == "recording" and bool(_rv["mine"])}\n',
        '                  #   「🎙 이어서 녹음」으로(대표 지시 2026-09-21 · 세션 10). WORKS 회의 화면의 REC.mine(z1120)과 같은 판단.\n'
        '                  "rec_mine": _rv["state"] == "recording" and bool(_rv["mine"]),\n'
        '                  # z1123: 보는 사람이 이 회의록을 지울 수 있나(작성자·관리자 = WORKS 🗑 삭제와 같은 판단) — 이음 🗓 회의 「삭제」\n'
        '                  #   확인 창이 「📋 WORKS 회의록도 함께 지워집니다 / 남습니다」를 미리 보이게(대표 결정 2026-09-22).\n'
        '                  "can_delete": bool(viewer) and _can_delete_meeting(viewer, m)}\n',
        "msg/status can_delete")

# ① 새 입구 — msg/status 바로 뒤(🗓 회의 카드 모아보기 구역 앞)
NEW_EP = '''

@app.post("/api/meeting/msg/delete")
async def api_meeting_msg_delete(req: Request):
    """[서버 전용] 이음 🗓 회의에서 회의를 지울 때 그 회의의 WORKS 회의록도 함께 지운다 (z1123 · 대표 결정 2026-09-22).
    ⭐ 이음은 자기 회의를 지우기 **전에** 이것을 부르고 200 ok 를 받아야 지운다 — WORKS 에 못 닿으면 이음도 안 지운다
      (한쪽만 지워진 채 남지 않게 · WORKS 🗑 삭제 z1122 와 거꾸로 같은 규칙).
    회의록은 WORKS 규칙 그대로 작성자(▶ 회의 시작을 누른 사람)·관리자(admin/ceo)가 지울 때만 — 아니면 남기고 까닭을 돌려준다.
    🔴 여기서는 이음을 다시 부르지 않는다(이음이 지우는 중 — 서로 부르며 돌지 않게).
    body: {msg_meeting_id, employee_no(지우는 사람 사번)}
    → 200 {ok: true, result: "deleted" | "none"(회의록 없음) | "kept", reason?: "not_allowed" | "viewer_not_found", works_meeting_id?}"""
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
    out = {"ok": True, "result": "none"}
    with db_session() as c:
        row = c.execute("SELECT * FROM meetings WHERE msg_meeting_id=?", (msg_id,)).fetchone()
        if row:
            m = dict(row)
            out["works_meeting_id"] = m["id"]
            viewer = _msg_user_by_empno(c, d.get("employee_no"))
            if not viewer:
                out.update(result="kept", reason="viewer_not_found")
            elif not _can_delete_meeting(viewer, m):
                out.update(result="kept", reason="not_allowed")
            else:
                # 자식(결정·할일·참석자)은 FK ON DELETE CASCADE — WORKS 🗑 삭제(api_meeting_delete)와 같은 한 줄
                c.execute("DELETE FROM meetings WHERE id=?", (m["id"],))
                out["result"] = "deleted"
                try:
                    log_activity(c, viewer["id"], "meeting_delete",
                                 f"{viewer['name']} 이음 🗓 회의에서 삭제 — 회의록도 함께: {(m.get('title') or '')[:60]}",
                                 team_id=viewer.get("team_id"))
                except Exception as _le:
                    print(f"[MEETING-MSG] 활동기록 실패(삭제는 완료): {_le}")
    try:   # 이음 회의가 곧 지워진다 — 「🗓 회의 카드 모아보기」 30초 저장본을 비워 바로 빠지게(z1122 와 같게)
        with _MSG_CARDS_LOCK:
            _MSG_CARDS_CACHE.clear()
    except Exception as _e:
        print(f"[MSG-CARDS] 저장본 비우기 실패(무시): {_e}")
    return JSONResponse(out)
'''
s = rep(s,
        '    return JSONResponse({"ok": True, "items": items})\n\n\n'
        '# ════════════════════════════════════════════════════════════════════════\n'
        '#  🗓 회의 카드 모아보기 (2026-09-17 대표 지시)\n',
        '    return JSONResponse({"ok": True, "items": items})\n' + NEW_EP + '\n\n'
        '# ════════════════════════════════════════════════════════════════════════\n'
        '#  🗓 회의 카드 모아보기 (2026-09-17 대표 지시)\n',
        "새 입구 자리")
assert s.count('@app.post("/api/meeting/msg/delete")') == 1
wr("app/main.py", s)

# ─────────────────────────── sso_client.py ───────────────────────────
s = rd("app/sso_client.py")
s = rep(s,
        '    if r.status_code == 200 and d and d.get("ok"):\n'
        '        return {"kind": "already" if d.get("already") else "deleted"}\n',
        '    if r.status_code == 200 and d and d.get("ok"):\n'
        '        out = {"kind": "already" if d.get("already") else "deleted"}\n'
        '        try:   # z1123: 시작 전 회의면 이음이 참석자에게 「회의가 취소되었습니다」를 보내고 몇 명인지 돌려준다(대표 결정 2026-09-22)\n'
        '            n = int(d.get("notified") or 0)\n'
        '        except (TypeError, ValueError):\n'
        '            n = 0\n'
        '        if n > 0:\n'
        '            out["notified"] = n\n'
        '        return out\n',
        "이음 응답 notified")
wr("app/sso_client.py", s)

# ─────────────────────────── meeting_form.html ───────────────────────────
s = rd("app/templates/meeting_form.html")
s = rep(s,
        "          : '회의록을 지웠습니다.\\n\\n이음 회의는 등록한 사람(또는 관리자)만 지울 수 있어 그대로 남았습니다.');\n"
        "      }\n",
        "          : '회의록을 지웠습니다.\\n\\n이음 회의는 등록한 사람(또는 관리자)만 지울 수 있어 그대로 남았습니다.');\n"
        "      }\n"
        "      else if (mg.notified>0){   // z1123 (대표 결정 2026-09-22): 시작 전 회의 — 이음이 참석자에게 취소 알림을 보냈다\n"
        "        alert('회의록과 이음 회의를 지웠습니다.\\n\\n🔔 시작 전 회의라 참석자 '+mg.notified+'명에게 「회의가 취소되었습니다」 알림이 갔습니다.');\n"
        "      }\n",
        "삭제 뒤 취소 알림 안내")
wr("app/templates/meeting_form.html", s)
print("[OK] z1123 패치 끝")
