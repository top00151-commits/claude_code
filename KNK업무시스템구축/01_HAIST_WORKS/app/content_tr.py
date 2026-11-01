# -*- coding: utf-8 -*-
"""
🌐 z1199 — 회의록 내용 베트남어 번역(뒤에서 · 저장해 다시 씀). 이 모듈은 「한국어 조각 → 베트남어」만 한다 —
   언제 번역할지 · 어디에 저장할지 · 누구에게 보일지는 main.py(_tr_*)가 정한다.

대표 2026-10-28 「베트남직원이 포함된 회의록은 베트남 직원이 봤을때 베트남어로 표현이 되는거야?」 → 시안 A·B →
결정: A안(베트남어 먼저 · 한국어 원문 보기) · 베트남어 참석자가 있으면 정리 직후 미리 · 범위 = 정리·결정·할 일·제목 + 양식·한눈에 보기.

· 품질 지킴(서버가 확인): 원문의 숫자(\\d+ 덩어리)가 번역에 모두 있다 · [결정]·[제안]·[미결]·[확인 필요]·[내부 방침] 표시와
  「v_」 개수가 같다 · 여러 줄 글은 줄 수와 줄 앞 모양(## · - · 1.)이 같다 · 원문 그대로 돌려준 것이 아니다.
  어긋나면 그 조각만 한 번 더(더 엄한 말) → 그래도 어긋나면 그 조각은 「실패」(화면은 그 조각만 한국어 원문).
· 로그에는 숫자만(회의 글·번역 글은 찍지 않는다).
· 시험 가짜 자리: _chat_json · _client · available (시험 서버가 바꿔 끼운다).
"""
import hashlib
import json
import os
import re
import time

try:
    import openai
except Exception:   # 시험·키 없는 곳
    openai = None

from . import ai_client

LANG = "vi"
MODELS = [m.strip() for m in (os.environ.get("KNK_WORKS_TR_MODELS") or "gpt-4.1,gpt-4o,gpt-4o-mini").split(",") if m.strip()]
TIMEOUT = 120
BATCH_ITEMS = 30          # 한 번에 보내는 조각 수
BATCH_CHARS = 6000        # 한 번에 보내는 원문 글자 수

SYSTEM = (
    "당신은 KNK(반도체·디스플레이 검사기와 자동화 설비를 만드는 회사)의 회의록 번역가입니다. "
    "한국어 회의록 조각들을 베트남 직원이 읽을 자연스럽고 정확한 베트남어로 옮깁니다.\n"
    "입력: JSON {\"items\": [{\"k\": 열쇠, \"t\": 한국어 글}]} · 출력: JSON {\"items\": [{\"k\": 같은 열쇠, \"t\": 베트남어}]} — "
    "열쇠와 개수를 그대로 두고 번역만 넣는다.\n"
    "꼭 지킬 것:\n"
    "1) 줄 수와 줄 순서를 그대로 둔다(한 줄 = 한 줄 · 빈 줄도 그 자리). 줄 앞 모양 「## 」「- 」「  - 」「1. 」은 그대로 둔다.\n"
    "2) [결정] [제안] [미결] [확인 필요] [내부 방침] 표시와 「v_」 표시는 글자 그대로 둔다(옮기지 않는다 — 화면이 베트남어로 바꿔 보여 준다).\n"
    "3) 숫자를 바꾸지 않는다 — 숫자·단위·날짜·시각·금액·수량·모델명·설비 번호·영문 약어는 원문 그대로 쓴다"
    "(숫자를 글자로, 글자를 숫자로 바꾸지 않는다).\n"
    "4) 사람 이름·회사 이름·고객사 이름은 원문 그대로 둔다(한글 이름은 한글 그대로).\n"
    "5) **굵게** 표시는 같은 낱말에 그대로 둔다.\n"
    "6) 회사 말: 호기 = máy (2호기 = máy số 2) · 베트남 법인 = Pháp nhân Việt Nam · 도금 = mạ · 에어호스 = dây khí · "
    "유닛 = cụm · 검사기 = máy kiểm tra · 시운전 = chạy thử · 반입 = đưa vào · 출하 = xuất hàng · 고객사 = khách hàng.\n"
    "7) 뜻을 더하거나 빼지 않는다 — 요약하지 말고 모두 옮긴다. 설명·따옴표·머리말 없이 번역만."
)
RETRY = ("\n\n⚠ 앞 번역에서 숫자·표시([결정] 등 · v_)·줄 수·줄 앞 모양 가운데 하나가 원문과 달랐다. "
         "위 규칙을 글자 그대로 지켜 다시 옮겨라.")


class TrError(Exception):
    pass


def available() -> bool:
    return bool(ai_client._key_for("openai")) and openai is not None


def sig(text) -> str:
    return hashlib.sha1((text or "").strip().encode("utf-8")).hexdigest()[:16]


def _client(timeout=TIMEOUT):
    key = ai_client._key_for("openai")
    if not key or openai is None:
        return None
    return openai.OpenAI(api_key=key, timeout=timeout, max_retries=1)


def _chat_json(client, model, system, user):
    r = client.chat.completions.create(model=model, temperature=0, response_format={"type": "json_object"},
                                       messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
    u = getattr(r, "usage", None)
    return (json.loads(r.choices[0].message.content or "{}"),
            ({"prompt": getattr(u, "prompt_tokens", 0), "completion": getattr(u, "completion_tokens", 0)} if u is not None else None))


# ── 품질 지킴 ─────────────────────────────────────────────────────
_TAG = re.compile(r"\[(결정|제안|미결|확인 ?필요|내부 방침)\]")
_NUM = re.compile(r"\d+")
_HAN = re.compile(r"[가-힣]")
_LEAD = re.compile(r"^\s*(#{1,3}\s|[-*•]\s|\d{1,2}[.)]\s)")


def _lines(t):
    return [ln for ln in (t or "").split("\n") if ln.strip()]


def check(src: str, dst: str) -> str:
    """'' = 통과 · 아니면 까닭(짧은 영문 낱말 — 글은 담지 않는다)."""
    s, d = (src or "").strip(), (dst or "").strip()
    if not d:
        return "empty"
    if d == s and _HAN.search(s):
        return "same"
    ns, nd = sorted(_NUM.findall(s)), _NUM.findall(d)
    rest = list(nd)
    for n in ns:
        if n in rest:
            rest.remove(n)
        else:
            return "nums"
    if len(rest) > 2 or any(int(x) > 10 for x in rest if len(x) < 6):
        return "nums+"
    if sorted(_TAG.findall(s)) != sorted(_TAG.findall(d)):
        return "tags"
    if s.count("v_") != d.count("v_"):
        return "v_"
    ls, ld = _lines(s), _lines(d)
    if len(ls) > 1 or len(ld) > 1:
        if len(ls) != len(ld):
            return "lines"
        for a, b in zip(ls, ld):
            ma, mb = _LEAD.match(a), _LEAD.match(b)
            ka = (ma.group(1).strip()[:1] if ma else "")
            kb = (mb.group(1).strip()[:1] if mb else "")
            if ka.isdigit():
                ka = "1"
            if kb.isdigit():
                kb = "1"
            if ka != kb:
                return "shape"
    return ""


# ── 한 번 묻기(모델 차례로) ───────────────────────────────────────────
def _ask(client, system, user, log):
    last = None
    for model in MODELS:
        try:
            data, usage = _chat_json(client, model, system, user)
            if isinstance(data, dict):
                return data, (usage or {}), model
        except Exception as e:   # 다음 모델로
            last = e
            log("[TR-Z1199] 모델 %s 실패: %s" % (model, type(e).__name__))
    raise TrError(type(last).__name__ if last else "no model")


def _batches(items: dict):
    cur, n = {}, 0
    for k, t in items.items():
        if cur and (len(cur) >= BATCH_ITEMS or n + len(t) > BATCH_CHARS):
            yield cur
            cur, n = {}, 0
        cur[k] = t
        n += len(t)
    if cur:
        yield cur


def translate(items: dict, log=print) -> dict:
    """{열쇠: 한국어} → {"texts": {열쇠: 베트남어}, "fails": {열쇠: 까닭}, "usage": [..], "model": str, "elapsed": 초}.
    키가 없거나 모델이 모두 실패하면 TrError(그때는 아무것도 저장하지 않는다)."""
    out = {"texts": {}, "fails": {}, "usage": [], "model": "", "elapsed": 0.0}
    items = {k: (t or "").strip() for k, t in (items or {}).items() if (t or "").strip()}
    if not items:
        return out
    client = _client()
    if client is None:
        raise TrError("no key")
    t0 = time.time()
    for batch in _batches(items):
        pending = dict(batch)
        for attempt in (1, 2):
            if not pending:
                break
            payload = json.dumps({"items": [{"k": k, "t": t} for k, t in pending.items()]}, ensure_ascii=False)
            data, usage, model = _ask(client, SYSTEM if attempt == 1 else SYSTEM + RETRY, payload, log)
            out["usage"].append(usage)
            out["model"] = model
            got = {}
            for it in (data.get("items") or []):
                if isinstance(it, dict) and it.get("k") in pending and isinstance(it.get("t"), str):
                    got[it["k"]] = it["t"].strip()
            nxt = {}
            for k, src in pending.items():
                why = check(src, got.get(k, ""))
                if why:
                    nxt[k] = src
                    out["fails"][k] = why
                else:
                    out["texts"][k] = got[k]
                    out["fails"].pop(k, None)
            pending = nxt
    out["elapsed"] = round(time.time() - t0, 1)
    tin = sum((u or {}).get("prompt", 0) for u in out["usage"])
    tout = sum((u or {}).get("completion", 0) for u in out["usage"])
    log("[TR-Z1199] 조각 %d · 통과 %d · 실패 %d%s · 부름 %d · 토큰 (%d, %d) · %.1f초" % (
        len(items), len(out["texts"]), len(out["fails"]),
        (" (" + ",".join(sorted(set(out["fails"].values()))) + ")") if out["fails"] else "",
        len(out["usage"]), tin, tout, out["elapsed"]))
    return out


# ── 한눈에 보기 그림 자료(JSON) — 글 칸만 옮기고 모양·종류·원문 근거(q)는 그대로 ─────────────────
_VIZ_SKIP = {"kind", "type", "sure", "from", "to", "q", "headline_q", "who", "due"}   # 이름·날짜(기한)도 그대로


def viz_items(viz) -> tuple:
    """그림 자료 → ({"v1": 한국어, …}, {"v1": 경로, …}) · 원문 근거(q)는 옮기지 않는다(근거 찾기는 원문에서)."""
    items, paths = {}, {}

    def walk(o, path):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in _VIZ_SKIP:
                    continue
                walk(v, path + [k])
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, path + [i])
        elif isinstance(o, str) and o.strip():
            key = "v%d" % (len(items) + 1)
            items[key] = o
            paths[key] = list(path)

    walk(viz, [])
    return items, paths


def viz_apply(viz, paths: dict, texts: dict):
    """옮긴 글을 같은 자리에 넣은 사본 · 흐름 고리(from·to)는 구역 이름을 옮긴 대로 따라간다 · 못 옮긴 칸은 원문 그대로."""
    v = json.loads(json.dumps(viz, ensure_ascii=False))
    zone = {}
    for key, path in paths.items():
        if key not in texts:
            continue
        o = v
        for p in path[:-1]:
            o = o[p]
        old = o[path[-1]]
        o[path[-1]] = texts[key]
        if len(path) == 4 and path[0] == "flow" and path[1] == "zones" and path[3] == "name":
            zone[old] = texts[key]
    lp = ((v.get("flow") or {}).get("loop") or {}) if isinstance(v, dict) else {}
    for k in ("from", "to"):
        if isinstance(lp, dict) and lp.get(k) in zone:
            lp[k] = zone[lp[k]]
    return v


def translate_parts(parts: dict, log=print) -> dict:
    """main 이 넘긴 조각(title · summary · dec:N · act:N · viz) → translate() 결과 모양 그대로(viz 는 JSON 글로 묶어 돌려줌)."""
    plain = {k: t for k, t in parts.items() if k != "viz"}
    viz_src = parts.get("viz")
    vitems, vpaths, viz_obj = {}, {}, None
    if viz_src:
        try:
            viz_obj = json.loads(viz_src)
            vitems, vpaths = viz_items(viz_obj)
        except Exception:
            viz_obj = None
    allitems = dict(plain)
    allitems.update({"viz#" + k: t for k, t in vitems.items()})
    res = translate(allitems, log=log)
    out = {"texts": {k: t for k, t in res["texts"].items() if not k.startswith("viz#")},
           "fails": {k: w for k, w in res["fails"].items() if not k.startswith("viz#")},
           "usage": res["usage"], "model": res["model"], "elapsed": res["elapsed"]}
    if viz_obj is not None:
        vt = {k[4:]: t for k, t in res["texts"].items() if k.startswith("viz#")}
        nfail = sum(1 for k in res["fails"] if k.startswith("viz#"))
        if vt or not vitems:
            out["texts"]["viz"] = json.dumps(viz_apply(viz_obj, vpaths, vt), ensure_ascii=False)
        else:
            out["fails"]["viz"] = "viz"
        out["viz_fail"] = nfail
    return out
