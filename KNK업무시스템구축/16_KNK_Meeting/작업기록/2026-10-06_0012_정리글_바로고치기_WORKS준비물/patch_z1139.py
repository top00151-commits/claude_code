# -*- coding: utf-8 -*-
"""z1139 — 「📋 회의록 정리」 글을 사람이 **바로 고친다** (대표 지시 2026-10-05)

발단(대표): 「회의록 정리시 음성 인식이 잘못되어서 잘못 작성한 부분은 어떻게 수정을 해야하지?」
그때까지: 정리 글은 **읽기 전용**이었고, 서버도 그 글을 **AI 정리로만** 썼다. 낱말 하나를 고치려 해도
  ① 원문을 고치고 ② 저장하고 ③ 「🔧 다시 하기」를 펼쳐 「🔄 다시 정리」로 **AI 를 통째로 다시** 돌려야 했고,
  그러면 **다른 문장 표현까지 바뀌었다**.
대표 결정: 「정리 글을 바로 고치기」.

바꾸는 것
  [app/main.py] 1곳
    · 새 입구 `POST /api/meeting/{mid}/summary` — 고친 글을 그대로 저장(AI 안 부름) ·
      권한은 `_can_edit_meeting`(참석자 포함) · 먼저 저장 충돌 검사(base_ts) · 활동기록에 누가 고쳤는지 남김
  [app/templates/meeting_form.html] 5곳
    · CSS — 고치기 칸 · 🔴 `[hidden]` 을 이기는 규칙(display 가 hidden 을 덮는다)
    · 정리 칸 머리에 「✏ 고치기」 단추(고칠 수 있는 사람에게만)
    · 정리 칸 아래 고치기 상자(글칸 + 💾 정리 저장 + 취소 + 알림 줄)
    · JS — 열기/닫기·저장·충돌 안내
    · JS — 손으로 고친 뒤 「🔄 다시 정리」를 누르면 **한 번 묻는다**(고친 글이 사라지므로)

사용: python patch_z1139.py <main.py 경로> <meeting_form.html 경로>
"""
import io
import os
import sys

# ───────────────────────── 서버 ─────────────────────────
ENDPOINT = '''@app.post("/api/meeting/{mid:int}/summary")
async def api_meeting_summary_save(req: Request, mid: int):
    """z1139 (대표 지시 2026-10-05): 「📋 회의록 정리」 글을 **사람이 바로 고친다**.
    음성→글자가 낱말을 잘못 들었을 때, 전에는 원문을 고쳐 「🔄 다시 정리」로 AI 를 통째로 다시 돌려야 했고
    그러면 다른 문장 표현까지 바뀌었다. 여기서는 **고친 글을 그대로 저장**한다(AI 를 부르지 않는다).
    body: {summary: 고친 글, base_ts: 내가 보던 시각}
    권한은 회의록 고치기와 같다(작성자·이음 등록 담당·관리자/대표·그 회의 참석자 — z1133)."""
    u = get_user(req)
    if not u:
        return JSONResponse({"error": "로그인 필요"}, 401)
    try:
        d = await req.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "본문을 읽지 못했습니다."}, 400)
    if not isinstance(d, dict) or d.get("summary") is None:
        return JSONResponse({"ok": False, "error": "고친 정리 글이 없습니다."}, 400)
    summary = str(d.get("summary")).replace("\\r\\n", "\\n").strip()[:20000]
    with db_session() as c:
        m = c.execute("SELECT * FROM meetings WHERE id=?", (mid,)).fetchone()
        if not m:
            return JSONResponse({"ok": False, "error": "없는 회의록입니다."}, 404)
        m = dict(m)
        if not _can_edit_meeting(u, m, c):
            return JSONResponse({"ok": False, "error": "수정 권한이 없습니다."}, 403)
        _conf, _cur = _edit_conflict(c, "meetings", mid, d.get("base_ts"))
        if _conf:
            return _conflict_resp(_cur)
        if summary == (m.get("summary") or "").strip():
            return JSONResponse({"ok": True, "updated_at": _row_ts(c, "meetings", mid), "changed": False})
        c.execute("UPDATE meetings SET summary=?, updated_at=datetime('now','localtime') WHERE id=?",
                  (summary, mid))
        try:    # 누가 고쳤는지 남긴다(AI 정리와 사람이 고친 것을 나중에 가릴 수 있게)
            log_activity(c, u["id"], "meeting_summary_edit",
                         f"{u['name']} 회의록 정리 고침: {(m.get('title') or '')[:60]}",
                         team_id=u.get("team_id"))
        except Exception:
            pass
        new_ts = _row_ts(c, "meetings", mid)
    return JSONResponse({"ok": True, "updated_at": new_ts, "changed": True})


'''

# ───────────────────────── 화면 ─────────────────────────
CSS = """/* ── ✏ 정리 글 바로 고치기 — z1139 대표 지시 2026-10-05 ──
   음성 인식이 잘못 들은 낱말을 그 자리에서 고친다(AI 를 다시 돌리지 않는다). */
#sumEdit { width:100%; box-sizing:border-box; min-height:240px; padding:12px 13px; font-size:14px;
  line-height:1.75; border:1px solid var(--qv-line-3); border-radius:10px; background: var(--qv-surface);
  color: var(--qv-ink); font-family:inherit; white-space:pre-wrap; resize:vertical; }
#sumEdit:focus { outline:2px solid rgba(160,30,30,.35); outline-offset:1px; }
#btnSumEdit { color: var(--knk-red); border-color: var(--knk-red); font-weight:800; }
/* 🔴 .sum-box / div 의 display 가 hidden 속성을 덮는다 — 이겨야 서로 바꿔 보인다 */
#sumEditWrap[hidden], #mtgSummary[hidden] { display:none !important; }
/* 좁은 휴대폰에서는 단추가 둘이라 제목이 어중간하게 끊긴다 → 단추를 아랫줄 오른쪽으로 */
@media (max-width: 430px) {
  #secSummary .mf-sec-head { flex-wrap:wrap; row-gap:8px; }
  #secSummary .mf-sec-title { flex:1 1 100%; }
}
"""

HEADBTN = ('        {# z1139(대표 지시 2026-10-05): 음성 인식이 잘못 들은 낱말을 여기서 바로 고친다 #}\n'
           '        {% if can_edit %}<button class="copy-btn" id="btnSumEdit" type="button" style="margin-left:auto;"'
           ' title="음성 인식이 잘못 들은 낱말을 여기서 바로 고칩니다(AI 를 다시 돌리지 않습니다)">✏ 고치기</button>{% endif %}\n')

EDITBOX = '''      {% if can_edit %}
      {# z1139: 고치기 상자 — 「✏ 고치기」를 누르면 위 정리 글 대신 이 칸이 보인다 #}
      <div id="sumEditWrap" hidden style="margin-top:4px;">
        <textarea id="sumEdit" spellcheck="false" placeholder="정리 글을 고치세요. 잘못 들린 낱말만 바꾸시면 됩니다."></textarea>
        <div class="mf-hint" style="margin-top:8px;line-height:1.7;">잘못 들린 낱말만 고쳐 저장하세요 —
          <b>AI 를 다시 돌리지 않으므로 다른 문장은 그대로</b> 있습니다.
          (회의 원문까지 바로잡고 싶으시면 아래 「회의 내용」을 고친 뒤 「🔧 다시 하기 · 녹음 추가」의 「🔄 다시 정리」를 쓰세요.)</div>
        <div style="display:flex;gap:8px;margin-top:10px;flex-wrap:wrap;align-items:center;">
          <button class="btn btn-primary" id="btnSumSave" type="button">💾 정리 저장</button>
          <button class="btn btn-secondary" id="btnSumCancel" type="button">취소</button>
          <span class="rec-status" id="sumSt"></span>
        </div>
      </div>
      {% endif %}
'''

JS = '''  // ── z1139 ✏ 정리 글 바로 고치기 (대표 지시 2026-10-05) ───────────────────────
  //   음성 인식이 잘못 들은 낱말을 그 자리에서 고친다. AI 를 다시 돌리지 않으므로 다른 문장은 그대로.
  var _sumEdited = false;   // 이 화면에서 손으로 고쳤나 → 「🔄 다시 정리」 때 한 번 묻는다
  function sumSt(msg, kind){
    var el=$('sumSt'); if(!el) return;
    el.textContent = msg || '';
    el.style.color = kind==='err' ? 'var(--knk-red)' : (kind==='ok' ? '#15803d' : 'var(--qv-ink-3)');
  }
  function sumEditShow(on){
    var w=$('sumEditWrap'), box=$('mtgSummary'), b=$('btnSumEdit');
    if(!w||!box) return;
    if(on){ var t=$('sumEdit'); if(t) t.value = M.summary || ''; }
    w.hidden = !on; box.hidden = !!on;
    if(b) b.textContent = on ? '✖ 그만두기' : '✏ 고치기';
    if(on){ var t2=$('sumEdit'); if(t2){ try{ t2.focus(); }catch(_){} } }
  }
  var _bSumE=$('btnSumEdit');
  if(_bSumE) _bSumE.addEventListener('click', function(){
    var w=$('sumEditWrap'); if(!w) return;
    sumEditShow(!!w.hidden); sumSt('');
  });
  var _bSumC=$('btnSumCancel');
  if(_bSumC) _bSumC.addEventListener('click', function(){ sumEditShow(false); sumSt(''); });
  var _bSumS=$('btnSumSave');
  if(_bSumS) _bSumS.addEventListener('click', async function(){
    var t=$('sumEdit'); if(!t) return;
    _bSumS.disabled=true; sumSt('저장 중…');
    var r = await jreq('POST', '/api/meeting/' + M.id + '/summary', { summary: t.value, base_ts: M.base_ts });
    _bSumS.disabled=false;
    if(r.ok && r.data && r.data.ok){
      M.summary = (t.value||'').replace(/\\r\\n/g, String.fromCharCode(10)).trim();
      M.base_ts = r.data.updated_at || M.base_ts;
      _sumEdited = true;
      renderSummary(); sumEditShow(false); sumSt('');
      status('정리를 고쳤습니다 ✓', 'ok');
    } else if (r.status === 409){
      sumSt((r.data && r.data.message) || '다른 곳에서 먼저 저장됐습니다. 새로고침하세요.', 'err');
    } else {
      sumSt((r.data && r.data.error) || '저장 실패', 'err');
    }
  });

'''

EXTRACT_OLD = """  async function extract(){
    var btn = $('btnExtract'); if (btn){ btn.disabled=true; }"""
EXTRACT_NEW = """  async function extract(){
    // z1139: 손으로 고친 정리 글은 AI 가 다시 쓰면 사라진다 → 그때만 한 번 묻는다
    if (_sumEdited && !confirm('「🔄 다시 정리」를 하면 AI 가 정리 글을 새로 만듭니다.'
        + String.fromCharCode(10) + '손으로 고치신 정리 글은 사라집니다. 계속할까요?')) return;
    var btn = $('btnExtract'); if (btn){ btn.disabled=true; }"""


def put(path, text):
    data = text.encode("utf-8")        # 🔴 쓰기 전에 인코딩을 먼저 해 본다
    with open(path + ".tmp_z1139", "wb") as f:
        f.write(data)
    os.replace(path + ".tmp_z1139", path)


def main():
    if len(sys.argv) < 3:
        print("사용: python patch_z1139.py <main.py> <meeting_form.html>")
        return 2
    mp, tp = sys.argv[1], sys.argv[2]
    for p in (mp, tp):
        if not os.path.exists(p):
            print("없는 파일:", p)
            return 2

    # ── 서버 ──
    src = io.open(mp, encoding="utf-8").read()
    if "api_meeting_summary_save" in src:
        print("main.py 는 이미 z1139 가 들어 있음 — 건너뜀")
    else:
        a = '@app.delete("/api/meeting/{mid:int}")'
        if src.count(a) != 1:
            print("자리 못 찾음(%d): 서버 새 입구" % src.count(a))
            return 3
        src = src.replace(a, ENDPOINT + a, 1)
        put(mp, src)
        import py_compile
        py_compile.compile(mp, doraise=True)
        print("적용: 서버 새 입구 POST /api/meeting/{mid}/summary · 문법 통과")

    # ── 화면 ──
    t = io.open(tp, encoding="utf-8").read()
    if "sumEditWrap" in t:
        print("양식은 이미 z1139 가 들어 있음 — 건너뜀")
        return 0

    steps = [
        ("① CSS", "#recUpTop[hidden] { display:none !important; }\n", CSS, "after"),
        ("② 「✏ 고치기」 단추",
         '        <button class="copy-btn" id="btnCopySum" type="button" style="margin-left:auto;"', HEADBTN, "before"),
        ("④ JS 고치기·저장",
         "  var bExt=$('btnExtract'); if(bExt && !bExt.disabled) bExt.addEventListener('click', extract);\n",
         JS, "after"),
    ]
    for label, anchor, block, how in steps:
        if t.count(anchor) != 1:
            print("자리 못 찾음(%d): %s" % (t.count(anchor), label))
            return 3
        t = t.replace(anchor, (block + anchor) if how == "before" else (anchor + block), 1)
        print("적용:", label)

    # ③ 고치기 상자 — 정리 글 <div> 줄 바로 뒤
    i = t.index('      <div class="sum-box empty" id="mtgSummary">')
    j = t.index("\n", i) + 1
    t = t[:j] + EDITBOX + t[j:]
    print("적용: ③ 고치기 상자")

    # ⑤ 「🔄 다시 정리」 되묻기
    if t.count(EXTRACT_OLD) != 1:
        print("자리 못 찾음(%d): ⑤ 다시 정리 되묻기" % t.count(EXTRACT_OLD))
        return 3
    t = t.replace(EXTRACT_OLD, EXTRACT_NEW, 1)
    print("적용: ⑤ 손으로 고친 뒤 「🔄 다시 정리」는 한 번 묻는다")

    # 복사 단추는 이제 두 번째 — 오른쪽 끝 붙임을 고치기 단추에 넘긴다
    t = t.replace('<button class="copy-btn" id="btnCopySum" type="button" style="margin-left:auto;"',
                  '<button class="copy-btn" id="btnCopySum" type="button" style="margin-left:8px;"', 1)
    print("적용: 복사 단추 자리 정리(오른쪽 끝은 고치기 단추가 맡는다)")

    put(tp, t)
    print("저장:", tp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
