# -*- coding: utf-8 -*-
"""z1131 — 「⏹ 회의 종료」 단추(예정 시각 전에 끝났을 때) + 공유 안내를 사실대로
사용: py -3.13 patch_z1131.py <앱 사본 경로>

대표 지시(2026-09-27):
  ① 「회의 종료는 어디서 선택할 수 있지?… 종료시간 이전에 끝났을 때는?」 → 누를 곳이 없었다 → 만든다.
  ② 「녹음기에서 공유를 눌러도 KNK WORKS 가 안 보인다(앱은 설치돼 있어)」
     → 공유 목록에 뜨는 것은 **브라우저가 설치한 WORKS 앱**일 때뿐이다(그 폰에는 이음만 설치돼 있었다).
     → 화면 안내를 「📁 녹음 파일 올리기」를 먼저로 바꾸고, 공유는 「앱을 깔아 두었을 때」로 적는다.

바꾸는 것
  - main.py       : 마이그(ended_at) 등록 · `_can_end_meeting` · `POST /api/meeting/{mid}/end`(되돌리기 포함)
                    · 이음에 넘기는 칸(msg/status · msg-cards)에 `ended` 추가 · 상세 화면에 can_end 넘김
  - meeting_form  : 머리줄 「⏹ 회의 종료」/「✅ 종료됨 · 되돌리기」 · 누를 때 녹음 중이면 먼저 마침 · 안내 글
  - meetings.html : 모아보기 카드 판정에서 `ended` 를 맨 먼저(시간과 상관없이 「✅ 회의 종료」)
"""
import os
import shutil
import sys

if len(sys.argv) < 2:
    print("사용: patch_z1131.py <앱 사본 경로>")
    raise SystemExit(2)
APP = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
P_MAIN = os.path.join(APP, "app", "main.py")
P_FORM = os.path.join(APP, "app", "templates", "meeting_form.html")
P_LIST = os.path.join(APP, "app", "templates", "meetings.html")
P_MIG = os.path.join(APP, "app", "migrations", "m_z1131_meeting_end.py")
done = []


def edit(path, name, old, new, count=1):
    s = open(path, encoding="utf-8").read()
    n = s.count(old)
    if n != count:
        print("  [실패] %s — 찾은 수 %d (바라던 수 %d)" % (name, n, count))
        raise SystemExit(1)
    bak = path + ".bak_z1131"
    if not os.path.exists(bak):
        open(bak, "w", encoding="utf-8").write(s)
    tmp = path + ".tmp_z1131"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(s.replace(old, new))
    os.replace(tmp, path)
    done.append(name)
    print("  [고침] %s" % name)


# ── ⓪ 마이그 파일 넣기 ────────────────────────────────────────────
shutil.copyfile(os.path.join(HERE, "m_z1131_meeting_end.py"), P_MIG)
print("  [넣음] app/migrations/m_z1131_meeting_end.py")
done.append("마이그 파일")

# ── ① 마이그 등록(기동 때 1회) ────────────────────────────────────
edit(P_MAIN, "마이그 등록(ended_at)",
     "    # v5H226z455 (2026-06-15, 대표 지시): 형태 4종(완제품/제품/상품/기타) — 기존 form_type 재동기화 (idempotent)\n",
     "    # z1131 (대표 지시 2026-09-27): 「⏹ 회의 종료」 — meetings.ended_at (idempotent)\n"
     "    try:\n"
     "        from .migrations.m_z1131_meeting_end import migrate as _mend_migrate\n"
     "        from .database import DB_PATH as _DB_PATH_MEND\n"
     "        _rmend = _mend_migrate(_DB_PATH_MEND)\n"
     "        if _rmend.get('added'):\n"
     "            print(f\"[MEETING-END-MIG-Z1131] {_rmend}\")\n"
     "    except Exception as _e:\n"
     "        print(f\"[MEETING-END-MIG-Z1131 ERR] {_e}\")\n"
     "    # v5H226z455 (2026-06-15, 대표 지시): 형태 4종(완제품/제품/상품/기타) — 기존 form_type 재동기화 (idempotent)\n")

# ── ② 누가 종료할 수 있나 ────────────────────────────────────────
edit(P_MAIN, "_can_end_meeting(권한)",
     "def _meeting_due_or_none(s):",
     "def _can_end_meeting(u, m) -> bool:\n"
     "    \"\"\"z1131 「⏹ 회의 종료」 권한: 회의록 작성자(총괄)·관리자/대표 + **이음에 그 회의를 등록한 사람**.\n"
     "    (삭제 권한 + 등록 담당 — 등록 담당은 회의를 열고 닫는 사람이라 종료는 할 수 있게 한다)\"\"\"\n"
     "    if not u or not m:\n"
     "        return False\n"
     "    if _can_delete_meeting(u, m):\n"
     "        return True\n"
     "    return bool(u.get(\"id\")) and m.get(\"msg_organizer_id\") == u.get(\"id\")\n"
     "\n"
     "\n"
     "def _meeting_ended(m) -> bool:\n"
     "    \"\"\"사람이 「⏹ 회의 종료」를 눌러 끝낸 회의인가(시간 규칙보다 먼저 본다).\"\"\"\n"
     "    return bool(((m or {}).get(\"ended_at\") or \"\").strip())\n"
     "\n"
     "\n"
     "def _meeting_due_or_none(s):")

# ── ③ 이음·모아보기에 넘기는 칸에 ended 추가 ─────────────────────
edit(P_MAIN, "msg/status 에 ended",
     "                  # z1123: 보는 사람이 이 회의록을 지울 수 있나(작성자·관리자 = WORKS 🗑 삭제와 같은 판단) —",
     "                  # z1131: 사람이 「⏹ 회의 종료」를 눌렀나 — 이음 카드가 시간 규칙보다 먼저 본다\n"
     "                  \"ended\": _meeting_ended(m),\n"
     "                  \"ended_at\": (m.get(\"ended_at\") or \"\"),\n"
     "                  # z1123: 보는 사람이 이 회의록을 지울 수 있나(작성자·관리자 = WORKS 🗑 삭제와 같은 판단) —")

edit(P_MAIN, "msg-cards 에 ended",
     "                  # z1122: 보는 사람이 그 녹음을 시작했나(msg/status z1121 과 같은 값) —",
     "                  # z1131: 사람이 「⏹ 회의 종료」를 눌렀나(모아보기 탭 카드가 먼저 본다)\n"
     "                  \"ended\": _meeting_ended(m),\n"
     "                  \"ended_at\": (m.get(\"ended_at\") or \"\"),\n"
     "                  # z1122: 보는 사람이 그 녹음을 시작했나(msg/status z1121 과 같은 값) —")

# ── ④ 상세 화면에 can_end 넘기기 ─────────────────────────────────
edit(P_MAIN, "상세 화면에 can_end",
     "               can_edit=_can_edit_meeting(u, m), can_delete=_can_delete_meeting(u, m), ai_on=ai_client.ai_available(),",
     "               can_edit=_can_edit_meeting(u, m), can_delete=_can_delete_meeting(u, m), ai_on=ai_client.ai_available(),\n"
     "               can_end=_can_end_meeting(u, m),   # z1131: 「⏹ 회의 종료」 단추를 보일까",
     )

# ── ⑤ 종료/되돌리기 입구 ─────────────────────────────────────────
edit(P_MAIN, "POST /api/meeting/{mid}/end",
     "@app.post(\"/api/meeting/msg/delete\")",
     "@app.post(\"/api/meeting/{mid:int}/end\")\n"
     "async def api_meeting_end(req: Request, mid: int):\n"
     "    \"\"\"z1131 (대표 지시 2026-09-27): 예정 끝 시각보다 일찍 끝났을 때 사람이 회의를 끝낸다.\n"
     "    끝낸 시각을 `meetings.ended_at` 에 적고, 회의 카드(이음·모아보기)가 그 값을 시간 규칙보다 먼저 본다.\n"
     "    `undo=true` 면 되돌린다(실수로 눌렀을 때).\"\"\"\n"
     "    u = get_user(req)\n"
     "    if not u:\n"
     "        return JSONResponse({\"ok\": False, \"error\": \"login\"}, 401)\n"
     "    try:\n"
     "        d = await req.json()\n"
     "    except Exception:\n"
     "        d = {}\n"
     "    undo = bool(isinstance(d, dict) and d.get(\"undo\"))\n"
     "    with db_session() as c:\n"
     "        row = c.execute(\"SELECT * FROM meetings WHERE id=?\", (mid,)).fetchone()\n"
     "        if not row:\n"
     "            return JSONResponse({\"ok\": False, \"error\": \"not_found\"}, 404)\n"
     "        m = dict(row)\n"
     "        if not _can_end_meeting(u, m):\n"
     "            return JSONResponse({\"ok\": False, \"error\": \"not_allowed\"}, 403)\n"
     "        if undo:\n"
     "            c.execute(\"UPDATE meetings SET ended_at='', updated_at=datetime('now','localtime') WHERE id=?\",\n"
     "                      (mid,))\n"
     "            print(f\"[MEETING-END] 회의 {mid} 종료 되돌림 — {u.get('name')}\", flush=True)\n"
     "            return JSONResponse({\"ok\": True, \"ended\": False, \"ended_at\": \"\"})\n"
     "        if _meeting_ended(m):\n"
     "            return JSONResponse({\"ok\": True, \"ended\": True, \"ended_at\": m.get(\"ended_at\") or \"\",\n"
     "                                 \"already\": True})\n"
     "        c.execute(\"UPDATE meetings SET ended_at=datetime('now','localtime'),\"\n"
     "                  \" updated_at=datetime('now','localtime') WHERE id=?\", (mid,))\n"
     "        _r2 = c.execute(\"SELECT ended_at FROM meetings WHERE id=?\", (mid,)).fetchone()\n"
     "        now = (dict(_r2).get(\"ended_at\") if _r2 else \"\") or \"\"\n"
     "        print(f\"[MEETING-END] 회의 {mid} 종료 — {u.get('name')} {now}\", flush=True)\n"
     "    return JSONResponse({\"ok\": True, \"ended\": True, \"ended_at\": now})\n"
     "\n"
     "\n"
     "@app.post(\"/api/meeting/msg/delete\")")
print("\n[완료] z1131 main.py %d곳" % len(done))

# ══════════ 화면 ① meeting_form.html ══════════
# (1) 머리줄 단추 — 이음 회의와 연결된 회의록에서만
edit(P_FORM, "머리줄 「⏹ 회의 종료」 단추",
     '      {% if not is_new and can_delete %}<button class="btn btn-secondary" id="btnDelete" style="color:var(--knk-red);">🗑 삭제</button>{% endif %}\n',
     '      {% if not is_new and can_delete %}<button class="btn btn-secondary" id="btnDelete" style="color:var(--knk-red);">🗑 삭제</button>{% endif %}\n'
     '      {# z1131(대표 지시 2026-09-27): 예정 끝 시각보다 일찍 끝났을 때 — 이음 회의와 연결된 회의록에만 #}\n'
     '      {% if not is_new and meeting.msg_meeting_id and can_end %}'
     '<button class="btn btn-secondary" id="btnEndMeeting"{% if meeting.ended_at %} hidden{% endif %}>⏹ 회의 종료</button>'
     '<button class="btn btn-secondary" id="btnUnendMeeting"{% if not meeting.ended_at %} hidden{% endif %} '
     'style="color:var(--qv-ink-3);">↩ 종료 되돌리기</button>{% endif %}\n'
     '      {% if not is_new and meeting.msg_meeting_id %}<span class="mf-ended" id="mtgEndedTag"'
     '{% if not meeting.ended_at %} hidden{% endif %}>✅ 종료됨{% if meeting.ended_at %} · {{ meeting.ended_at[11:16] }}{% endif %}</span>{% endif %}\n')

# (2) 종료 표시 모양
edit(P_FORM, "종료 표시 CSS",
     "#recOther[hidden] { display:none !important; }",
     "#recOther[hidden] { display:none !important; }\n"
     ".mf-ended { display:inline-flex; align-items:center; font-size:13px; font-weight:800; color:#166534;\n"
     "            background:#ECFDF5; border:1px solid #A7F3D0; border-radius:10px; padding:8px 12px; }\n"
     "/* 🔴 .btn 의 display 가 hidden 속성을 덮는다 — 이겨야 숨는다(.rec-phone 과 같은 함정) */\n"
     ".mf-ended[hidden], #btnEndMeeting[hidden], #btnUnendMeeting[hidden] { display:none !important; }")

# (3) 누를 때 — 녹음 중이면 먼저 마치고 끝낸다
edit(P_FORM, "종료/되돌리기 손질",
     "  var bDel=$('btnDelete'); if(bDel) bDel.addEventListener('click', delMeeting);\n",
     "  var bDel=$('btnDelete'); if(bDel) bDel.addEventListener('click', delMeeting);\n"
     "  // ── z1131(대표 지시 2026-09-27): 「⏹ 회의 종료」 — 예정 끝 시각 전에 끝났을 때 사람이 끝낸다 ──\n"
     "  //   회의 카드(이음·모아보기)는 이 값을 시간 규칙보다 **먼저** 본다 → 누르면 곧 「✅ 회의 종료」.\n"
     "  var _endBtn=$('btnEndMeeting'), _unendBtn=$('btnUnendMeeting');\n"
     "  function endTagShow(on, at){\n"
     "    var t=$('mtgEndedTag');\n"
     "    if(t){ t.hidden=!on; if(on) t.textContent='✅ 종료됨' + (at ? ' · ' + String(at).slice(11,16) : ''); }\n"
     "    if(_endBtn) _endBtn.hidden=on;\n"
     "    if(_unendBtn) _unendBtn.hidden=!on;\n"
     "  }\n"
     "  async function endMeetingCall(undo){\n"
     "    if(!M.id) return null;\n"
     "    var r=await fetch('/api/meeting/'+M.id+'/end',{method:'POST',\n"
     "      headers:{'Content-Type':'application/json'}, body: JSON.stringify({undo: !!undo})});\n"
     "    var j=null; try{ j=await r.json(); }catch(_){ j=null; }\n"
     "    if(!r.ok || !j || !j.ok){ alert((undo?'되돌리지':'종료하지')+' 못했습니다' + ((j&&j.error)?' ('+j.error+')':'')); return null; }\n"
     "    return j;\n"
     "  }\n"
     "  var _NL = String.fromCharCode(10);   // 확인 창 줄바꿈(글자 escape 를 쓰지 않는다)\n"
     "  if(_endBtn) _endBtn.addEventListener('click', async function(){\n"
     "    var recing = !!(_mr && _mr.state!=='inactive');\n"
     "    if(!confirm('이 회의를 종료할까요?' + _NL + _NL + '회의 카드가 「✅ 회의 종료」로 바뀝니다.'\n"
     "       + (recing ? _NL + '(녹음 중입니다 — 녹음도 마치고 정리를 시작합니다)' : ''))) return;\n"
     "    if(recing){ try{ recStop(); }catch(_){} }\n"
     "    _endBtn.disabled=true;\n"
     "    try{\n"
     "      var j=await endMeetingCall(false);\n"
     "      if(j){ endTagShow(true, j.ended_at||''); recSt('⏹ 회의를 종료했습니다 — 회의 카드가 「✅ 회의 종료」로 바뀝니다.'); }\n"
     "    } finally { _endBtn.disabled=false; }\n"
     "  });\n"
     "  if(_unendBtn) _unendBtn.addEventListener('click', async function(){\n"
     "    if(!confirm('회의 종료를 되돌릴까요?' + _NL + _NL + '회의 카드가 다시 예정 시각 규칙을 따릅니다.')) return;\n"
     "    _unendBtn.disabled=true;\n"
     "    try{\n"
     "      var j=await endMeetingCall(true);\n"
     "      if(j){ endTagShow(false, ''); recSt('회의 종료를 되돌렸습니다.'); }\n"
     "    } finally { _unendBtn.disabled=false; }\n"
     "  });\n")

# (4) 공유 안내를 사실대로 — 앱이 깔려 있어야 「공유 → KNK WORKS」가 보인다
edit(P_FORM, "안내 ②를 「올리기」 먼저로", 
     '            ② 끝나면 녹음기에서 <b>「공유 → KNK WORKS」</b> — 회의를 고르면 <b>음성→글자·AI 정리까지 자동</b>입니다.\n',
     '            ② 끝나면 이 화면 <b>「📁 녹음 파일 올리기」</b>로 그 녹음을 고르세요 — <b>음성→글자·AI 정리까지 자동</b>입니다.<br>\n'
     '            <span style="opacity:.85">휴대폰에 <b>WORKS 앱을 깔아 두면</b> 녹음기 <b>「공유 → KNK WORKS」</b>로 바로 보낼 수도 있습니다(크롬 ⋮ → 「앱 설치」).</span>\n',
     2)

edit(P_FORM, "기기별 안내도 올리기 먼저",
     "      el.innerHTML='📱 <b>안드로이드</b> — 회의 녹음은 위 안내대로 <b>홈 화면의 「음성 녹음」</b>으로 하세요. '\n",
     "      el.innerHTML='📱 <b>안드로이드</b> — 회의 녹음은 위 안내대로 <b>홈 화면의 「음성 녹음」</b>으로 하고, '\n"
     "        +'끝나면 <b>「📁 녹음 파일 올리기」</b>로 붙이세요(WORKS 앱을 깔았으면 녹음기 <b>「공유 → KNK WORKS」</b>도 됩니다). '\n")

# ══════════ 화면 ② meetings.html(모아보기) ══════════
edit(P_LIST, "모아보기 카드 — 종료를 맨 먼저",
     "    function headState(m, now){\n"
     "      var mn = m.minutes || {}, st = mn.stage || 'none', s = startMs(m), e = endMs(m);\n",
     "    function headState(m, now){\n"
     "      var mn = m.minutes || {}, st = mn.stage || 'none', s = startMs(m), e = endMs(m);\n"
     "      // z1131: 사람이 「⏹ 회의 종료」를 눌렀으면 시간과 상관없이 끝난 회의(이음 카드도 같은 규칙으로 요청)\n"
     "      if (mn.ended === true) return 'end';\n")

print("\n[완료] z1131 — 모두 %d곳" % len(done))
