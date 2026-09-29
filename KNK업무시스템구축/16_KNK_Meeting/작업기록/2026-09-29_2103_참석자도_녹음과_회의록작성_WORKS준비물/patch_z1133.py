# -*- coding: utf-8 -*-
"""z1133 — 회의 참석자도 녹음·녹음파일 올리기·회의록 작성·회의 종료를 할 수 있게 (대표 지시 2026-09-28)
사용: py -3.13 patch_z1133.py <앱 사본 경로>

대표 지시: 「회의록 녹음 및 녹음파일 올리는거 회의록 정리하는거 지금은 회의 만든 작성자만 허용이 되는 것 같은데…
          이 부분을 회의 참석자 누구나 녹음파일 등록 및 회의록 작성할 수 있게 해줘.」
대표 결정(범위): **「⏹ 회의 종료」까지** 열고, **🗑 삭제는 그대로**(작성자·관리자/대표).

지금까지: 손댈 수 있는 사람 = 작성자 · 이음 등록 담당 · 관리자/대표 (참석자는 **보기만**).
바꾼 뒤: + **그 회의의 참석자**(계정이 연결된 참석자 줄) — 이음 「▶ 회의 시작」이 사번으로 정확히 연결해 준다.
  → 녹음(시작·이어서·끝내기) · 📁 올리기 · 공유로 붙이기 · 음성→글자 · 🔄 다시 정리 · 본문/제목 저장 ·
    결정사항·할 일 추가/삭제 · 프로젝트/기회 연결 · ⏹ 회의 종료 가 한꺼번에 열린다.

🔴 권한 함수가 DB 를 봐야 하므로 `c`(열린 커서)를 받게 했다. 안 넘겨도 **짧게 새로 열어** 본다
   (안 넘겼다고 조용히 권한이 사라지면 안 된다 — WAL 이라 읽기는 서로 막지 않는다).
"""
import os
import sys

if len(sys.argv) < 2:
    print("사용: patch_z1133.py <앱 사본 경로>")
    raise SystemExit(2)
APP = sys.argv[1]
P = os.path.join(APP, "app", "main.py")
src = open(P, encoding="utf-8").read()
orig = src
done = []


def sub(name, old, new, count=1):
    global src
    n = src.count(old)
    if n != count:
        print("  [실패] %s — 찾은 수 %d (바라던 수 %d)" % (name, n, count))
        raise SystemExit(1)
    src = src.replace(old, new)
    done.append("%s(%d곳)" % (name, count))
    print("  [고침] %s (%d곳)" % (name, count))


# ── ① 참석자인가 + 고치기 권한 ────────────────────────────────
sub("참석자 판정 + 고치기 권한에 참석자 추가",
    'def _can_edit_meeting(u, m) -> bool:\n'
    '    """회의록 수정 권한: 작성자 본인 · 회의 알림 등록 담당(msg_organizer_id) · admin/ceo.\n'
    '    2026-09-15 대표 결정: 녹음을 직접 하지 않은 등록 담당도 회의록을 고칠 수 있어야 한다.\n'
    '    ⚠ 삭제는 _can_delete_meeting(작성자·admin/ceo 만) — \'고치기\'까지가 지시 범위."""\n'
    '    if not u or not m:\n'
    '        return False\n'
    '    if (u.get("role") or "").lower() in ("admin", "ceo"):\n'
    '        return True\n'
    '    uid = u.get("id")\n'
    '    if not uid:\n'
    '        return False\n'
    '    return m.get("owner_id") == uid or (bool(m.get("msg_organizer_id")) and m.get("msg_organizer_id") == uid)\n',

    'def _meeting_is_attendee(c, u, m) -> bool:\n'
    '    """z1133: 이 사람이 그 회의의 **참석자**인가(계정이 연결된 참석자 줄).\n'
    '    이음 「▶ 회의 시작」이 참석자를 **사번으로** 연결해 `meeting_attendees.user_id` 에 넣어 준다\n'
    '    (이름 맞추기가 아니다 — 사람 참조는 ID). 계정 없는 외부 참석자는 이름만 남아 해당 없음."""\n'
    '    uid = (u or {}).get("id")\n'
    '    mid = (m or {}).get("id")\n'
    '    if not uid or not mid or c is None:\n'
    '        return False\n'
    '    try:\n'
    '        return bool(c.execute("SELECT 1 FROM meeting_attendees WHERE meeting_id=? AND user_id=?",\n'
    '                              (mid, uid)).fetchone())\n'
    '    except Exception:\n'
    '        return False\n'
    '\n'
    '\n'
    'def _can_edit_meeting(u, m, c=None) -> bool:\n'
    '    """회의록 수정 권한: 작성자 본인 · 회의 알림 등록 담당(msg_organizer_id) · admin/ceo · **그 회의 참석자**.\n'
    '    2026-09-15 대표 결정: 녹음을 직접 하지 않은 등록 담당도 회의록을 고칠 수 있어야 한다.\n'
    '    2026-09-28 대표 지시: **참석자 누구나** 녹음·녹음파일 올리기·회의록 작성을 할 수 있어야 한다(z1133).\n'
    '    ⚠ 삭제는 _can_delete_meeting(작성자·admin/ceo 만) — 대표 결정으로 삭제는 넓히지 않는다.\n'
    '    🔴 c(열린 커서)를 넘기면 그걸로 참석자를 본다. 안 넘기면 짧게 새로 열어 본다\n'
    '       (안 넘겼다고 조용히 권한이 사라지면 안 된다 · WAL 이라 읽기는 서로 막지 않는다)."""\n'
    '    if not u or not m:\n'
    '        return False\n'
    '    if (u.get("role") or "").lower() in ("admin", "ceo"):\n'
    '        return True\n'
    '    uid = u.get("id")\n'
    '    if not uid:\n'
    '        return False\n'
    '    if m.get("owner_id") == uid or (bool(m.get("msg_organizer_id")) and m.get("msg_organizer_id") == uid):\n'
    '        return True\n'
    '    if c is not None:\n'
    '        return _meeting_is_attendee(c, u, m)\n'
    '    try:\n'
    '        with db_session() as _c:\n'
    '            return _meeting_is_attendee(_c, u, m)\n'
    '    except Exception:\n'
    '        return False\n')

# ── ② 회의 종료 권한에도 참석자 ──────────────────────────────
sub("회의 종료 권한에 참석자 추가",
    'def _can_end_meeting(u, m) -> bool:\n'
    '    """z1131 「⏹ 회의 종료」 권한: 회의록 작성자(총괄)·관리자/대표 + **이음에 그 회의를 등록한 사람**.\n'
    '    (삭제 권한 + 등록 담당 — 등록 담당은 회의를 열고 닫는 사람이라 종료는 할 수 있게 한다)"""\n'
    '    if not u or not m:\n'
    '        return False\n'
    '    if _can_delete_meeting(u, m):\n'
    '        return True\n'
    '    return bool(u.get("id")) and m.get("msg_organizer_id") == u.get("id")\n',

    'def _can_end_meeting(u, m, c=None) -> bool:\n'
    '    """z1131 「⏹ 회의 종료」 권한: 회의록 작성자(총괄)·관리자/대표 + 이음에 그 회의를 등록한 사람\n'
    '    + z1133(대표 결정 2026-09-28) **그 회의 참석자**(회의를 함께 한 사람이 끝낼 수 있게).\n'
    '    ⚠ 🗑 삭제는 넓히지 않는다(_can_delete_meeting 그대로)."""\n'
    '    if not u or not m:\n'
    '        return False\n'
    '    if _can_delete_meeting(u, m):\n'
    '        return True\n'
    '    if bool(u.get("id")) and m.get("msg_organizer_id") == u.get("id"):\n'
    '        return True\n'
    '    return _can_edit_meeting(u, m, c)   # z1133: 참석자면 종료도 할 수 있다\n')

# ── ③ 부르는 곳에 열린 커서 넘기기(쓸데없이 다시 열지 않게) ──
sub("고치기 권한에 커서 넘기기 ①", "if not _can_edit_meeting(u, m):",
    "if not _can_edit_meeting(u, m, c):", 5)
sub("고치기 권한에 커서 넘기기 ②", "if not m or not _can_edit_meeting(u, dict(m)):",
    "if not m or not _can_edit_meeting(u, dict(m), c):", 4)
sub("고치기 권한에 커서 넘기기 ③", "if not _can_edit_meeting(u, dict(r)):",
    "if not _can_edit_meeting(u, dict(r), c):", 1)
sub("고치기 권한에 커서 넘기기 ④", "if not _can_edit_meeting(u, dict(m)):",
    "if not _can_edit_meeting(u, dict(m), c):", 1)
sub("고치기 권한에 커서 넘기기 ⑤(녹음 입구)", "if need_edit and not _can_edit_meeting(u, mm):",
    "if need_edit and not _can_edit_meeting(u, mm, c):", 1)
sub("공유 화면 회의 목록에 커서 넘기기",
    "mine = [dict(r) for r in rows if _can_edit_meeting(u, dict(r))][:12]",
    "mine = [dict(r) for r in rows if _can_edit_meeting(u, dict(r), c)][:12]", 1)
sub("회의 종료 입구에 커서 넘기기", "if not _can_end_meeting(u, m):",
    "if not _can_end_meeting(u, m, c):", 1)

if src == orig:
    print("바뀐 것이 없다 — 중지")
    raise SystemExit(1)
bak = P + ".bak_z1133"
if not os.path.exists(bak):
    open(bak, "w", encoding="utf-8").write(orig)
tmp = P + ".tmp_z1133"
with open(tmp, "w", encoding="utf-8", newline="") as f:
    f.write(src)
os.replace(tmp, P)
print("\n[완료] z1133 — %s" % " · ".join(done))
