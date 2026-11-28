# -*- coding: utf-8 -*-
"""이음메일 선 아이콘 — 화면 글(템플릿)에서 그림 문자 대신 쓰는 SVG (11-28 대표 「이음메일 디자인을 코드로」 4단계).

아이콘 모양은 한 곳: templates/_v5_partials/mail_design_icons.html 의 window.MD_ICONS(lucide-static · ISC 허가).
  이 파일은 그 표를 읽어 서버에서 <svg class="md-i"> 를 만든다 → 화면을 그리기 전부터 아이콘(흔들림 0).
  모양(viewBox·선 굵기 1.8·둥근 끝)은 브라우저가 그림 문자를 바꿔 끼우던 것(mail_design_v2.html svg())과 똑같이.
템플릿: {{ mi('inbox') }} · 뜻 글을 함께 읽어 주려면 단추에 title·aria-label 을 그대로 둔다(아이콘은 aria-hidden).
스크립트(JS)에서 만드는 단추는 window.mdI('inbox') (mail_design_icons.html).
"""
import io
import json
import os
import re

from markupsafe import Markup

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(_HERE, "templates", "_v5_partials", "mail_design_icons.html")
_ICONS = None


def _load():
    """mail_design_icons.html 의 MD_ICONS 표(자동 생성 줄 + 손으로 더한 줄)를 읽는다."""
    s = io.open(_SRC, encoding="utf-8").read()
    out = {}
    m = re.search(r"window\.MD_ICONS=(\{.*?\});</script>", s, re.S)
    if m:
        out.update(json.loads(m.group(1)))
    # 손으로 더한 줄: MD_ICONS["name"]="..."
    for mm in re.finditer(r'MD_ICONS\["([a-z0-9-]+)"\]\s*=\s*("(?:[^"\\]|\\.)*")', s):
        out.setdefault(mm.group(1), json.loads(mm.group(2)))
    return out


def icons():
    global _ICONS
    if _ICONS is None:
        _ICONS = _load()
    return _ICONS


def mi(name, cls=""):
    """선 아이콘 하나(없는 이름이면 빈 글 — 화면이 깨지지 않게, 시험 mail_icons_test 가 이름을 확인)."""
    body = icons().get(name)
    if not body:
        return Markup("")
    c = "md-i" + ((" " + cls) if cls else "")
    return Markup('<svg width="1.15em" height="1.15em" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
                  'stroke-linejoin="round" aria-hidden="true" class="%s">%s</svg>' % (c, body))


# 목록 줄처럼 같은 아이콘이 수백 번 나오는 곳 — 모양은 한 번(mi_sprite)만 싣고 줄마다 <use> 로 부름(쪽 크기 그대로)
ROW_ICONS = ("star", "paperclip", "send", "message-square", "flag", "alarm-clock", "briefcase", "archive", "triangle-alert", "trash-2", "file-pen")


def mi_ref(name, cls=""):
    """mi() 와 같은 모양 · 내용은 쪽 안 <symbol id="mdi-이름">(mi_sprite) 을 부름."""
    if name not in icons():
        return Markup("")
    c = "md-i" + ((" " + cls) if cls else "")
    return Markup('<svg width="1.15em" height="1.15em" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
                  'stroke-linejoin="round" aria-hidden="true" class="%s"><use href="#mdi-%s"/></svg>' % (c, name))


def mi_sprite(names=ROW_ICONS):
    """mi_ref 가 부르는 모양 묶음(보이지 않는 svg 하나) — 쪽마다 한 번."""
    d = icons()
    return Markup('<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false">%s</svg>'
                  % "".join('<symbol id="mdi-%s" viewBox="0 0 24 24">%s</symbol>' % (n, d[n]) for n in names if n in d))
