# -*- coding: utf-8 -*-
"""관리자 '메일 보내기 설정' 화면 **실제 렌더** 시험 (대표 지시 2026-11-13).

왜: Jinja 문법 통과 ≠ 렌더 성공. 없는 칸 접근은 그릴 때만 터지고,
    그러면 대표가 그 화면을 열 때 500 이 난다.
    (로컬에 fastapi 가 없어 앱 기동 시험은 못 하므로, 화면만 따로 그려 본다.)

둘레 장식(chrome/mail_app_head)은 앱이 넣어 주는 전역을 많이 쓰고 내가 고친 곳이 아니라,
없는 전역은 빈 값으로 넘기는 '관대한' 환경을 쓴다. 보려는 건 내가 넣은 카드가 그려지는가다.
"""
import os
import sys
import traceback

ROOT = sys.argv[1]
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import jinja2  # noqa: E402
from jinja2 import Environment, FileSystemLoader  # noqa: E402

PASS = FAIL = 0


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [PASS]", name)
    else:
        FAIL += 1
        print("  [FAIL]", name, extra)


class Lenient(jinja2.Undefined):
    """앱이 넣어 주는 전역·함수의 대역. 불러도·칸을 따도 빈 값."""
    __slots__ = ()

    def __call__(self, *a, **k):
        return ""

    def __getattr__(self, k):
        if k.startswith("__"):
            raise AttributeError(k)
        return ""

    def __getitem__(self, k):
        return ""

    def __str__(self):
        return ""

    def __iter__(self):
        return iter(())

    def __bool__(self):
        return False


class Blank(dict):
    def __getattr__(self, k):
        return self.get(k, "")

    def __missing__(self, k):
        return ""


env = Environment(loader=FileSystemLoader(os.path.join(ROOT, "app", "templates")),
                  autoescape=True, undefined=Lenient)
env.globals.update(i=Blank(), cfg=Blank(), settings=Blank())

FAKE_PW = "FAKE-not-a-real-password-0000"

ST_OK = {"ok": True, "why": "", "addr": "top0015@knknara.co.kr",
         "host": "smtps.hiworks.com", "port": 465,
         "fetch_host": "pop3s.hiworks.com", "protocol": "pop3", "has_pass": True}
ST_NO = {"ok": False, "why": "「메일 가져오기」에 등록된 받기 계정이 없습니다. 그걸 먼저 등록하세요.",
         "addr": "", "host": "", "port": 465, "fetch_host": "", "protocol": "", "has_pass": False}


def render(mode, st, label):
    try:
        tpl = env.get_template("admin_mail_send.html")
        return tpl.render(
            request=None, user={"id": 5, "name": "김정락", "role": "ceo"},
            active="admin", ready=st["ok"], mail_key=True,
            cur_host="smtp.mx.cloudflare.net", cur_port="465",
            cur_user="relay-user", has_pass=True,
            cur_from="test@knk-mailtest.com",
            fetch_mode=mode, fetch_st=st,
            my_from=(st["addr"] or "test@knk-mailtest.com"),
            cur_fetch_host="", cur_fetch_port="465", saved=False,
            mail_app=True,
        )
    except Exception:
        check("렌더 성공 (%s)" % label, False, traceback.format_exc()[-1600:])
        return None


def tidy(s):
    return " ".join((s or "").split())


print("\n§ 관리자 '메일 보내기 설정' 화면 실제 렌더")

h = render("one", ST_OK, "켜짐 · 쓸 수 있음")
if h:
    t = tidy(h)
    check("렌더 성공 (켜짐 · 쓸 수 있음)", True)
    check("· 보내는 주소가 화면에 나온다", "top0015@knknara.co.kr" in h)
    check("· 보내기 서버가 화면에 나온다", "smtps.hiworks.com" in h)
    check("· '지금 바로 쓸 수 있습니다' 표시", "지금 바로 쓸 수 있습니다" in h)
    check("· '켜짐 · 나만' 표시", "켜짐 · 나만" in t)
    check("· '나만' 선택이 체크돼 있다", 'value="one" checked' in t)
    check("· 끄는 길이 화면에 있다", 'value="off"' in h and "끄기" in h)
    check("· 📮 지금 보내는 주소 안내가 있다", "지금 보내는 주소" in h)
    check("⭐비밀번호가 화면에 없다", FAKE_PW not in h and "gAAAAA" not in h)
    check("· 두 폼이 구분자를 각각 갖는다",
          'value="via_fetch"' in h and 'value="smtp"' in h)

h = render("off", ST_NO, "꺼짐 · 아직 못 씀")
if h:
    t = tidy(h)
    check("렌더 성공 (꺼짐 · 아직 못 씀)", True)
    check("· '아직 못 씁니다' + 이유 표시",
          "아직 못 씁니다" in h and "등록된 받기 계정이 없습니다" in h)
    check("· 「메일 가져오기」로 가는 길 표시", "/admin/mail-fetch" in h)
    check("· 꺼짐 표시", "꺼짐" in h)
    check("· 끄기가 체크돼 있다", 'value="off" checked' in t)

h = render("all", ST_OK, "전 직원")
if h:
    check("렌더 성공 (전 직원)", True)
    check("· '켜짐 · 전 직원' 표시", "켜짐 · 전 직원" in tidy(h))

h = render("one", dict(ST_OK, ok=False,
                       why="받기 호스트(pop.x)에 맞는 보내기(SMTP) 호스트를 모릅니다. 아래 '직접 입력'에 넣으세요."),
           "켜졌는데 못 씀(엇갈린 상태)")
if h:
    check("렌더 성공 (켜졌는데 못 씀 — 엇갈린 상태)", True)
    check("· 켜짐인데 경고를 함께 보여 준다", "켜짐" in h and "아직 못 씁니다" in h)
    check("· 직접 입력 안내가 보인다", "직접 입력" in h)

print("\n" + "=" * 56)
print("  통과 %d / 실패 %d" % (PASS, FAIL))
print("=" * 56)
sys.exit(1 if FAIL else 0)
