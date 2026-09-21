# -*- coding: utf-8 -*-
"""z1119 — WORKS 「🗓 회의 카드 모아보기」 탭: 끝났는데 「🔴 지금 회의 중」 (세션 10 전달 · 이음 v815 와 같은 규칙)

대표 신고(09-21): 이음 회의 카드가 끝났는데 「회의 중」 → 이음은 v815 로 고침(17:43).
세션 10 확인: WORKS 모아보기 탭(z1108)도 **같은 판정을 복사해 쓰고 있다**.
  · headState — WORKS 단계가 started 면 끝나고 12시간 「회의 중」(뜻은 '녹음 중일 때만')
  · minutesHtml — started 면 시간과 상관없이 「🔴 회의 진행 중 · 이름 녹음」
  · 탭이 받는 /api/meetings/msg-cards 에 recording 칸이 없어 녹음 중과 「시작만 누름」을 가를 수 없다
WORKS 의 started 는 두 경우를 다 담는다(_meeting_msg_stage): ①녹음 중 ②「▶ 회의 시작」만 누르고 녹음 없음.

고침(이음 v815 와 같은 규칙):
  ① msg-cards 의 minutes 에 recording·rec_secs (이음이 쓰는 msg/status 와 같은 값)
  ② 윗줄 — 녹음이 없으면(recording === false) 끝 시각에 종료 · 끝 뒤 12시간 「회의 중」은 녹음 중일 때만
     · 시작 전·회의 시간 안에 누른 회의는 그대로 「회의 중」 · recording 칸이 없으면(옛 응답) 예전 그대로
  ③ 아래 줄 — 녹음 중 「🔴 녹음 중 · 이름 · N분 저장됨」 / 녹음 없음·끝 전 「🔴 회의 진행 중 · 이름 · 녹음 안 됨」
     / 녹음 없음·끝 뒤 「⏹ 회의 끝남 · 이름 · 녹음 없음」(대표 결정 문구 · 이음 v815 와 같음)
     · 아래 줄은 윗줄 판정(hs)을 따라가 30초 다시 그리기 때 두 줄이 함께 바뀐다

사용: py patch_cards.py <원본 폴더> <결과 폴더>
"""
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


def sub1(s, old, new, tag):
    n = s.count(old)
    assert n == 1, "%s: 앵커 %d개(1개여야 함)" % (tag, n)
    return s.replace(old, new)


# ══════════════════════════════════════════════════════════════════════
# 1. main.py — /api/meetings/msg-cards 에 recording·rec_secs
# ══════════════════════════════════════════════════════════════════════
m0 = load("main.py")
m = sub1(
    m0,
    '            can_view = _can_view_meeting(c, u, m)\n'
    '            mn = {"stage": _meeting_msg_stage(m), "can_view": can_view,\n'
    '                  "started_by": _msg_owner_disp(c, m.get("owner_id"))}\n',
    '            can_view = _can_view_meeting(c, u, m)\n'
    '            _rv = _rec_view(m)   # z1119: 녹음 중인가(이음 msg/status 와 같은 값) — 탭이 「녹음 중」과 「시작만 누름」을 가른다\n'
    '            mn = {"stage": _meeting_msg_stage(m), "can_view": can_view,\n'
    '                  "started_by": _msg_owner_disp(c, m.get("owner_id")),\n'
    '                  "recording": _rv["state"] == "recording",\n'
    '                  "rec_secs": _rv["secs"] if _rv["state"] == "recording" else 0}\n',
    "msg-cards recording",
)
save("main.py", m)

# ══════════════════════════════════════════════════════════════════════
# 2. meetings.html — 윗줄·아래 줄
# ══════════════════════════════════════════════════════════════════════
h0 = load("meetings.html")
h = h0

# ── ② 윗줄
h = sub1(
    h,
    "    // 카드 윗줄 상태 — 이음 회의 카드(v795)와 같은 판단: 녹음이 끝났으면 종료 · 녹음 중이면 회의 중(끝나고 12시간까지)\n"
    "    function headState(m, now){\n"
    "      var st = (m.minutes && m.minutes.stage) || 'none', s = startMs(m), e = endMs(m);\n"
    "      if (st === 'recorded' || st === 'processing' || st === 'done' || st === 'failed') return 'end';\n"
    "      if (st === 'started' && !(e && now >= e + STUCK)) return 'live';\n",
    "    // 카드 윗줄 상태 — 이음 회의 카드(v795·v815)와 같은 판단: 녹음이 끝났으면 종료 · 녹음 중이면 회의 중(끝나고 12시간까지)\n"
    "    //   z1119: WORKS 단계 started 는 「녹음 중」과 「▶ 회의 시작만 누르고 녹음 없음」을 둘 다 담는다(09-21 대표 신고 · 세션 10 전달).\n"
    "    //   녹음이 없으면(recording === false) 끝 시각에 종료 — 끝 뒤 12시간 「회의 중」은 녹음 중일 때만.\n"
    "    //   시작 전·회의 시간 안에 누른 회의는 그대로 「회의 중」 · recording 칸이 없으면(옛 응답) 예전 그대로.\n"
    "    function headState(m, now){\n"
    "      var mn = m.minutes || {}, st = mn.stage || 'none', s = startMs(m), e = endMs(m);\n"
    "      if (st === 'recorded' || st === 'processing' || st === 'done' || st === 'failed') return 'end';\n"
    "      var grace = (mn.recording === false) ? 0 : STUCK;\n"
    "      if (st === 'started' && !(e && now >= e + grace)) return 'live';\n",
    "윗줄",
)

# ── ③ 아래 줄
h = sub1(
    h,
    "      if (st === 'started') out += '<span class=\"mc-state\">🔴 회의 진행 중 · ' + esc(mn.started_by || '') + ' 녹음</span>';\n",
    "      if (st === 'started') {\n"
    "        // z1119: 실제 녹음 여부(recording · 서버 저장 초 rec_secs)로 — 이음 회의 카드(v807·v815)와 같은 글\n"
    "        //   아래 줄은 윗줄 판정(hs)을 따라간다 → 30초 다시 그리기 때 두 줄이 함께 바뀐다\n"
    "        var who = esc(mn.started_by || ''), mins = Math.floor((+mn.rec_secs || 0) / 60);\n"
    "        if (mn.recording === true) out += '<span class=\"mc-state\">🔴 녹음 중 · ' + who + (mins >= 1 ? ' · ' + mins + '분 저장됨' : '') + '</span>';\n"
    "        else if (mn.recording === false) out += (hs === 'end')\n"
    "          ? '<span class=\"mc-state dim\">⏹ 회의 끝남 · ' + who + ' · 녹음 없음</span>'\n"
    "          : '<span class=\"mc-state\">🔴 회의 진행 중 · ' + who + ' · 녹음 안 됨</span>';\n"
    "        else out += '<span class=\"mc-state\">🔴 회의 진행 중 · ' + who + ' 녹음</span>';   // 칸이 없는 옛 응답 — 예전 글\n"
    "      }\n",
    "아래 줄",
)
save("meetings.html", h)

print("[OK] main.py %d → %d 글자" % (len(m0), len(m)))
print("[OK] meetings.html %d → %d 글자" % (len(h0), len(h)))
for k, got, want in [("main recording", m.count('"recording": _rv["state"] == "recording"'), 2),   # msg/status + msg-cards
                     ("html grace", h.count("var grace = (mn.recording === false) ? 0 : STUCK;"), 1),
                     ("html 회의 끝남", h.count("⏹ 회의 끝남 · "), 1),
                     ("html 녹음 없음", h.count(" · 녹음 없음"), 1),
                     ("html 녹음 안 됨", h.count(" · 녹음 안 됨"), 1)]:
    print("   %-16s %d  %s" % (k, got, "OK" if got == want else "⚠ %d 예상" % want))
    assert got == want, k
