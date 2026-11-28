# -*- coding: utf-8 -*-
"""메일 시험 공용 — 화면의 선 아이콘 SVG 를 짧은 표 「[i:이름]」 로 바꿔 읽기 (11-28 4단계 「화면 옮기기」).

4단계에서 단추·폴더·메뉴 이름의 그림 문자(📥 ⭐ 🗑 …)를 선 아이콘(<svg class="md-i">)으로 바꿨다.
예전 시험은 「📥 받은편지함」 같은 글자를 찾았으므로, 같은 뜻을 「[i:inbox] 받은편지함」 으로 확인한다
(아이콘 이름까지 맞아야 통과 → 시험이 약해지지 않음 · 아무 아이콘이나 되는 것이 아님).
  ico(html)  → 서버가 그린 mi()·mi_ref() SVG 와 스크립트 글 속 '+mdI('이름')+' 을 [i:이름] 으로
  I(이름)    → "[i:이름]"
"""
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from app.mail_icons import icons  # noqa: E402

_BODY = {v: k for k, v in icons().items()}
_SVG = re.compile(r'<svg\b[^>]*class="md-i[^"]*"[^>]*>(.*?)</svg>', re.S)
_USE = re.compile(r'<use href="#mdi-([a-z0-9-]+)"\s*/>')
_JS = re.compile(r"'\+mdI\('([a-z0-9-]+)'\)\+'")
_JINJA = re.compile(r"\{\{ mi(?:_ref)?\('([a-z0-9-]+)'\) \}\}")   # 템플릿 원문(파일을 직접 읽는 시험)


def _one(m):
    inner = m.group(1)
    u = _USE.search(inner)
    if u:
        return "[i:%s]" % u.group(1)
    return "[i:%s]" % _BODY.get(inner, "?")


def ico(h):
    h = _SVG.sub(_one, h or "")
    h = _JINJA.sub(lambda m: "[i:%s]" % m.group(1), h)
    return _JS.sub(lambda m: "[i:%s]" % m.group(1), h)


def I(name):
    return "[i:%s]" % name


class _R:
    def __init__(self, r):
        self._r = r
        self.status_code = r.status_code
        self.headers = r.headers
        self.text = ico(r.text)

    def json(self):
        return self._r.json()

    def __getattr__(self, k):
        return getattr(self._r, k)


class IcoClient:
    """시험 클라이언트를 감싸 .text 를 ico() 로 읽음(get·post 그대로)."""
    def __init__(self, c):
        self._c = c

    def get(self, *a, **kw):
        return _R(self._c.get(*a, **kw))

    def post(self, *a, **kw):
        return _R(self._c.post(*a, **kw))

    def __getattr__(self, k):
        return getattr(self._c, k)


def install():
    """이 시험 안의 모든 응답 글(httpx Response.text)을 ico() 로 읽게 함 — 시험 맨 위에서 한 번."""
    import httpx
    if getattr(httpx.Response, "_mail_ico", False):
        return
    _orig = httpx.Response.text

    def _text(self):
        return ico(_orig.fget(self))
    httpx.Response.text = property(_text)
    httpx.Response._mail_ico = True


def emo2tok(text):
    """글 속 그림 문자를 [i:이름] 으로(화면이 바꿔 그리는 것과 같은 표 — mail_design_v2.html MAP)."""
    import io as _io
    src = _io.open(os.path.join(_ROOT, "app", "templates", "_v5_partials", "mail_design_v2.html"), encoding="utf-8").read()
    mp = dict(re.findall(r"'([^']+)':'([a-z0-9-]+)'", src.split("var MAP=")[1].split("};")[0]))
    out = []
    for ch in (text or "").replace("️", ""):
        out.append("[i:%s]" % mp[ch] if ch in mp and ch not in "↩↪" else ch)
    return "".join(out)
