# -*- coding: utf-8 -*-
"""z1122 — 회의록 삭제: 두 번 확인 · 작성자·관리자만 · 이음 회의도 함께(이음 등록자·관리자일 때)

대표 지시(2026-09-21 23시 · 사진 3장 = WORKS 회의록 목록 / 「🗓 회의 카드 모아보기」 / 이음 「회의 알림」 방):
  1. 회의록 상세에서 삭제할 때 꼭 「삭제할까요?」 확인 — 한 번 더 확인 · 삭제는 회의 작성자 또는 관리자만
  2. 삭제된 회의는 모아보기(사진2)·이음 회의 알림(사진3)에서도 사라지게
대표 결정(같은 때 · 질문 4개 답):
  · 이음 회의까지 함께 삭제 · 이음 알림 카드는 방에서 아예 숨김 · 이음 회의까지 지우는 건 **이음 등록자 또는 관리자**
  · 이음 쪽(삭제 입구·카드 숨김)은 세션 10 에 넘김 → WORKS 는 먼저 준비(입구가 없으면 회의록만 지우고 알림)

지금(고치기 전): 확인 한 번(「이 회의록을 삭제할까요?」) · 서버가 작성자·관리자(admin/ceo)만 허락 · 이음 회의는 그대로 남음.
고침:
  ① meeting_form.html — 확인 두 번(제목·날짜·지워지는 것·이음 회의가 함께 지워지는지 미리 알림 → 「⚠ 정말 삭제할까요? 되돌릴 수 없습니다」)
     · 결과 알림(이음 회의가 남았으면 까닭) · 실패는 화면 가운데 알림(전엔 아래쪽 저장 줄에 떠서 휴대폰에선 안 보였다)
  ② main.py 삭제 입구 — 이음에서 온 회의면 이음에 「이 회의 지워 주세요」(사번 실어서) → 이음이 등록자·관리자인지 판단
     · 🔴 이음에 닿지 못하면(연결 실패·키 거부·오류) **아무것도 지우지 않는다**(한쪽만 지워진 채 남지 않게)
     · 이음이 거절(등록자 아님)·사번 모름·입구 없음(세션 10 배포 전) → 회의록만 지우고 그 까닭을 돌려준다
     · 지운 뒤 모아보기 30초 저장본을 비운다(지운 회의가 바로 빠지게)
     · 상세 화면에 msg_del(none·yes·no) — 확인 글에서 이음 회의가 함께 지워지는지 미리 알린다(최종 판단은 이음)
  ③ sso_client.py — delete_msg_meeting(): POST {이음}/api/works/meetings/delete · 공유키 · 결과 종류로 정리
사용: py patch_del.py <원본 폴더(main_base.py·sso_client_base.py·meeting_form_base.html)> <결과 폴더>
"""
import hashlib
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
SRC, DST = sys.argv[1], sys.argv[2]
os.makedirs(DST, exist_ok=True)


def load(name):
    s = io.open(os.path.join(SRC, name), encoding="utf-8", newline="").read()
    assert "\r\n" not in s, name + ": CRLF 원본 — git show 결과(LF)를 쓸 것"
    return s


def save(name, s):
    with io.open(os.path.join(DST, name), "w", encoding="utf-8", newline="") as f:
        f.write(s)
    print("[OK] %-20s sha256 %s" % (name, hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]))


def sub1(s, old, new, tag):
    n = s.count(old)
    assert n == 1, "%s: 앵커 %d개(1개여야 함)" % (tag, n)
    return s.replace(old, new)


# ══════════════════════════════════════════════════════════════════════
# 1. sso_client.py — 이음 회의 지우기 요청
# ══════════════════════════════════════════════════════════════════════
sc = load("sso_client_base.py")
sc = sub1(sc, '''    items = d.get("items")
    if not isinstance(items, list):
        return {"ok": False, "error": "이음 응답 형식이 다릅니다."}
    return {"ok": True, "items": items, "truncated": bool(d.get("truncated"))}
''', '''    items = d.get("items")
    if not isinstance(items, list):
        return {"ok": False, "error": "이음 응답 형식이 다릅니다."}
    return {"ok": True, "items": items, "truncated": bool(d.get("truncated"))}


# =====================================================
# z1122 (대표 결정 2026-09-21): WORKS 회의록을 지우면 이음 회의도 함께 지운다.
#   · 이음 회의까지 지우는 건 **이음 등록자 또는 관리자**만 — 이음이 판단한다(WORKS 가 흉내내지 않음).
#   · 이음은 회의를 지우고 그 회의의 「회의 알림」 카드를 방에서 숨긴다(세션 10 · POST /api/works/meetings/delete).
#   반환 {"kind": ...}
#     deleted · already(이미 없음)         → 이음 회의가 없어졌다
#     not_allowed · viewer_not_found       → 이음이 거절 — 회의록만 지운다
#     not_ready(이음에 입구가 아직 없음)    → 회의록만 지운다(세션 10 배포 전)
#     refused(키 없음·거부) · unreachable  → 🔴 아무것도 지우지 않는다(한쪽만 지워지지 않게)
# =====================================================
def delete_msg_meeting(msg_meeting_id, employee_no, works_meeting_id=None, timeout=8.0) -> dict:
    emp = str(employee_no or "").strip()
    if not emp:
        return {"kind": "viewer_not_found"}          # 사번 없는 계정 — 이음이 누군지 알 수 없다
    _key = get_service_key()
    if not _key:
        return {"kind": "refused", "error": "이음 연결 키가 설정되지 않았습니다(관리자 확인 필요)."}
    url = f"{MESSENGER_INTERNAL_BASE}/api/works/meetings/delete"
    try:
        r = httpx.post(url, headers={"X-SSO-Service-Key": _key},
                       json={"msg_meeting_id": int(msg_meeting_id), "employee_no": emp,
                             "works_meeting_id": works_meeting_id},
                       timeout=timeout)
    except Exception as e:
        print(f"[MSG-DEL] 이음 연결 실패: {type(e).__name__}: {str(e)[:160]}")
        return {"kind": "unreachable", "error": "이음에 연결하지 못했습니다."}
    try:
        d = r.json()
    except Exception:
        d = None
    if not isinstance(d, dict):
        d = None
    err = (d or {}).get("error")
    if r.status_code == 200 and d and d.get("ok"):
        return {"kind": "already" if d.get("already") else "deleted"}
    if err == "not_allowed":
        return {"kind": "not_allowed"}
    if err == "viewer_not_found":
        return {"kind": "viewer_not_found"}
    if r.status_code == 404 and d is None:
        return {"kind": "not_ready"}                 # 이음에 삭제 입구가 아직 없다(글자 404 화면)
    if r.status_code == 403:
        return {"kind": "refused", "error": "이음이 요청을 거부했습니다(연결 키 확인 필요)."}
    print(f"[MSG-DEL] 이음 응답 오류: {r.status_code} {str(err or '')[:80]}")
    return {"kind": "unreachable", "error": f"이음 응답 오류({r.status_code})."}
''', "sso_client delete_msg_meeting")
save("sso_client.py", sc)

# ══════════════════════════════════════════════════════════════════════
# 2. main.py — 삭제 입구 · 상세 화면 msg_del
# ══════════════════════════════════════════════════════════════════════
m0 = load("main_base.py")
m = sub1(m0, '''        if not _can_delete_meeting(u, dict(m)):   # 등록 담당은 고치기만(삭제 X) — 2026-09-15 대표 결정
            return JSONResponse({"ok": False, "error": "삭제 권한이 없습니다."}, 403)
        # 자식(결정·할일·참석자)은 FK ON DELETE CASCADE 로 정리.
        # 단, 일일카드(tasks)로 연동된 것은 카드 자체를 지우지 않음(이미 독립 업무).
        c.execute("DELETE FROM meetings WHERE id=?", (mid,))
    return JSONResponse({"ok": True})
''', '''        m = dict(m)
        if not _can_delete_meeting(u, m):   # 등록 담당은 고치기만(삭제 X) — 2026-09-15 대표 결정 · 작성자·관리자만(09-21 대표 재확인)
            return JSONResponse({"ok": False, "error": "삭제 권한이 없습니다."}, 403)
    # z1122 (대표 결정 2026-09-21): 이음에서 온 회의면 이음 회의(🗓 달력·회의 알림 카드·모아보기 카드)도 함께 지운다.
    #   이음 회의까지 지우는 건 이음 등록자·관리자만 — 이음이 판단(아니면 회의록만 지우고 까닭을 알린다).
    #   🔴 이음에 닿지 못하면(연결 실패·키 거부·오류) 아무것도 지우지 않는다 — 한쪽만 지워진 채 남지 않게.
    #   이음에 삭제 입구가 아직 없으면(세션 10 배포 전) 회의록만 지우고 알린다.
    msg = {"linked": False}
    if m.get("msg_meeting_id"):
        from . import sso_client
        from starlette.concurrency import run_in_threadpool
        res = await run_in_threadpool(sso_client.delete_msg_meeting, m["msg_meeting_id"],
                                      u.get("employee_no") or "", mid)
        kind = res.get("kind") or "unreachable"
        if kind in ("unreachable", "refused"):
            return JSONResponse({"ok": False, "error": (res.get("error") or "이음에 연결하지 못했습니다.")
                                 + " 회의록을 지우지 않았습니다 — 잠시 뒤 다시 눌러 주세요."}, 503)
        msg = {"linked": True, "deleted": kind in ("deleted", "already"), "reason": kind}
    with db_session() as c:
        # 자식(결정·할일·참석자)은 FK ON DELETE CASCADE 로 정리.
        # 단, 일일카드(tasks)로 연동된 것은 카드 자체를 지우지 않음(이미 독립 업무).
        c.execute("DELETE FROM meetings WHERE id=?", (mid,))
    try:   # z1122: 「🗓 회의 카드 모아보기」가 30초 저장본을 보여 주지 않게 — 지운 회의가 바로 빠진다
        with _MSG_CARDS_LOCK:
            _MSG_CARDS_CACHE.clear()
    except Exception as _e:
        print(f"[MSG-CARDS] 저장본 비우기 실패(무시): {_e}")
    return JSONResponse({"ok": True, "msg": msg})
''', "삭제 입구")
m = sub1(m, '''            linked_opp = dict(_r) if _r else None
    return ctx(req, "meeting_form.html", user=u, meeting=m,
''', '''            linked_opp = dict(_r) if _r else None
    # z1122: 🗑 삭제 확인 글 — 이음 회의도 함께 지워지나 미리 알린다(최종 판단은 이음 · 등록자·관리자만)
    _role = (u.get("role") or "").lower()
    _msg_del = ("none" if not m.get("msg_meeting_id") else
                ("yes" if (_role in ("admin", "ceo") or
                           (m.get("msg_organizer_id") and m.get("msg_organizer_id") == u.get("id"))) else "no"))
    return ctx(req, "meeting_form.html", user=u, meeting=m,
''', "상세 msg_del 계산")
m = sub1(m, '''               rec=_rec_view(m, u))   # z1113: 「🔴 녹음 중」 복귀 안내
''', '''               rec=_rec_view(m, u),   # z1113: 「🔴 녹음 중」 복귀 안내
               msg_del=_msg_del)      # z1122: 🗑 삭제 확인 글 — 이음 회의도 함께 지워지나
''', "상세 msg_del 넘기기")
save("main.py", m)

# ══════════════════════════════════════════════════════════════════════
# 3. meeting_form.html — 두 번 확인 · 결과 알림
# ══════════════════════════════════════════════════════════════════════
h = load("meeting_form_base.html")
h = sub1(h, '''  rec: {{ (rec|default({}, true))|tojson }},   {# z1113: 녹음 중 상태(초·저장량) — 창이 닫혀도 이어서 끝낼 수 있게 #}
''', '''  rec: {{ (rec|default({}, true))|tojson }},   {# z1113: 녹음 중 상태(초·저장량) — 창이 닫혀도 이어서 끝낼 수 있게 #}
  msg_del: {{ (msg_del|default('none', true))|tojson }},   {# z1122: 🗑 삭제 때 이음 회의도 함께 지워지나(none·yes·no) — 확인 글에 미리 알림 #}
''', "M.msg_del")
h = sub1(h, '''  async function delMeeting(){
    if (!confirm('이 회의록을 삭제할까요? (이미 일일카드로 보낸 할 일은 그대로 남습니다)')) return;
    var res = await jreq('DELETE','/api/meeting/'+M.id);
    if (res.ok && res.data.ok){ _leaveOk = true; location.href='/meetings'; }
    else { status(res.data.error||'삭제 실패','err'); }
  }
''', '''  async function delMeeting(){
    // z1122 (대표 지시 2026-09-21): 삭제는 **두 번** 확인 — 무엇이 지워지는지·이음 회의도 함께인지 먼저 보이고, 한 번 더 묻는다.
    //   삭제 단추는 작성자·관리자에게만 보이고, 서버도 그 밖의 사람은 막는다(403).
    var ttl=((($('mtgTitle')||{}).value)||'').trim()||'(제목 없음)', dt=((($('mtgDate')||{}).value)||'').trim();
    var md=M.msg_del||'none';
    var q1='🗑 이 회의록을 삭제할까요?\\n\\n「'+ttl+'」'+(dt?' ('+dt+')':'')
      +'\\n\\n녹음·음성 글자·정리·결정·할 일을 더 이상 볼 수 없습니다.\\n(이미 일일카드로 보낸 할 일은 그대로 남습니다)';
    if(md==='yes') q1+='\\n\\n🗓 이음 회의도 함께 지워집니다 — 참석자 달력·회의 알림 카드·회의 카드 모아보기에서 사라집니다.';
    else if(md==='no') q1+='\\n\\n🗓 이음 회의는 남습니다 — 이음에서 회의를 등록한 사람(또는 관리자)만 함께 지울 수 있어, 회의록만 지웁니다.';
    if (!confirm(q1)) return;
    if (!confirm('⚠ 정말 삭제할까요?\\n\\n「'+ttl+'」'+(md==='yes'?' — 이음 회의까지':'')+'\\n지우면 되돌릴 수 없습니다.')) return;
    var bd=$('btnDelete'); if(bd) bd.disabled=true;
    var res = await jreq('DELETE','/api/meeting/'+M.id);
    if (res.ok && res.data.ok){
      var mg=res.data.msg||{};
      if (mg.linked && !mg.deleted){   // 이음 회의가 남았으면 까닭을 알린다
        alert(mg.reason==='not_ready'
          ? '회의록을 지웠습니다.\\n\\n이음 회의는 아직 함께 지울 수 없어 그대로 남았습니다(이음 쪽 준비 중). 필요하면 이음 🗓 회의에서 등록한 사람이 지워 주세요.'
          : '회의록을 지웠습니다.\\n\\n이음 회의는 등록한 사람(또는 관리자)만 지울 수 있어 그대로 남았습니다.');
      }
      _leaveOk = true; location.href='/meetings';
    }
    else {   // 실패는 화면 가운데 알림 — 전엔 아래쪽 저장 줄에 떠서 휴대폰에선 안 보였다
      if(bd) bd.disabled=false;
      alert((res.data&&res.data.error)||'삭제하지 못했습니다.');
    }
  }
''', "delMeeting 두 번 확인")
# ── 아이폰 안내(z1120) — 이음 v817 로 녹음하던 본인 카드에 「🎙 이어서 녹음」이 뜬다(세션 10 전달 23:05)
h = sub1(h, '''        +'<br>실수로 이 창을 닫았으면(✕) 이음 회의 카드의 <b>「📋 회의록 열기」</b>(또는 회의록 목록에서 이 회의)를 누르세요 '
        +'— 맨 위 <b>「🎙 이어서 녹음」</b>으로 바로 이어집니다(그때까지 녹음은 서버에 남아 있습니다).';   // z1120
''', '''        +'<br>실수로 이 창을 닫았으면(✕) 이음 회의 카드의 <b>「🎙 이어서 녹음」</b>(또는 카드 빈 곳)을 누르세요 '
        +'— 이 화면 맨 위 <b>「🎙 이어서 녹음」</b>으로 바로 이어집니다(그때까지 녹음은 서버에 남아 있습니다). '
        +'회의록 목록에서 이 회의를 열어도 됩니다.';   // z1120 · z1122: 이음 v817 카드 단추 이름(녹음하던 본인에게 「🎙 이어서 녹음」)
''', "아이폰 안내 v817")
save("meeting_form.html", h)

# ══════════════════════════════════════════════════════════════════════
# 4. 「🗓 회의 카드 모아보기」 탭 — 이음 v817 과 같은 규칙(세션 10 전달 23:05 §4-2)
#    · msg-cards 에 rec_mine(보는 사람 기준) · 주소는 msg/status 와 같게(정리 끝이어도 녹음 중이면 녹음 화면)
#    · 녹음하던 본인 = 「🎙 이어서 녹음」(빨강) · 카드 빈 곳을 눌러도 그 카드의 회의록 단추와 같게
# ══════════════════════════════════════════════════════════════════════
m = sub1(m, '''            _rv = _rec_view(m)   # z1119: 녹음 중인가(이음 msg/status 와 같은 값) — 탭이 「녹음 중」과 「시작만 누름」을 가른다
            mn = {"stage": _meeting_msg_stage(m), "can_view": can_view,
                  "started_by": _msg_owner_disp(c, m.get("owner_id")),
                  "recording": _rv["state"] == "recording",
                  "rec_secs": _rv["secs"] if _rv["state"] == "recording" else 0}
            if can_view:      # 볼 수 없는 사람에겐 회의록 주소·내용 수를 주지 않는다
                mn["url"] = (f"/meetings/{m['id']}/doc" if mn["stage"] == "done" else f"/meetings/{m['id']}")
''', '''            _rv = _rec_view(m, u)   # z1119: 녹음 중인가(이음 msg/status 와 같은 값) — 탭이 「녹음 중」과 「시작만 누름」을 가른다
            mn = {"stage": _meeting_msg_stage(m), "can_view": can_view,
                  "started_by": _msg_owner_disp(c, m.get("owner_id")),
                  "recording": _rv["state"] == "recording",
                  "rec_secs": _rv["secs"] if _rv["state"] == "recording" else 0,
                  # z1122: 보는 사람이 그 녹음을 시작했나(msg/status z1121 과 같은 값) — 이음 v817 처럼 본인에게만 「🎙 이어서 녹음」
                  "rec_mine": _rv["state"] == "recording" and bool(_rv["mine"])}
            if can_view:      # 볼 수 없는 사람에겐 회의록 주소·내용 수를 주지 않는다
                # z1122: 주소는 msg/status(z1114)와 같게 — 정리가 끝났어도 녹음이 열려 있으면 녹음을 이어가거나 끝낼 화면
                mn["url"] = (f"/meetings/{m['id']}/doc" if (mn["stage"] == "done" and not mn["recording"])
                             else f"/meetings/{m['id']}")
''', "msg-cards rec_mine")
save("main.py", m)

t = load("meetings_base.html")
t = sub1(t, '''.mc-btn.mc-go { background: var(--knk-red); border-color: var(--knk-red); color: #fff; }
''', '''.mc-btn.mc-go { background: var(--knk-red); border-color: var(--knk-red); color: #fff; }
.mc-btn.mc-resume { background: #dc2626; border-color: #dc2626; color: #fff; font-weight: 800; }   /* z1122: 이음 v817 「🎙 이어서 녹음」과 같은 빨강 */
.mc-card.tap { cursor: pointer; }   /* z1122: 회의록 단추가 있는 카드만 — 빈 곳을 눌러도 그 단추와 같게 */
''', "CSS")
t = sub1(t, '''      if (mn.can_view && mn.url) {
        if (st === 'done') {
''', '''      if (mn.can_view && mn.url) {
        if (mn.recording === true && mn.rec_mine === true) {
          // z1122: 창이 닫혀 멈춘 녹음을 하던 본인 — 이음 회의 카드(v817)와 같은 「🎙 이어서 녹음」 · 도착 화면 맨 위 상자(z1120)
          out += '<a class="mc-btn mc-resume" href="' + esc(mn.url) + '">🎙 이어서 녹음</a>';
        } else if (st === 'done') {
''', "minutesHtml 이어서 녹음")
t = sub1(t, '''      return h + minutesHtml(m, hs) + '</article>';
    }
''', '''      var mh = minutesHtml(m, hs);
      // z1122: 회의록 단추가 있는 카드는 빈 곳을 눌러도 그 단추와 같게(이음 v817) — 손가락 모양은 그런 카드에만
      if (mh.indexOf('class="mc-btn') >= 0) h = h.replace('<article class="mc-card ', '<article class="mc-card tap ');
      return h + mh + '</article>';
    }
''', "cardHtml tap")
t = sub1(t, '''    body.addEventListener('click', function(e){
      if (e.target && e.target.closest && e.target.closest('[data-mc-retry]')) loadFirst();
    });
''', '''    body.addEventListener('click', function(e){
      if (e.target && e.target.closest && e.target.closest('[data-mc-retry]')) loadFirst();
    });
    // z1122: 카드 빈 곳 = 그 카드의 회의록 단추(이어서 녹음·회의록 화면·회의록 보기)와 같게 — 이음 v817 과 같은 규칙.
    //   단추·링크·입력·글자 고르기·오른쪽 버튼은 예전대로 · 단추가 없는 카드는 아무 일 없음.
    body.addEventListener('click', function(e){
      if (e.defaultPrevented || e.button) return;
      var tg = e.target;
      if (!tg || !tg.closest || tg.closest('a,button,input,select,textarea,label,[data-mc-retry]')) return;
      var card = tg.closest('article.mc-card.tap'); if (!card) return;
      try { if (String((window.getSelection && window.getSelection()) || '').trim()) return; } catch (_) {}
      var go = card.querySelector('.mc-min a.mc-btn'); if (go) go.click();   // 단추를 누른 것과 똑같이(새 창·화면 전환 규칙 그대로)
    });
''', "카드 누르기")
save("meetings.html", t)

for k, got, want in [("sso def", sc.count("def delete_msg_meeting("), 1),
                     ("main 이음 호출", m.count("sso_client.delete_msg_meeting"), 1),
                     ("main 저장본 비움", m.count("_MSG_CARDS_CACHE.clear()"), 2),   # 원래 1곳(캐시 넘침 정리) + 삭제 뒤 1곳
                     ("main msg_del", m.count("msg_del=_msg_del"), 1),
                     ("html 두 번 확인", h.count("⚠ 정말 삭제할까요?"), 1),
                     ("html M.msg_del", h.count("msg_del: {{"), 1),
                     ("html 안내 v817", h.count("이음 회의 카드의 <b>「🎙 이어서 녹음」</b>(또는 카드 빈 곳)"), 1),
                     ("html 옛 안내 없음", h.count("이음 회의 카드의 <b>「📋 회의록 열기」</b>"), 0),
                     ("main rec_mine 두 곳", m.count('"rec_mine": _rv["state"] == "recording" and bool(_rv["mine"])'), 2),
                     ("cards 이어서 녹음", t.count("mc-btn mc-resume"), 1),
                     ("cards 카드 누르기", t.count("article.mc-card.tap"), 1)]:
    print("   %-16s %d  %s" % (k, got, "OK" if got == want else "⚠ %d 예상" % want))
    assert got == want, k
