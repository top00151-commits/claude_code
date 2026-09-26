# -*- coding: utf-8 -*-
"""z1126 화면 시험 — WORKS 🗑 삭제 뒤 「🔔 참석자 N명에게 「회의가 취소되었습니다」」(z1126 · 새 규칙 = 나 말고 참석자가 있으면 언제나) 안내
  이음이 notified 를 줄 때만 · 안 줄 때(둘 다 지움)는 전처럼 알림 없이 목록으로 · 거절·입구 없음 알림은 그대로
실제 크롬 · 서버 = run_z1123_app.py(가짜 이음). 사용: py -3.12 ui_z1123.py <seed_del.json 폴더>"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright   # noqa: E402

SEED = json.load(io.open(os.path.join(sys.argv[1], "seed_del.json"), encoding="utf-8"))
IDS, CEO, OWNER = SEED["ids"], SEED["ceo"], SEED["owner"]
BASE = "http://localhost:%d" % SEED["port"]
UA_IOS = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
          "Version/18.2 Mobile/15E148 Safari/604.1")
UA_PC = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36")
HIDE = ("document.addEventListener('DOMContentLoaded', () => { const s = document.createElement('style');"
        "s.textContent = '#worksInstallHint{display:none !important}'; document.head.appendChild(s); });")
OK, NG, ERRS = [], [], []


def ok(name, cond, extra=""):
    (OK if cond else NG).append(name)
    print(("PASS " if cond else "FAIL ") + name + ((" · " + str(extra)[:220]) if extra != "" else ""), flush=True)


def ctx(br, uid, phone=False):
    c = br.new_context(service_workers="block", user_agent=UA_IOS if phone else UA_PC,
                       viewport={"width": 390, "height": 844} if phone else {"width": 1280, "height": 900},
                       is_mobile=phone, has_touch=phone)
    c.add_cookies([{"name": "tuser", "value": str(uid), "url": BASE}])
    c.add_init_script(HIDE)
    return c


class Dialogs:
    def __init__(self, page):
        self.plan, self.msgs = [], []
        page.on("dialog", self._on)

    def _on(self, d):
        self.msgs.append((d.type, d.message))
        (d.accept() if (self.plan.pop(0) if self.plan else "dismiss") == "accept" else d.dismiss())

    def set(self, *plan):
        self.plan, self.msgs = list(plan), []


def exists(p, mid):
    r = p.evaluate("async (u) => (await fetch(u)).status", "/api/meeting/%d/rec-status" % mid)
    return r == 200


def delete_flow(br, uid, mid, phone=False, plan=("accept", "accept", "accept")):
    c = ctx(br, uid, phone)
    p = c.new_page()
    p.on("pageerror", lambda e: ERRS.append(str(e)))
    dl = Dialogs(p)
    p.goto("%s/meetings/%d" % (BASE, mid), wait_until="domcontentloaded")
    p.wait_for_timeout(1200)
    dl.set(*plan)
    p.locator("#btnDelete").click()
    p.wait_for_url("**/meetings", timeout=15000)
    p.wait_for_timeout(800)
    return c, p, dl


def main():
    with sync_playwright() as pw:
        br = pw.chromium.launch(channel="chrome", headless=True)

        print("\n■ ① 이음이 「참석자 3명에게 취소 알림」이라고 답함 → 지운 뒤 한 번 알림 (아이폰 · 작성자=등록자)", flush=True)
        c, p, dl = delete_flow(br, OWNER, IDS["D8"], phone=True)
        types = [t for t, _ in dl.msgs]
        ok("창 3개 = 확인 2 + 알림 1", types == ["confirm", "confirm", "alert"], types)
        m3 = dl.msgs[2][1] if len(dl.msgs) > 2 else ""
        ok("알림 = 「회의록과 이음 회의를 지웠습니다」", "회의록과 이음 회의를 지웠습니다." in m3, m3)
        ok("알림 = 「🔔 참석자 3명에게 「회의가 취소되었습니다」 알림이 갔습니다」",
           "🔔 참석자 3명에게 「회의가 취소되었습니다」 알림이 갔습니다." in m3, m3)
        ok("🔴 옛 글 「시작 전 회의라」 없음(z1126)", "시작 전 회의라" not in m3, m3)
        m1 = dl.msgs[0][1] if dl.msgs else ""
        ok("첫 확인 창에 「나 말고 참석자가 있으면 「회의가 취소되었습니다」 알림이 갑니다」",
           "(나 말고 참석자가 있으면 「회의가 취소되었습니다」 알림이 갑니다)" in m1, m1[-120:])
        ok("첫 확인 창의 이음 줄도 그대로", "🗓 이음 회의도 함께 지워집니다" in m1)
        ok("목록으로 · 회의록 없음", p.url.rstrip("/").endswith("/meetings") and not exists(p, IDS["D8"]), p.url)
        c.close()

        print("\n■ ② 이음이 notified 를 안 줌(둘 다 지움) → 전처럼 알림 없이 목록으로 (PC · 대표)", flush=True)
        c, p, dl = delete_flow(br, CEO, IDS["D2"], plan=("accept", "accept"))
        ok("창 2개뿐(확인 2 · 추가 알림 없음)", [t for t, _ in dl.msgs] == ["confirm", "confirm"], [t for t, _ in dl.msgs])
        # z1126: 첫 확인 창에는 「…있으면 취소 알림이 갑니다」 미리 안내가 들어간다 → 여기서 보는 것은 **삭제 뒤 알림**뿐
        ok("삭제 뒤 취소 알림 안내 없음(확인 창의 미리 안내는 제외)",
           not any(t == "alert" and "회의가 취소되었습니다" in m for t, m in dl.msgs), [t for t, _ in dl.msgs])
        ok("지워짐", not exists(p, IDS["D2"]))
        c.close()

        print("\n■ ③ 이음이 거절 · 입구 없음 → 원래 까닭 알림 그대로(취소 알림 문구 없음)", flush=True)
        c, p, dl = delete_flow(br, OWNER, IDS["D3"])
        m3 = dl.msgs[2][1] if len(dl.msgs) > 2 else ""
        ok("거절 → 「등록한 사람(또는 관리자)만」", "등록한 사람(또는 관리자)만" in m3 and "회의가 취소되었습니다" not in m3, m3)
        c.close()
        c, p, dl = delete_flow(br, OWNER, IDS["D4"])
        m3 = dl.msgs[2][1] if len(dl.msgs) > 2 else ""
        ok("입구 없음 → 「이음 쪽 준비 중」", "이음 쪽 준비 중" in m3 and "회의가 취소되었습니다" not in m3, m3)
        c.close()

        ok("화면 오류 없음", not ERRS, ERRS[:3])
        br.close()
    print("\n" + "=" * 72)
    print("합계: 통과 %d · 실패 %d" % (len(OK), len(NG)))
    for x in NG:
        print("  - 실패:", x)
    sys.exit(1 if NG else 0)


if __name__ == "__main__":
    main()
