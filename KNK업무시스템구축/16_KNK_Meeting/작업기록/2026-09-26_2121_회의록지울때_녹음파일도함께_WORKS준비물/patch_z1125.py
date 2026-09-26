# -*- coding: utf-8 -*-
"""z1125 — 회의록을 지우면 그 회의의 녹음 파일도 함께 지운다 (대표 결정 2026-09-26 「지울때 함께 지워」)
  ① `_meeting_audio_purge(mid)` — `meeting_audio/meeting_<번호>/` 폴더만 지운다(다른 회의·`_share` 는 안 건드림 · 실패해도 삭제는 유지)
  ② WORKS 🗑 삭제(`DELETE /api/meeting/{mid}`)·이음 🗓 삭제 입구(`POST /api/meeting/msg/delete`) 둘 다에서 호출(느릴 수 있어 스레드에서)
  ③ 확인 창 글에 「녹음 파일도 서버에서 지워집니다」 한 마디
사용: py patch_z1125.py <앱 사본 폴더(app/ 가 들어 있는 곳)>
기준: 운영 z1124(main 4c1a9cbf · meeting_form 331c2e9f)"""
import hashlib
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = sys.argv[1]
BASE = {"app/main.py": "4c1a9cbf", "app/templates/meeting_form.html": "331c2e9f"}


def rd(rel):
    raw = open(os.path.join(ROOT, rel), "rb").read()
    h = hashlib.sha256(raw).hexdigest()[:8]
    assert h == BASE[rel], f"{rel} 기준이 다름: {h} (기대 {BASE[rel]})"
    s = raw.decode("utf-8")
    assert "\r\n" not in s
    return s


def wr(rel, s):
    p = os.path.join(ROOT, rel)
    tmp = p + ".tmp_z1125"
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

HELPER = '''
def _meeting_audio_purge(mid: int) -> dict:
    """회의록을 지울 때 그 회의의 녹음 파일도 함께 지운다 (z1125 · 대표 결정 2026-09-26 「지울때 함께 지워」).
    전에는 DB 줄만 지우고 `meeting_audio/meeting_<번호>/` 는 서버에 남았다(화면에선 안 보이지만 파일은 남음).
    🔴 그 회의 폴더 하나만 — 폴더 이름·경로를 다시 확인해 `meeting_audio` 밖이나 `_share`(아직 어느 회의인지 정해지지 않은 파일)는 건드리지 않는다.
    🔴 지우다 실패해도 회의록 삭제는 이미 끝났다 → 실패는 기록만 남기고 넘어간다(삭제를 되돌리지 않는다).
    디스크가 느릴 수 있어(NAS) 부르는 쪽에서 스레드로 돌린다."""
    out = {"files": 0, "bytes": 0}
    try:
        mid = int(mid)
        base = os.path.abspath("meeting_audio")
        d = os.path.abspath(os.path.join("meeting_audio", f"meeting_{mid}"))
        if os.path.basename(d) != f"meeting_{mid}" or os.path.dirname(d) != base:
            print(f"[MEETING-AUDIO] 지우지 않음(폴더 자리가 이상): {d}")
            return out
        if not os.path.isdir(d):
            return out
        for root, _dirs, files in os.walk(d):
            for fn in files:
                out["files"] += 1
                try:
                    out["bytes"] += os.path.getsize(os.path.join(root, fn))
                except OSError:
                    pass
        import shutil as _sh
        _sh.rmtree(d)
        print(f"[MEETING-AUDIO] 회의 {mid} 녹음 파일 {out['files']}개({out['bytes'] // 1024}KB) 함께 지움")
    except Exception as _e:
        print(f"[MEETING-AUDIO] 녹음 파일 지우기 실패(회의록은 지워짐): {type(_e).__name__}: {str(_e)[:160]}")
    return out
'''

# ① 도우미 — 음성(모드 B) 구역 머리글 앞에
s = rep(s,
        "\n\n# ── 모드 B: 음성 녹음 → Whisper 음성→글자 (z412+ ) ──────────────────────────\n",
        "\n" + HELPER + "\n\n# ── 모드 B: 음성 녹음 → Whisper 음성→글자 (z412+ ) ──────────────────────────\n",
        "도우미 자리")

# ② WORKS 🗑 삭제 — DB 줄을 지운 뒤 녹음 파일도
s = rep(s,
        '        c.execute("DELETE FROM meetings WHERE id=?", (mid,))\n'
        '    try:   # z1122: 「🗓 회의 카드 모아보기」가 30초 저장본을 보여 주지 않게 — 지운 회의가 바로 빠진다\n',
        '        c.execute("DELETE FROM meetings WHERE id=?", (mid,))\n'
        '    # z1125 (대표 결정 2026-09-26): 그 회의의 녹음 파일도 함께 — 디스크가 느릴 수 있어 스레드에서\n'
        '    #   🔴 이음과 무관한 회의는 위 블록을 건너뛰어 run_in_threadpool 이름이 없다 → 여기서 다시 불러온다\n'
        '    from starlette.concurrency import run_in_threadpool\n'
        '    await run_in_threadpool(_meeting_audio_purge, mid)\n'
        '    try:   # z1122: 「🗓 회의 카드 모아보기」가 30초 저장본을 보여 주지 않게 — 지운 회의가 바로 빠진다\n',
        "WORKS 삭제에서 호출")

# ③ 이음 🗓 삭제 입구 — 지웠을 때만
s = rep(s,
        '                except Exception as _le:\n'
        '                    print(f"[MEETING-MSG] 활동기록 실패(삭제는 완료): {_le}")\n'
        '    try:   # 이음 회의가 곧 지워진다 — 「🗓 회의 카드 모아보기」 30초 저장본을 비워 바로 빠지게(z1122 와 같게)\n',
        '                except Exception as _le:\n'
        '                    print(f"[MEETING-MSG] 활동기록 실패(삭제는 완료): {_le}")\n'
        '    if out.get("result") == "deleted":   # z1125: 그 회의의 녹음 파일도 함께(대표 결정 2026-09-26)\n'
        '        from starlette.concurrency import run_in_threadpool\n'
        '        await run_in_threadpool(_meeting_audio_purge, out["works_meeting_id"])\n'
        '    try:   # 이음 회의가 곧 지워진다 — 「🗓 회의 카드 모아보기」 30초 저장본을 비워 바로 빠지게(z1122 와 같게)\n',
        "이음 입구에서 호출")
assert s.count("_meeting_audio_purge") == 3
wr("app/main.py", s)

# ─────────────────────────── meeting_form.html ───────────────────────────
s = rd("app/templates/meeting_form.html")
s = rep(s,
        "\\n\\n녹음·음성 글자·정리·결정·할 일을 더 이상 볼 수 없습니다.\\n(이미 일일카드로 보낸 할 일은 그대로 남습니다)';\n",
        "\\n\\n녹음·음성 글자·정리·결정·할 일을 더 이상 볼 수 없습니다.\\n"
        "(녹음 파일도 서버에서 지워집니다 · 이미 일일카드로 보낸 할 일은 그대로 남습니다)';\n",
        "확인 창 글")
wr("app/templates/meeting_form.html", s)
print("[OK] z1125 패치 끝")
