# -*- coding: utf-8 -*-
"""🗣 통역 대조 (z1196 · 대표 2026-10-27 「통역이 제대로 통역을 했을까?」 → 화면 시안 → 「이대로 만들어 회귀 통과하면 올리기」)

회의록·음성 메모의 녹음을 **말한 사람을 나눠** 다시 받아쓰고(화자 구분 받아쓰기 모델 · 한 요청 23분 한도 → 10분 조각 ·
앞 조각 목소리를 「아는 화자」로 넘겨 조각끼리 이름을 맞춤), 빅터AI 가 통역의 말과 원말을 **독립 번역으로 대조**해
「들어 볼 자리」 표(JSON 한 덩이)를 만든다. 받아쓴 글·정리(ai_client 의 정리 지시문)는 손대지 않는다 — 추가 화면의 자료일 뿐.

  · 2026-10-27 37분 녹음 실측(세션 16 작업기록 1643·1733): 조각 4 · 발화 517 · 화자 8 · 대조 줄 122 → 항목 57 · 받아쓰기 약 14분
  · 🔴 지시문 둘(SYSTEM_CMP 대조 · SYSTEM_BLK 묶음 판정)은 그 실측에서 쓴 글 **그대로** — 고치면 결과가 달라진다(실증된 지시문 불변)
  · 기록(print)에는 숫자만 — 회의 내용은 안 찍는다 · AI 키는 ai_client 가 가진 것(값 안 찍음) · 공급사 설정과 무관하게 OpenAI 키가 있어야 한다
  · 보기·만들기 권한은 main.py(대표·임원) — 여기는 계산만 · 시험은 _diarize_call · _chat_json 두 자리만 가짜로 바꾼다
"""
import base64
import io
import json
import math
import os
import re
import shutil
import subprocess
import time

from . import ai_client

try:
    import openai
except ImportError:          # pragma: no cover — 운영엔 있다(받아쓰기가 쓴다)
    openai = None

DIARIZE_MODEL = (os.environ.get("KNK_WORKS_DIARIZE_MODEL") or "gpt-4o-transcribe-diarize").strip()
CMP_MODELS = [m.strip() for m in (os.environ.get("KNK_WORKS_INTERP_MODELS") or "gpt-4.1,gpt-4o,gpt-4o-mini").split(",") if m.strip()]
CHUNK_SEC = 600.0            # 10분 조각(한 요청 1,400초 한도 안 · 실측과 같은 크기)
OVERLAP_SEC = 3.0            # 조각 사이 겹침 — 겹친 자리는 앞 조각 것을 남긴다
WIN, CTX, TAIL = 240.0, 45.0, 30.0     # 대조 창 4분 · 앞 45초 흐름 참고 · 뒤 30초 통역 이어짐
GAP, MAXLEN = 20.0, 90.0               # 「통역 안 함」 조각 묶기 — 20초 안 이어짐 · 한 묶음 90초까지
DIARIZE_TIMEOUT = 900
CMP_TIMEOUT = 600
VI = set("ăâđêôơưĂÂĐÊÔƠƯàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ")
LANG_KO = {"ko": "한국어", "vi": "베트남어", "ko+vi": "섞임", "?": "?"}

SYSTEM_CMP = (
    "당신은 한국어·베트남어에 모두 능통한 통역 품질 검토자입니다. 회의 녹음을 말한 사람별로 받아쓴 글(기계 받아쓰기 · 틀린 글자가 있을 수 있음)을 받습니다.\n"
    "회의 구조: 한국 측은 한국어, 베트남 측은 베트남어로 말하고, 통역(화자 %s 로 짐작 · 한국어·베트남어 둘 다 씀)이 양쪽으로 옮깁니다. "
    "화자 표시는 기계가 목소리로 나눈 것이라 틀릴 수 있습니다(비슷한 목소리는 한 표시로 묶임). 그러니 **언어와 내용**으로 판단하세요.\n\n"
    "대조 단위(한 줄) = 「통역이 아닌 사람의 원말」 하나(또는 통역이 한꺼번에 옮긴 연속 원말 묶음) + 그것을 통역이 옮긴 말.\n"
    "- VI→KO: 베트남어 원말(베트남 측이 새로 한 말 — 앞 한국어를 옮긴 것이 아닌 말) ↔ 그 뒤에 나오는 통역의 **한국어**. "
    "AI_독립번역 = 원말을 당신이 직접 한국어로 번역.\n"
    "- KO→VI: 한국어 원말(한국 측이 한 말 — 앞 베트남어를 옮긴 것이 아닌 말) ↔ 그 뒤에 나오는 통역의 **베트남어**. "
    "AI_독립번역 = 통역의 베트남어를 당신이 한국어로 되돌려 번역(통역 안 함이면 원말을 베트남어로 번역).\n"
    "- 🔴 통역 자신의 말(앞 발화를 옮긴 것)은 원말로 쓰지 말고 「통역한_말」에만 씁니다. 베트남어 발화가 바로 앞 한국어의 번역이면 통역의 말이고, "
    "새 내용이면 베트남 측 원말입니다(화자 표시가 통역으로 돼 있어도 내용이 새 것이면 원말로). 한국어도 같은 방식.\n"
    "- 판정: 같음 / 일부 빠짐(원말의 일부가 통역에 없음) / 보탬(원말에 없는 내용이 통역에 있음) / 뜻 바뀜(숫자·조건·주어·긍정부정·책임이 다름) / "
    "통역 안 함(뒤에 옮긴 말이 없음) / 확인 불가(받아쓰기가 깨져 판단 못 함).\n"
    "- 성격: 질문 / 지시·요청 / 답변·설명 / 결정 / 내부 논의(같은 쪽끼리 한 말 — 옮길 필요 없음) / 잡담·맞장구.\n"
    "- 심각도: 2 = 숫자·조건·결정·책임·일정이 달라지거나, 베트남 측의 답변·설명·질문이 한국어로 전달되지 않음, 또는 베트남 측에게 한 질문·지시가 베트남어로 전달되지 않음 · "
    "1 = 세부·뉘앙스 빠짐, 가벼운 보탬 · 0 = 같음, 또는 내부 논의·잡담을 안 옮긴 것(정상).\n"
    "- 까닭: 무엇이 어떻게 다른지 한국어 한두 문장(통역 안 함이면 무엇이 전달 안 됐는지). 원말·통역한_말은 받아쓴 글 그대로(고치지 말 것). 지어내지 말 것.\n"
    "- 받아쓰기가 두 언어 글자로 뒤섞여 깨진 발화는 「확인 불가」 · 까닭에 「받아쓰기 깨짐」.\n"
    "- 「흐름 참고」 발화는 맥락으로만(줄 만들지 말 것) · 「뒤 30초」 발화는 통역한_말로만.\n"
    "- 시각은 발화 앞 대괄호의 「분:초」 글을 그대로 적습니다(예: \"3:39\").\n"
    "출력은 오직 JSON 한 개: {\"rows\": [{\"시작\": \"분:초\", \"끝\": \"분:초\", \"방향\": \"VI→KO\"|\"KO→VI\", \"원말_화자\": \"A\", \"원말\": \"…\", "
    "\"통역_시작\": \"분:초\" 또는 \"\", \"통역한_말\": \"…\", \"AI_독립번역\": \"…\", \"판정\": \"…\", \"성격\": \"…\", \"심각도\": 0, \"까닭\": \"…\"}]}"
)
SYSTEM_BLK = (
    "당신은 한국어·베트남어에 능통한 통역 품질 검토자입니다. 회의(한국 측 한국어 · 베트남 측 베트남어 · 통역 화자 %s 가 양쪽으로 옮김)에서 "
    "**옮겨지지 않은 말 묶음**을 받습니다. 묶음마다 아래를 JSON 으로 답하세요.\n"
    "- 요지: 그 묶음에서 한 말의 요지를 한국어 1~2문장으로(베트남어면 번역해서 · 받아쓰기가 깨졌으면 알 수 있는 만큼만 · 지어내지 말 것).\n"
    "- 대상: 「베트남 측에게 한 말」 / 「한국 측끼리 한 말」 / 「통역과 베트남 측끼리 한 말」 / 「모름」 — 앞뒤 흐름으로 판단.\n"
    "- 들었어야: 그 말이 상대쪽에 전달됐어야 했는가 — 「예」(질문·답변·수치·조건·결정·요청) / 「아니오」(같은 쪽끼리 의논·맞장구·잡담·되풀이) / 「모름」.\n"
    "- 심각도: 2 = 들었어야 하는 말이 안 전달됨(특히 베트남 측의 답변·수치·조건이 한국어로 안 옴, 또는 베트남 측에게 한 질문·지시가 베트남어로 안 감) · "
    "1 = 모름/부분 · 0 = 같은 쪽끼리 한 말·잡담(안 옮겨도 정상).\n"
    "- 까닭: 한 문장.\n"
    "출력: {\"items\": [{\"id\": 번호, \"요지\": \"…\", \"대상\": \"…\", \"들었어야\": \"…\", \"심각도\": 0, \"까닭\": \"…\"}]}"
)


class InterpError(Exception):
    """사람에게 보여 줄 까닭(한국어) — 회의 내용은 넣지 않는다."""


def available() -> bool:
    """만들 수 있나 — OpenAI SDK + OpenAI 키(ai_client 와 같은 판정) + ffmpeg·ffprobe."""
    return bool(ai_client.transcribe_available() and shutil.which("ffmpeg") and shutil.which("ffprobe"))


def _client(timeout):
    """OpenAI 클라이언트(키는 ai_client 에서 · 값 안 찍음). 공급사 설정이 Claude 여도 OpenAI 키가 있으면 된다(받아쓰기와 같음)."""
    key = ai_client._key_for("openai")
    if not key or openai is None:
        return None
    return openai.OpenAI(api_key=key, timeout=timeout, max_retries=1)


# ── 시험이 가짜로 바꾸는 두 자리 ──────────────────────────────────────────
def _diarize_call(client, path, names=None, refs=None):
    kw = dict(model=DIARIZE_MODEL, response_format="diarized_json", chunking_strategy="auto")
    if names:
        kw["known_speaker_names"] = names
        kw["known_speaker_references"] = refs
    with open(path, "rb") as f:
        return client.audio.transcriptions.create(file=f, **kw)


def _chat_json(client, model, system, user):
    r = client.chat.completions.create(model=model, temperature=0, response_format={"type": "json_object"},
                                       messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
    u = getattr(r, "usage", None)
    return (json.loads(r.choices[0].message.content or "{}"),
            ({"prompt": getattr(u, "prompt_tokens", 0), "completion": getattr(u, "completion_tokens", 0)} if u is not None else None))


# ── 작은 도우미 ──────────────────────────────────────────────────────────
def lang_of(t):
    h = sum(1 for ch in t if "가" <= ch <= "힣")
    v = sum(1 for ch in t if ch in VI)
    return "ko" if h and not v else "vi" if v and not h else "ko+vi" if h and v else "?"


def mmss(sec):
    sec = int(round(float(sec)))
    return "%d:%02d" % (sec // 60, sec % 60)


def to_sec(v, default=None):
    """「3:39」·「03:39」·숫자(초) → 초. 못 풀면 default."""
    if v is None or v == "":
        return default
    if isinstance(v, (int, float)):
        return float(v)
    m = re.match(r"^\s*(\d{1,3}):(\d{2})\s*$", str(v))
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    try:
        return float(str(v).strip())
    except ValueError:
        return default


def _sev(r):
    try:
        return max(0, min(2, int(r.get("심각도") or 0)))
    except (TypeError, ValueError):
        return 0


def _ffdur(path):
    out = subprocess.run([shutil.which("ffprobe"), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True, timeout=120).stdout.strip()
    try:
        return float(out or 0)
    except ValueError:
        return 0.0


def _cut(src, dst, ss, t, fmt="mp3"):
    args = [shutil.which("ffmpeg"), "-hide_banner", "-nostdin", "-loglevel", "error", "-y", "-ss", "%.2f" % ss, "-t", "%.2f" % t,
            "-i", src, "-vn", "-ac", "1", "-ar", "16000"]
    args += (["-c:a", "libmp3lame", "-b:a", "64k"] if fmt == "mp3" else ["-c:a", "pcm_s16le"])
    subprocess.run(args + [dst], check=True, capture_output=True, timeout=1800)


def _norm(resp, offset=0.0):
    out = []
    for s in (getattr(resp, "segments", None) or []):
        d = s.model_dump() if hasattr(s, "model_dump") else dict(s)
        out.append({"start": round(float(d.get("start") or 0) + offset, 2), "end": round(float(d.get("end") or 0) + offset, 2),
                    "speaker": str(d.get("speaker") or "?"), "text": (d.get("text") or "").strip()})
    return out


def _usage_of(resp):
    u = getattr(resp, "usage", None)
    if u is None:
        return None
    return u.model_dump() if hasattr(u, "model_dump") else (dict(u) if isinstance(u, dict) else None)


def _stats(segs):
    by = {}
    for s in segs:
        b = by.setdefault(s["speaker"], {"초": 0.0, "첫": None})
        b["초"] += s["end"] - s["start"]
        if b["첫"] is None:
            b["첫"] = s["start"]
    return by


# ── 1. 화자 구분 받아쓰기(조각 · 아는 화자) ─────────────────────────────────
def diarize(disk, workdir, log=print, progress=None):
    """녹음 → 16kHz 모노 mp3 → 10분 조각 → 화자 구분 받아쓰기. 반환 (segments, duration, usages, n_chunks)."""
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        raise InterpError("서버에 음성 도구(ffmpeg)가 없어 통역 대조를 만들지 못했습니다 — 관리자에게 알려 주세요.")
    client = _client(DIARIZE_TIMEOUT)
    if client is None:
        raise InterpError("빅터AI(OpenAI) 키가 없어 통역 대조를 만들지 못했습니다.")
    os.makedirs(workdir, exist_ok=True)
    full = os.path.join(workdir, "full_16k.mp3")
    if progress:
        progress("녹음 준비")
    try:
        subprocess.run([shutil.which("ffmpeg"), "-hide_banner", "-nostdin", "-loglevel", "error", "-y", "-i", disk, "-vn", "-ac", "1",
                        "-ar", "16000", "-c:a", "libmp3lame", "-b:a", "64k", full], check=True, capture_output=True, timeout=1800)
    except subprocess.CalledProcessError as e:
        tail = (e.stderr or b"").decode("utf-8", "replace").strip().splitlines()[-1:]
        raise InterpError("녹음 파일을 읽지 못했습니다(손상됐거나 읽을 수 없는 형식) — " + (tail[0][:120] if tail else "ffmpeg 오류"))
    dur = _ffdur(full)
    if dur <= 1.0:
        raise InterpError("녹음 길이를 알 수 없거나 너무 짧습니다.")
    n = max(1, int(math.ceil(dur / CHUNK_SEC)))
    piece = dur / n
    segs, usages, names, refs = [], [], [], []
    for i in range(n):
        ss = max(0.0, i * piece - (OVERLAP_SEC if i else 0))
        t = piece + (OVERLAP_SEC if i else 0) + (OVERLAP_SEC if i < n - 1 else 0)
        p = os.path.join(workdir, "part%02d.mp3" % i)
        _cut(full, p, ss, t)
        if progress:
            progress("받아쓰기 %d/%d" % (i + 1, n))
        t1 = time.time()
        resp = _diarize_call(client, p, names or None, refs or None)
        part = _norm(resp, ss)
        usages.append(_usage_of(resp))
        log("[INTERP-Z1196] 받아쓰기 조각 %d/%d(%.0f~%.0f초) · %.0f초 걸림 · 발화 조각 %d · 화자 %d" % (
            i + 1, n, ss, ss + t, time.time() - t1, len(part), len({x["speaker"] for x in part})))
        if i == 0 and n > 1:
            #  첫 조각에서 많이 말한 화자 최대 4명 — 4~10초짜리 한 덩이 목소리를 「아는 화자」로(이름이 조각끼리 이어진다)
            by = _stats(part)
            for spk, _b in sorted(by.items(), key=lambda kv: -kv[1]["초"])[:4]:
                best = max((s for s in part if s["speaker"] == spk and 4 <= (s["end"] - s["start"]) <= 10),
                           key=lambda s: s["end"] - s["start"], default=None)
                if not best:
                    continue
                wav = os.path.join(workdir, "ref_%s.wav" % re.sub(r"[^A-Za-z0-9_]", "_", spk))
                _cut(full, wav, best["start"], min(8.0, best["end"] - best["start"]), fmt="wav")
                names.append(spk)
                refs.append("data:audio/wav;base64," + base64.b64encode(open(wav, "rb").read()).decode("ascii"))
            log("[INTERP-Z1196] 아는 화자로 넘김 %d명" % len(names))
        cutoff = segs[-1]["end"] if segs else -1     # 겹친 자리는 앞 조각 것을 남긴다
        segs.extend(s for s in part if s["start"] >= cutoff)
    segs.sort(key=lambda s: (s["start"], s["end"]))
    return segs, dur, usages, n


# ── 2. 발화 묶기 · 역할 ─────────────────────────────────────────────────────
def build_turns(segs):
    turns = []
    for s in segs:
        if not s["text"]:
            continue
        if turns and turns[-1]["speaker"] == s["speaker"] and s["start"] - turns[-1]["end"] <= 1.0 and len(turns[-1]["text"]) < 400:
            turns[-1]["end"] = s["end"]
            turns[-1]["text"] = (turns[-1]["text"] + " " + s["text"]).strip()
        else:
            turns.append({"start": s["start"], "end": s["end"], "speaker": s["speaker"], "text": s["text"]})
    for t in turns:
        t["lang"] = lang_of(t["text"])
    return turns


def roles(turns):
    """화자별 통계 + 통역 짐작(한국어·베트남어 둘 다 20% 넘게 쓰는 화자 중 가장 많이 말한 사람). 반환 (by, interp)."""
    by = {}
    for t in turns:
        b = by.setdefault(t["speaker"], {"초": 0.0, "ko": 0, "vi": 0, "ko+vi": 0, "?": 0, "첫": t["start"], "발화": 0})
        b["초"] += t["end"] - t["start"]
        b[t["lang"]] += len(t["text"])
        b["발화"] += 1
    if not by:
        raise InterpError("받아쓴 말이 없습니다 — 녹음에 알아들을 말이 거의 없습니다.")
    cands = []
    for k, b in by.items():
        tot = max(1, b["ko"] + b["vi"] + b["ko+vi"])
        ko, vi = (b["ko"] + b["ko+vi"] / 2) / tot, (b["vi"] + b["ko+vi"] / 2) / tot
        b["ko%"], b["vi%"] = round(100 * ko), round(100 * vi)
        if ko >= 0.2 and vi >= 0.2:
            cands.append((b["초"], k))
    interp = max(cands)[1] if cands else max(by, key=lambda k: min(by[k]["ko"], by[k]["vi"]))
    for k, b in by.items():
        b["역할"] = ("통역(추정)" if k == interp else "두 언어 섞임(두 사람이 묶였을 수 있음)" if (b["vi%"] >= 20 and b["ko%"] >= 20)
                    else ("베트남 측(추정)" if b["vi%"] > b["ko%"] else "한국 측(추정)"))
    return by, interp


def _fmt_turn(t):
    return "[%s~%s] 화자 %s (%s): %s" % (mmss(t["start"]), mmss(t["end"]), t["speaker"], LANG_KO[t["lang"]], t["text"])


def _ask(client, system, user, used, usages, log, what):
    """모델 차례대로(처음 된 모델을 그 뒤로 씀). 반환 (dict, used_model)."""
    last = ""
    for m in ([used] if used else CMP_MODELS):
        try:
            t1 = time.time()
            res, u = _chat_json(client, m, system, user)
            if u:
                usages.append(u)
            log("[INTERP-Z1196] %s · %.0f초 · 토큰 %s" % (what, time.time() - t1, (u["prompt"], u["completion"]) if u else "?"))
            return res, m
        except Exception as e:   # 다음 모델로 — 마지막까지 안 되면 까닭을 올린다
            last = "%s: %s" % (m, str(e)[:160])
            log("[INTERP-Z1196] %s · 모델 %s 실패 → 다음" % (what, m))
    raise InterpError("빅터AI 대조에 실패했습니다 — " + last)


# ── 3. 대조(4분 창) · 4. 「통역 안 함」 묶음 판정 ────────────────────────────
def compare(turns, interp, dur, log=print, progress=None):
    client = _client(CMP_TIMEOUT)
    if client is None:
        raise InterpError("빅터AI(OpenAI) 키가 없어 통역 대조를 만들지 못했습니다.")
    system = SYSTEM_CMP % interp
    rows_all, usages, used = [], [], None
    nwin = max(1, int(math.ceil(dur / WIN)))
    w0, wi = 0.0, 0
    while w0 < dur:
        w1 = min(dur, w0 + WIN)
        wi += 1
        if progress:
            progress("대조 %d/%d" % (wi, nwin))
        ctx = [t for t in turns if w0 - CTX <= t["start"] < w0]
        body = [t for t in turns if w0 <= t["start"] < w1]
        tail = [t for t in turns if w1 <= t["start"] < w1 + TAIL]
        if body:
            user = ("※ 녹음 위치는 분:초. 판정 구간 = %s ~ %s 에서 시작하는 원말.\n\n" % (mmss(w0), mmss(w1))
                    + ("[흐름 참고 — 줄 만들지 말 것]\n" + "\n".join(_fmt_turn(t) for t in ctx) + "\n\n" if ctx else "")
                    + "[판정 구간]\n" + "\n".join(_fmt_turn(t) for t in body)
                    + ("\n\n[뒤 30초 — 통역이 이어지면 통역한_말로만 쓸 것]\n" + "\n".join(_fmt_turn(t) for t in tail) if tail else ""))
            res, used = _ask(client, system, user, used, usages, log, "대조 창 %d/%d(%d발화)" % (wi, nwin, len(body)))
            rows = res.get("rows") or []
            for r in rows:
                if not isinstance(r, dict):
                    continue
                r["_sec"] = to_sec(r.get("시작"), w0)
                r["_isec"] = to_sec(r.get("통역_시작"), None)
                rows_all.append(r)
        w0 = w1
    seen, rows = set(), []
    for r in sorted(rows_all, key=lambda r: (r["_sec"], r.get("방향") or "")):
        k = (round(r["_sec"]), r.get("방향"), (r.get("원말") or "")[:30])
        if k in seen:
            continue
        seen.add(k)
        rows.append(r)
    #  「통역 안 함」 조각을 시간 묶음으로
    blocks = []
    for direction in ("VI→KO", "KO→VI"):
        cur = None
        for r in [x for x in rows if x.get("방향") == direction and x.get("판정") == "통역 안 함"]:
            if cur and r["_sec"] - cur["end"] <= GAP and r["_sec"] - cur["start"] <= MAXLEN:
                cur["rows"].append(r)
                cur["end"] = r["_sec"]
            else:
                cur = {"dir": direction, "start": r["_sec"], "end": r["_sec"], "rows": [r]}
                blocks.append(cur)
    for i, b in enumerate(blocks, 1):
        b["id"] = i
        b["원말"] = " / ".join((r.get("원말") or "").strip() for r in b["rows"])
        b["번역"] = " / ".join((r.get("AI_독립번역") or "").strip() for r in b["rows"])
        b["화자"] = ",".join(sorted({str(r.get("원말_화자")) for r in b["rows"]}))
        b["sev0"] = max(_sev(r) for r in b["rows"])
    judged = {}
    if blocks:
        system2 = SYSTEM_BLK % interp

        def ctx_lines(b):
            lo, hi = b["start"] - 25, b["end"] + 25
            return "\n".join("[%s~%s] 화자 %s (%s): %s" % (mmss(t["start"]), mmss(t["end"]), t["speaker"], LANG_KO[t["lang"]], t["text"][:220])
                             for t in turns if lo <= t["start"] <= hi)
        nb = int(math.ceil(len(blocks) / 8.0))
        for i in range(0, len(blocks), 8):
            batch = blocks[i:i + 8]
            if progress:
                progress("묶음 판정 %d/%d" % (i // 8 + 1, nb))
            user = "\n\n".join("### 묶음 %d · 방향 %s · %s~%s · 화자 %s\n[옮겨지지 않은 말] %s\n[앞뒤 흐름]\n%s" % (
                b["id"], b["dir"], mmss(b["start"]), mmss(b["end"]), b["화자"], b["원말"][:900], ctx_lines(b)) for b in batch)
            res, used = _ask(client, system2, user, used, usages, log, "묶음 판정 %d~%d" % (batch[0]["id"], batch[-1]["id"]))
            for it in (res.get("items") or []):
                if isinstance(it, dict):
                    judged[str(it.get("id"))] = it
    for b in blocks:
        j = judged.get(str(b["id"]), {})
        try:
            b["sev"] = max(0, min(2, int(j.get("심각도", b["sev0"]))))
        except (TypeError, ValueError):
            b["sev"] = b["sev0"]
        b["요지"], b["대상"], b["들었어야"], b["까닭"] = j.get("요지", ""), j.get("대상", "모름"), j.get("들었어야", "모름"), j.get("까닭", "")
    return rows, blocks, usages, used


# ── 5. 화면 자료(JSON) ───────────────────────────────────────────────────────
CAT_OF = {"뜻 바뀜": 1, "일부 빠짐": 1, "보탬": 1, "확인 불가": 4, "같음": 5}


def assemble(turns, by, interp, rows, blocks, dur, n_chunks, start_clock="", usage=None, elapsed=None, models=None):
    items = []
    for r in rows:
        if r.get("판정") == "통역 안 함":
            continue
        items.append({"kind": "row", "t": round(r["_sec"], 1), "cat": CAT_OF.get(r.get("판정"), 4), "dir": r.get("방향") or "",
                      "judge": r.get("판정") or "", "sev": _sev(r), "nature": r.get("성격") or "", "sp": str(r.get("원말_화자") or ""),
                      "src": r.get("원말") or "", "isec": (round(r["_isec"], 1) if r["_isec"] is not None else None),
                      "itxt": r.get("통역한_말") or "", "ai": r.get("AI_독립번역") or "", "why": r.get("까닭") or ""})
    for b in blocks:
        items.append({"kind": "block", "t": round(b["start"], 1), "t2": round(b["end"], 1), "cat": (2 if b["dir"] == "VI→KO" else 3), "dir": b["dir"],
                      "judge": "통역 안 함", "sev": b["sev"], "sp": b["화자"], "src": b["원말"], "ai": b["번역"], "gist": b["요지"],
                      "target": b["대상"], "should": b["들었어야"], "why": b["까닭"], "n": len(b["rows"])})
    items.sort(key=lambda x: (x["t"], x["cat"]))
    for i, it in enumerate(items, 1):
        it["id"] = i
    counts = {}
    for c in (1, 2, 3, 4, 5):
        xs = [x for x in items if x["cat"] == c]
        counts[str(c)] = [len(xs), sum(1 for x in xs if x["sev"] == 2)]
    return {
        "v": 1, "dur": round(dur, 1), "start_clock": start_clock or "", "n_turns": len(turns), "interp": interp, "chunks": n_chunks,
        "chunk_sec": int(CHUNK_SEC), "usage": usage or {}, "elapsed": elapsed or {}, "models": models or {},
        "speakers": [{"id": k, "role": b["역할"], "sec": round(b["초"]), "n": b["발화"], "ko": b["ko%"], "vi": b["vi%"], "first": round(b["첫"], 1)}
                     for k, b in sorted(by.items(), key=lambda kv: -kv[1]["초"])],
        "turns": [{"s": round(t["start"], 1), "e": round(t["end"], 1), "sp": t["speaker"], "lang": t["lang"], "t": t["text"]} for t in turns],
        "items": items, "counts": counts,
    }


def run(disk, workdir, start_clock="", log=print, progress=None):
    """끝까지 — 받아쓰기 → 발화·역할 → 대조 → 묶음 판정 → JSON. 임시 폴더는 끝나면 지운다. 실패는 InterpError(사람말)."""
    t0 = time.time()
    try:
        segs, dur, stt_usage, n = diarize(disk, workdir, log=log, progress=progress)
        t_stt = time.time() - t0
        turns = build_turns(segs)
        by, interp = roles(turns)
        log("[INTERP-Z1196] 발화 %d · 화자 %d · 통역 추정 = 화자 %s · 받아쓰기 %.0f초" % (len(turns), len(by), interp, t_stt))
        rows, blocks, cmp_usage, used = compare(turns, interp, dur, log=log, progress=progress)
        if progress:
            progress("정리")
        data = assemble(turns, by, interp, rows, blocks, dur, n, start_clock=start_clock,
                        usage={"stt": [u for u in stt_usage if u], "cmp": cmp_usage},
                        elapsed={"stt": round(t_stt), "all": round(time.time() - t0)},
                        models={"stt": DIARIZE_MODEL, "cmp": used or ""})
        log("[INTERP-Z1196] 끝 · 대조 줄 %d · 묶음 %d · 항목 %d · 전체 %.0f초" % (len(rows), len(blocks), len(data["items"]), time.time() - t0))
        return data
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
