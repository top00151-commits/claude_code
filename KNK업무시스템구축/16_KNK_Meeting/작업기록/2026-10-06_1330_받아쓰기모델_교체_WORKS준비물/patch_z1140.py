# -*- coding: utf-8 -*-
"""z1140 — 회의록 받아쓰기 모델을 이음과 같은 것으로 (대표 지시 2026-10-06)

발단(대표): 「녹음 파일을 너무 잘못 분석을 한 것 같아.. 이건 교정 사전을 사용한다고 해서 해결될 사항은 아닌 것 같아」
실측(같은 녹음 5분을 네 가지로 받아써 비교 · 회의 53 커넥터to커넥터):
  · 🔴 지금 방식(whisper-1)은 **회의 앞 20초를 통째로 빠뜨렸다**
  · 코그넥스→「코고넥스」 · 동글→「동굴」 · OKNG→「OK 엔지」 · 2D→「3D」 · 기술적으로→「교수적으로」 …
  · 새 모델(gpt-transcribe)은 그 낱말을 거의 다 맞히고 **더 빠르다**(15초→8~10초) · 값도 더 싸다(이음 기록)
  · 🔎 언어 지정(ko)·힌트 낱말·소리 품질(96kbps)은 **효과를 증명하지 못해 넣지 않는다**
    (특히 언어 지정은 베트남 직원 52명 회의를 한국어로 강제할 위험이 있어 뺀다)

바꾸는 것 (app/ai_client.py 1곳 — `ai_transcribe`)
  · 모델 = 환경변수 `KNK_WORKS_STT_MODEL`(기본 `gpt-transcribe`)
  · 실패하면 `KNK_WORKS_STT_FALLBACK`(기본 `whisper-1`)로 **자동으로 한 번 더** 시도
  · 신형/구형 호출법이 다르다 — 신형: `response_format="json"` + 언어는 `extra_body.languages`(복수) /
    구형: `language`(단수). 🔴 구형에 지시문(prompt)을 주면 결과에 튀어나오므로 둘 다 안 준다.
  · 🔧 되돌리기 = 컨테이너 환경변수 `KNK_WORKS_STT_MODEL=whisper-1` 한 줄

사용: python patch_z1140.py <ai_client.py 경로>
"""
import io
import os
import sys

OLD = '''def ai_transcribe(audio_path: str, lang: str = "") -> tuple[bool, str]:
    """음성 파일 → 텍스트 (OpenAI Whisper `whisper-1`).
    audio_path: 디스크 경로(webm/m4a/mp4/mp3/wav 등). lang: 'ko'/'vi'/'en' 또는 ''(자동감지).
    반환 (성공, 텍스트 또는 오류메시지). 호출부는 transcribe_available() 로 먼저 확인 권장.
    Whisper 는 OpenAI 전용 — claude만 설정돼 있으면 (False, 사유) 반환."""
    key = _key_for("openai")
    if not _OPENAI_OK:
        return (False, "음성→글자: openai SDK 미설치 (pip install openai)")
    if not key:
        return (False, "음성→글자: OpenAI 키가 필요합니다(현재 미설정/무효). 관리자 → AI 설정에서 등록하세요.")
    if not audio_path or not os.path.exists(audio_path):
        return (False, "음성 파일을 찾을 수 없습니다.")
    try:
        client = openai.OpenAI(api_key=key, timeout=300)
        kwargs: dict[str, Any] = {"model": "whisper-1"}
        if lang in ("ko", "vi", "en"):
            kwargs["language"] = lang
        with open(audio_path, "rb") as f:
            resp = client.audio.transcriptions.create(file=f, **kwargs)
        text = getattr(resp, "text", "") or ""
        return (True, text.strip())
    except Exception as e:
        return (False, f"음성→글자 오류(openai): {e}")'''

NEW = '''# ── 음성 → 글자 모델 (z1140 · 대표 지시 2026-10-06) ─────────────────────────
#  같은 녹음 5분을 나란히 받아쓴 실측(회의 53):
#    whisper-1 은 **회의 앞 20초를 통째로 빠뜨렸고**, 코그넥스→「코고넥스」·동글→「동굴」·
#    OKNG→「OK 엔지」·2D→「3D」·기술적으로→「교수적으로」 처럼 전문용어를 줄줄이 틀렸다.
#    gpt-transcribe 는 그 낱말을 거의 다 맞히고 더 빠르다(15초→8~10초). 값도 더 싸다.
#    이음(메신저)은 2026-07-31 대표 지시로 이미 바꿔 석 달째 쓰고 있다.
#  🔎 같이 재 봤지만 **넣지 않은 것**: 언어 지정(ko)·힌트 낱말·소리 품질 올리기 —
#    이 표본에서 이득을 증명하지 못했다. 특히 언어 지정은 베트남 직원 회의를 한국어로
#    강제할 위험이 있어 뺐다(호출자가 lang 을 주면 그때만 쓴다).
#  🔧 되돌리기: 환경변수 KNK_WORKS_STT_MODEL=whisper-1 한 줄.
STT_MODEL = (os.environ.get("KNK_WORKS_STT_MODEL") or "gpt-transcribe").strip()
STT_FALLBACK_MODEL = (os.environ.get("KNK_WORKS_STT_FALLBACK") or "whisper-1").strip()


def _stt_is_new_model(model: str) -> bool:
    """신형 전사 모델(gpt-transcribe·gpt-4o-transcribe…)인가.
    신형: 언어는 `extra_body.languages`(복수) · 응답형식은 json 만.
    구형(whisper-1): `language`(단수) · 🔴 prompt 는 '앞서 받아쓴 글' 취급이라 지시문을 주면 결과에 튀어나온다."""
    return (model or "").lower().startswith("gpt")


def ai_transcribe(audio_path: str, lang: str = "") -> tuple[bool, str]:
    """음성 파일 → 텍스트. 기본 `gpt-transcribe`, 실패하면 `whisper-1` 로 한 번 더(z1140).
    audio_path: 디스크 경로(webm/m4a/mp4/mp3/wav 등). lang: 'ko'/'vi'/'en' 또는 ''(자동감지).
    반환 (성공, 텍스트 또는 오류메시지). 호출부는 transcribe_available() 로 먼저 확인 권장.
    OpenAI 전용 — claude만 설정돼 있으면 (False, 사유) 반환."""
    key = _key_for("openai")
    if not _OPENAI_OK:
        return (False, "음성→글자: openai SDK 미설치 (pip install openai)")
    if not key:
        return (False, "음성→글자: OpenAI 키가 필요합니다(현재 미설정/무효). 관리자 → AI 설정에서 등록하세요.")
    if not audio_path or not os.path.exists(audio_path):
        return (False, "음성 파일을 찾을 수 없습니다.")
    models = [STT_MODEL] + ([STT_FALLBACK_MODEL] if (STT_FALLBACK_MODEL and STT_FALLBACK_MODEL != STT_MODEL) else [])
    client = openai.OpenAI(api_key=key, timeout=300)
    last = ""
    for i, model in enumerate(models):
        kwargs: dict[str, Any] = {"model": model}
        if _stt_is_new_model(model):
            kwargs["response_format"] = "json"        # 신형은 text/verbose_json/srt/vtt 미지원
            if lang in ("ko", "vi", "en"):
                kwargs["extra_body"] = {"languages": [lang]}
        else:
            if lang in ("ko", "vi", "en"):
                kwargs["language"] = lang             # 구형은 단수
        try:
            with open(audio_path, "rb") as f:         # ⚠ 스트림은 시도마다 새로 연다(한 번 읽으면 다시 못 읽는다)
                resp = client.audio.transcriptions.create(file=f, **kwargs)
            text = (getattr(resp, "text", "") or "").strip()
            if i > 0:
                print(f"[STT] {models[0]} 실패 → {model} 로 받아씀")
            return (True, text)
        except Exception as e:
            last = f"{model}: {e}"
            print(f"[STT] {model} 실패: {str(e)[:160]}")
    return (False, f"음성→글자 오류(openai): {last}")'''


def main():
    if len(sys.argv) < 2:
        print("사용: python patch_z1140.py <ai_client.py 경로>")
        return 2
    p = sys.argv[1]
    if not os.path.exists(p):
        print("없는 파일:", p)
        return 2
    s = io.open(p, encoding="utf-8").read()
    if "STT_FALLBACK_MODEL" in s:
        print("이미 z1140 이 들어 있음 — 건너뜀")
        return 0
    n = s.count(OLD)
    if n != 1:
        print("자리 못 찾음(%d개) — 운영본이 달라졌는지 확인할 것" % n)
        return 3
    s = s.replace(OLD, NEW, 1)
    data = s.encode("utf-8")          # 🔴 쓰기 전에 인코딩을 먼저 해 본다
    tmp = p + ".tmp_z1140"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, p)
    import py_compile
    py_compile.compile(p, doraise=True)
    print("적용: 받아쓰기 모델 gpt-transcribe(+실패 시 whisper-1) · 문법 통과 ·", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
