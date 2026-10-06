# -*- coding: utf-8 -*-
"""z1141 — 아이폰에서 「📁 녹음 파일 올리기」가 안 되던 것 (직원 신고 2026-10-06)

신고: 박성수 프로(사번 317 · 아이폰) — 「녹음파일 올리기 눌러서 누르면 반응이 없어」
      (보내 준 사진 = 파일 앱 정보창 · `기산로 3.m4a` 15.5MB · 30:10)
실측: 서버에 **요청이 아예 안 들어왔다**(올리기 기록 없음) → 휴대폰 안에서 막힌 것.
      박성수 프로는 같은 날 14:56 에 한 번 성공한 적 있음(PC 로 보임).

아이폰에서 알려진 두 가지를 함께 고친다(둘 다 작고 다른 기기에 해가 없다):
  ① 고를 수 있는 파일 조건이 `audio/*` 하나뿐 — 아이폰은 이걸 좁게 봐서 **녹음 파일이 안 눌리는** 일이 있다.
     → 서버가 실제로 받는 **확장자 12가지를 함께** 적는다(서버 `_MEETING_AUDIO_EXT` 와 같게 — 고를 수 있는데
       서버가 퇴짜 놓는 일이 없게).
  ② 입력칸을 `display:none` 으로 숨김 — 아이폰 일부 상황에서 **파일 고르기 창 자체가 안 열린다**.
     → 「안 보이게」 하되 「없는 것」으로는 만들지 않는 방식(접근성 표준)으로 바꾼다.

🔴 「📱 녹음기로 바로 녹음」(recFileCap)의 `accept` 는 **건드리지 않는다** — 거기에 확장자를 붙이면
   아이폰이 녹음기 대신 파일 고르기를 열 수 있다. 숨기는 방식만 함께 바꾼다.

🔎 내 시험으로는 아이폰 파일 고르기를 재현할 수 없다 → **박성수 프로 실물 확인 필요**.

사용: python patch_z1141.py <meeting_form.html 경로>
"""
import io
import os
import sys

# 서버 _MEETING_AUDIO_EXT 와 같게 (2026-10-06 실측)
EXTS = ".m4a,.mp3,.mp4,.wav,.webm,.ogg,.oga,.aac,.3gp,.mpeg,.mpga,.caf"
ACCEPT = 'accept="audio/*,%s"' % EXTS

CSS = """/* ── 📁 파일 고르기 입력칸 숨기기 — z1141 (아이폰 신고 2026-10-06) ──
   🔴 `display:none` 은 아이폰에서 단추를 눌러도 **파일 고르기 창이 안 열리는** 일이 있다.
   「안 보이게」 하되 「없는 것」으로는 만들지 않는다(접근성 표준 방식 · 자리도 차지하지 않는다). */
.knk-file-vh { position:absolute; width:1px; height:1px; padding:0; margin:-1px;
  overflow:hidden; clip:rect(0 0 0 0); clip-path:inset(50%); white-space:nowrap; border:0; }
"""


def put(path, text):
    data = text.encode("utf-8")        # 🔴 쓰기 전에 인코딩을 먼저 해 본다
    tmp = path + ".tmp_z1141"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)


def main():
    if len(sys.argv) < 2:
        print("사용: python patch_z1141.py <meeting_form.html 경로>")
        return 2
    p = sys.argv[1]
    if not os.path.exists(p):
        print("없는 파일:", p)
        return 2
    s = io.open(p, encoding="utf-8").read()
    if "knk-file-vh" in s:
        print("이미 z1141 이 들어 있음 — 건너뜀")
        return 0

    # ① CSS
    a = "#sumEditWrap[hidden], #mtgSummary[hidden] { display:none !important; }\n"
    if s.count(a) != 1:
        print("자리 못 찾음(%d): ① CSS" % s.count(a))
        return 3
    s = s.replace(a, a + CSS, 1)
    print("적용: ① 숨김 방식 CSS(.knk-file-vh)")

    # ② 올리기 입력칸 3개 — 확장자 넓히고 숨김 방식 바꾸기
    old_up = 'accept="audio/*" data-knk-no-dropzone style="display:none"'
    n_up = s.count(old_up)
    if n_up != 3:
        print("자리 못 찾음(%d개, 3개여야 함): ② 올리기 입력칸" % n_up)
        return 3
    s = s.replace(old_up, ACCEPT + ' data-knk-no-dropzone class="knk-file-vh"')
    print("적용: ② 올리기 입력칸 3곳 — 확장자 12가지 + 아이폰 안전 숨김")

    # ③ 「녹음기로 바로 녹음」 2개 — accept 는 그대로, 숨김 방식만
    old_cap = 'accept="audio/*" capture data-knk-no-dropzone style="display:none"'
    n_cap = s.count(old_cap)
    if n_cap != 2:
        print("자리 못 찾음(%d개, 2개여야 함): ③ 녹음기 입력칸" % n_cap)
        return 3
    s = s.replace(old_cap, 'accept="audio/*" capture data-knk-no-dropzone class="knk-file-vh"')
    print("적용: ③ 녹음기 입력칸 2곳 — 숨김 방식만(accept 는 그대로)")

    if 'style="display:none"' in s.split("</style>", 1)[1]:
        left = s.split("</style>", 1)[1].count('style="display:none"')
        print("   (참고: 화면 쪽에 남은 display:none %d곳 — 파일 칸이 아니면 정상)" % left)

    put(p, s)
    print("저장:", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
