# -*- coding: utf-8 -*-
"""KNK 메신저 — 공휴일 달력 데이터 생성기 (한국·베트남).

용도: static/holidays_kr_vn.json 을 생성/갱신한다.
      이 JSON 은 공용 KNK 달력(date picker)이 K(한국)·V(베트남) 공휴일 배지를 찍는 데 쓴다.
      서버 런타임은 이 라이브러리를 쓰지 않는다(사전 생성 방식) → 컨테이너 무변경.

실행:  py deploy/gen_holidays.py            (기본 2025~2032)
       py deploy/gen_holidays.py 2026 2035  (연도 범위 지정)

준비:  py -m pip install holidays
갱신주기: 매년 1회(연말) 권장 — 범위를 앞으로 밀어 재생성 후 배포.

참고:  음력 명절(설날·추석/Tết)·대체공휴일·Nghỉ bù 는 라이브러리가 자동 계산.
       대체공휴일 명칭에 '대체'(KR) / 'bù'(VN) 가 들어가면 달력에서 점선 배지로 표시.
"""
import sys, io, json, os

def main():
    try:
        import holidays
    except ImportError:
        print("holidays 미설치 — 'py -m pip install holidays' 후 다시 실행")
        sys.exit(1)

    y0 = int(sys.argv[1]) if len(sys.argv) > 1 else 2025
    y1 = int(sys.argv[2]) if len(sys.argv) > 2 else 2032
    years = list(range(y0, y1 + 1))

    kr, vn = {}, {}
    for d, name in holidays.KR(years=years, language="ko").items():
        if "제헌절" in name:          # 2008년부터 공휴일 아님 → 제외
            continue
        kr[d.isoformat()] = name
    for y in years:                   # 근로자의 날(라이브러리 미포함) 추가
        kr.setdefault("%d-05-01" % y, "근로자의 날")
    for d, name in holidays.VN(years=years).items():
        vn[d.isoformat()] = name

    out = {
        "generated_for_years": [years[0], years[-1]],
        "kr": dict(sorted(kr.items())),
        "vn": dict(sorted(vn.items())),
    }
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "..", "static", "holidays_kr_vn.json")
    with io.open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=0)
    print("저장:", os.path.normpath(path))
    print("  KR %d개 · VN %d개 · 범위 %d~%d" % (len(kr), len(vn), years[0], years[-1]))


if __name__ == "__main__":
    main()
