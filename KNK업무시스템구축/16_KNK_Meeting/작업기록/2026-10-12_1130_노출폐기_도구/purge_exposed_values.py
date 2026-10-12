# -*- coding: utf-8 -*-
"""노출된 설정 값 폐기 — 대표 지시 2026-10-12 「기존 너가 노출한 부분 폐기」.

■ 무엇을 지우나
  2026-10-11 21:48 KST, 세션 16(빅터)이 운영 `app_settings` 를 통째로 읽어 찍은 출력.
  가리는 판정을 **칸 이름**으로 써서 **이름을 가리고 값을 찍은** 실수였다.
  그 출력에서 **비밀값처럼 보이는 토막(길이 20자 이상)** 만 골라, 같은 길이의 `*` 로 바꾼다.

■ 어떻게 (왜 이 방식인가)
  🔵 **바이트 길이를 그대로 유지**하며 제자리에 덮어쓴다(`r+b` + seek).
     기록 파일은 **지금 돌아가는 세션이 뒤에 계속 덧붙이는 파일**이라,
     이름 바꾸기·전체 재작성은 윈도우 파일 잠금·줄 유실 위험이 있다.
     길이를 유지하면 뒤에 덧붙는 글에 **아무 영향이 없다.**
  🔵 `*` 는 JSON 에서 그대로 쓸 수 있는 글자라 **줄이 깨지지 않는다**(쓰기 전에 다시 읽어 검사).

■ ⛔ 안 하는 것
  · 값을 화면에 찍지 않는다 (출력은 **개수와 길이뿐**).
  · **평문 백업을 만들지 않는다** — 백업이 비밀값을 그대로 보관하게 되므로.
    대신 바꾼 줄이 **JSON 으로 다시 읽히는지** 쓰기 전에 검사하고, 안 읽히면 그 파일은 건너뛴다.
  · 기록 내용을 지우지 않는다 — **비밀값 토막만** 바꾼다(대화 흐름은 그대로 읽힌다).

■ 쓰는 법 (PowerShell)
    # ① 먼저 무엇을 바꿀지만 보기 (아무것도 안 바꿈)
    python "<이 파일>"
    # ② 실제로 바꾸기
    python "<이 파일>" --apply
"""
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

D = "C:/Users/top00/.claude/projects/C--Users-top00-JR-Claude---"
SRC_FILE = "31b97fce-95eb-4c01-8a66-eddd91b2bd12.jsonl"   # 노출이 일어난 세션
SRC_LINE = 33769                                           # 그 도구 결과 줄
APPLY = "--apply" in sys.argv


def find_source_tokens():
    """노출된 그 출력에서 **비밀값 후보 토막**을 뽑는다(메모리 안에서만)."""
    p = os.path.join(D, SRC_FILE)
    line = None
    with io.open(p, "rb") as fh:
        for n, raw in enumerate(fh, 1):
            if n == SRC_LINE:
                line = raw
                break
    if line is None:
        raise SystemExit("!! 그 줄(%d)을 못 찾았습니다 — 파일이 바뀐 듯합니다." % SRC_LINE)
    o = json.loads(line.decode("utf-8").rstrip("\r\n"))
    s = o.get("toolUseResult", {}).get("stdout", "")
    if "gAAAA" not in s:
        raise SystemExit("!! 그 줄에 기대한 표식이 없습니다 — 이미 지워졌거나 줄 번호가 달라졌습니다.")
    toks = {t for t in re.findall(r"[A-Za-z0-9+/=_\-]{20,}", s)}
    # UUID 처럼 생긴 것은 비밀값이 아니다
    toks = {t for t in toks if not re.fullmatch(r"[0-9a-f]{8}-?[0-9a-f-]{20,}", t)}
    return sorted(toks, key=len, reverse=True)


def main():
    toks = find_source_tokens()
    print("비밀값 후보 토막 %d개 (길이: %s)"
          % (len(toks), ", ".join(str(len(t)) for t in toks)))
    print("바꾸는 방식: 같은 길이의 '*' 로 → 바이트 길이 그대로 → 돌아가는 세션에 영향 없음")
    print("모드: %s\n" % ("🔴 실제로 바꿉니다(--apply)" if APPLY else "🔵 보기만 합니다(안 바꿈)"))

    total = 0
    for fn in sorted(os.listdir(D)):
        if not fn.endswith(".jsonl"):
            continue
        p = os.path.join(D, fn)
        try:
            blob = io.open(p, "rb").read()
        except Exception as e:
            print("  읽기 실패 %-42s %s" % (fn, e))
            continue

        new = blob
        per = 0
        for t in toks:
            b = t.encode("utf-8")
            c = new.count(b)
            if c:
                new = new.replace(b, b"*" * len(b))
                per += c
        if not per:
            continue
        total += per
        assert len(new) == len(blob), "길이가 바뀌었습니다 — 멈춥니다"

        # 쓰기 전 검사: 바뀐 줄이 전부 JSON 으로 다시 읽히나
        ok = True
        bad = 0
        for ln in new.split(b"\n"):
            if not ln.strip():
                continue
            try:
                json.loads(ln.decode("utf-8").rstrip("\r"))
            except Exception:
                bad += 1
                ok = False
        if not ok:
            print("  ⚠ %-42s %d군데 — 그런데 JSON 이 깨지는 줄 %d개 → **건너뜁니다**" % (fn, per, bad))
            continue

        if APPLY:
            with open(p, "r+b") as fh:
                cur = fh.read()
                if cur != blob:
                    print("  ⚠ %-42s 그 사이 파일이 바뀌었습니다 → 건너뜁니다" % fn)
                    continue
                fh.seek(0)
                fh.write(new)
                fh.flush()
                os.fsync(fh.fileno())
            print("  ✅ %-42s %d군데 폐기" % (fn, per))
        else:
            print("  · %-42s %d군데 바뀔 예정" % (fn, per))

    print("\n합계 %d군데%s" % (total, " 폐기했습니다." if APPLY else " 바뀔 예정입니다."))
    if APPLY:
        print("확인: 아래를 다시 돌리면 「그 줄에 기대한 표식이 없습니다」가 나와야 정상입니다")
        print("      (원본 줄의 표식까지 지워졌다는 뜻).")
    else:
        print("실제로 바꾸려면 끝에 --apply 를 붙여 다시 돌려 주십시오.")


if __name__ == "__main__":
    main()
