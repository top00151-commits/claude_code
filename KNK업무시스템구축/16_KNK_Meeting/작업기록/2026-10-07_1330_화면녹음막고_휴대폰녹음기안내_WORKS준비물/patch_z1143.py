# -*- coding: utf-8 -*-
"""z1143 — 이 화면에서 직접 녹음하는 길을 막고 「휴대폰 녹음기를 쓰세요」로 안내 (대표 지시 2026-10-07)

대표 결정(2026-10-07):
  · 막는 범위 = ① 새 회의록 「🎙 녹음하며 회의」 ② 회의록 상세 「🎙 녹음 추가」
    🔴 ③ 이음 「▶ 회의 시작」 자동 녹음은 **그대로 둔다**
    🔴 ④ 「🎙 이어서 녹음」(돌던 녹음 이어받기)도 그대로 — 막으면 녹음 중인 사람이 못 건진다
  · PC 도 함께 막는다(기기 구분 없음)
  · 스위치는 두지 않는다(코드로 막는다)

왜:
  이 화면 녹음은 화면을 켜 둘 때만 소리가 들어오고(아이폰은 다른 앱으로 가면 끊김),
  2026-10-07 대회의실 진단에서 멀리 담긴 소리는 받아쓰기가 무너졌다(일치율 73% ↔ 95%).

🔴 기준점에 역슬래시를 쓰지 않는다(셸을 거치면 뭉개진다) — 넣을 코드의 역슬래시는 chr(92)로 만든다.
"""
import io
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
F = "meeting_form.html"


def load():
    return io.open(os.path.join(OUT, F), encoding="utf-8").read()


def save(t):
    p = os.path.join(OUT, F)
    data = t.encode("utf-8")
    with open(p + ".tmp", "wb") as f:
        f.write(data)
    os.replace(p + ".tmp", p)


def sub(t, old, new, label):
    n = t.count(old)
    assert n == 1, "%s: %d건 (1건이어야 함)" % (label, n)
    return t.replace(old, new)


s = load()
assert "recBlockNote" not in s, "이미 패치됨"

# ── ① 단추 보조글 — 「누르면 바로 녹음」은 이제 사실이 아니다 ──────────────
s = sub(s,
        '<button class="start-big rec-btn" id="recBtn">🎙 녹음하며 회의&nbsp;'
        '<span class="start-sub">누르면 바로 녹음</span></button>',
        '<button class="start-big rec-btn" id="recBtn">🎙 녹음하며 회의&nbsp;'
        '<span class="start-sub">휴대폰 녹음기로 녹음해 주세요</span></button>',
        "단추 보조글")

# ── ② 새 회의록 안내문 — 이 화면 녹음 설명을 휴대폰 녹음기 안내로 ───────────
s = sub(s,
        '<div class="mf-hint" style="margin-top:10px;line-height:1.6;">※ 녹음을 마치면 '
        '<b>음성→글자, AI 정리까지 자동</b>으로 됩니다. <b>전화를 받을 땐 「⏸ 일시정지」</b>'
        '(통화 내용 녹음 방지) → 통화 후 「▶ 재개」. 이 화면 녹음은 <b>10초마다 서버에 저장</b>돼 '
        '창이 닫혀도 그때까지는 남고, <b>회의록 목록에서 「녹음 끝내고 정리」</b>로 마칠 수 있습니다.</div>',
        '<div class="mf-hint" style="margin-top:10px;line-height:1.6;">※ <b>회의 녹음은 휴대폰 기본 녹음기</b>'
        '(안드로이드 「음성 녹음」 · 아이폰 「음성 메모」)로 하세요 — 다른 앱을 보거나 화면이 꺼져도 '
        '<b>안 끊깁니다</b>. 끝나면 <b>「📁 녹음 파일 올리기」</b>로 그 파일을 고르면 '
        '<b>음성→글자, AI 정리까지 자동</b>입니다. 소리는 <b>말하는 사람 가까이</b>에서 담을수록 정확합니다.</div>',
        "새 회의록 안내문")

# ── ③ 사람이 누르는 길만 막는다 ────────────────────────────────────────────
OLD_CLICK = """  var _recBtn=$('recBtn');if(_recBtn)_recBtn.addEventListener('click',function(){
    if(_recBtn.dataset.on){ recStop(); return; }
    _phrecChosen=false; _recHandoff=false;"""
NEW_CLICK = """  // 🔴 z1143 (대표 지시 2026-10-07): 이 화면에서 **사람이 직접** 시작하는 녹음을 막는다.
  //   왜 — 이 화면 녹음은 화면을 켜 둘 때만 소리가 들어오고(아이폰은 다른 앱으로 가면 끊김),
  //   2026-10-07 대회의실 실측에서 멀리 담긴 소리는 받아쓰기가 무너졌다(일치율 73% ↔ 95%).
  //   🔴 막는 것은 ① 새 회의록 「🎙 녹음하며 회의」 ② 상세 「🎙 녹음 추가」 **둘뿐**이다.
  //     이음 「▶ 회의 시작」 자동 녹음(dataset.autorec)·「🎙 이어서 녹음」(recResumeBtn 은 recStart 를
  //     직접 부른다)·녹음 중 「⏹ 종료」는 **그대로 둔다**(대표 결정).
  //   🔴 「먹통」으로 보이지 않게 — 누르면 반드시 **까닭과 갈 길**을 보여 준다.
  function recBlockNote(){
    var b=$('recBtn'); if(!b) return null;
    var n=$('recBlockNote');
    if(!n){
      n=document.createElement('div'); n.id='recBlockNote'; n.className='plat-note';
      try{ b.parentNode.insertBefore(n, b.nextSibling); }catch(_){ return null; }
    }
    n.innerHTML='🎙 <b>이 화면 녹음은 지금 쓰지 않습니다.</b><br>'
      +'회의 녹음은 <b>휴대폰 기본 녹음기</b>(안드로이드 「음성 녹음」 · 아이폰 「음성 메모」)로 하세요 — '
      +'다른 앱을 보거나 화면이 꺼져도 <b>안 끊깁니다</b>.<br>'
      +'끝나면 이 화면 <b>「📁 녹음 파일 올리기」</b>로 그 파일을 고르면 '
      +'<b>음성→글자·AI 정리까지 자동</b>입니다. 소리는 <b>말하는 사람 가까이</b>에서 담을수록 정확합니다.';
    n.hidden=false;
    return n;
  }
  var _recBtn=$('recBtn');if(_recBtn)_recBtn.addEventListener('click',function(){
    if(_recBtn.dataset.on){ recStop(); return; }
    if(!_recBtn.dataset.autorec){                      // z1143 — 사람이 직접 시작하는 길은 막는다
      var _n=recBlockNote();
      try{ (_n||_recBtn).scrollIntoView({block:'center'}); }catch(_){}
      return;
    }
    _phrecChosen=false; _recHandoff=false;"""
s = sub(s, OLD_CLICK, NEW_CLICK, "사람이 누르는 길 막기")

# ── ④ 이음 「▶ 회의 시작」으로 열린 창은 표시를 남겨 그대로 통과시킨다 ──────
s = sub(s,
        """        if(!_phFirst) phrecLeadShow('running');
        var _rb=$('recBtn');""",
        """        if(!_phFirst) phrecLeadShow('running');
        var _rb=$('recBtn');
        // 🔴 z1143: 이음 「▶ 회의 시작」으로 열린 창임을 단추에 남긴다 — 이 길의 녹음은 막지 않는다
        //   (주소의 ?autorec=1 은 바로 위에서 지워지므로 나중에 다시 읽을 수 없다)
        if(_rb) _rb.dataset.autorec='1';""",
        "이음 자동 녹음 표시")

save(s)
print("meeting_form.html 고침 — %d바이트" % os.path.getsize(os.path.join(OUT, F)))
