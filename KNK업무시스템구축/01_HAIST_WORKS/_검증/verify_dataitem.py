# -*- coding: utf-8 -*-
"""배포될 **실제** project_bom.html 에서 품목 행 태그만 떼어내 험한 값으로 렌더 → 되읽기 시험.

옛 표기(data-item="...")와 새 표기(data-item='...')를 나란히 돌려 변별력을 확인한다.
"""
import html as H
import json
import re
import sys

from jinja2 import Environment

path = sys.argv[1]
src = re.sub(r"\{#.*?#\}", "", open(path, encoding="utf-8").read(), flags=re.S)
m = re.search(r"(<tr class=\"rowx.*?data-item=.*?>)", src, re.S)
tag_new = re.sub(r"\{\{ oldv.*?\}\}", "", m.group(1))
# 같은 태그를 옛 표기로 되돌린 것 (변별력 비교용)
tag_old = tag_new.replace("data-item='{{ it | tojson }}'",
                          'data-item="{{ it | tojson | e }}"')

print("실제 파일에서 떼어낸 줄 :", tag_new.strip().splitlines()[-1].strip())
print("변별력 비교용 옛 표기   :", tag_old.strip().splitlines()[-1].strip())

CASES = [
    ("큰따옴표",  {"id": 1, "status": "활성", "review_flag": 0, "buy_at": "KOR",
                   "part_no": 'BEARING 1/2" SHAFT', "part_name": "베어링", "maker": "NSK"}),
    ("홑따옴표",  {"id": 2, "status": "활성", "review_flag": 0, "buy_at": "",
                   "part_no": "O-RING 3'LONG", "part_name": "오링", "maker": "SMC"}),
    ("꺾쇠·앰퍼", {"id": 3, "status": "활성", "review_flag": 0, "buy_at": "VINA",
                   "part_no": "A<B>&C", "part_name": "브라켓", "maker": "MISUMI"}),
    ("평범한 값", {"id": 4, "status": "활성", "review_flag": 0, "buy_at": "KOR",
                   "part_no": "MSMF022L1S1", "part_name": "SERVO MOTOR", "maker": "PANASONIC"}),
    ("한글·물결", {"id": 5, "status": "활성", "review_flag": 0, "buy_at": "KOR",
                   "part_no": "MX-1", "part_name": "실린더 (납기 4~5일)", "maker": "에스엠씨"}),
]

env = Environment(autoescape=True)


def roundtrip(tmpl, item, quote):
    """렌더한 뒤 data-item 을 다시 읽어 원본과 같은지 본다."""
    out = tmpl.render(it=item, rc=None, recent_map={}, can_edit=True)
    hit = re.search("data-item=" + quote + "(.*?)" + quote, out, re.S)
    if not hit:
        return False, "속성을 못 찾음"
    try:
        got = json.loads(H.unescape(hit.group(1)))
    except Exception as exc:                       # noqa: BLE001 - 실패 사유를 그대로 보여준다
        return False, "파싱 실패(%s)" % str(exc)[:40]
    return (got == item), ("원본과 동일" if got == item else "값이 달라짐")


t_new, t_old = env.from_string(tag_new), env.from_string(tag_old)
print()
print("%-12s %-24s %s" % ("값 종류", "옛 표기(운영 현재)", "새 표기(고친 것)"))
print("-" * 62)
n_old = n_new = 0
for name, item in CASES:
    ok_o, why_o = roundtrip(t_old, item, '"')
    ok_n, why_n = roundtrip(t_new, item, "'")
    n_old += ok_o
    n_new += ok_n
    print("%-13s %s %-22s %s %s" % (name, "OK" if ok_o else "❌", why_o,
                                    "OK" if ok_n else "❌", why_n))
print("-" * 62)
print("옛 표기: %d/5 통과   ←  이게 지금 운영에 있는 것" % n_old)
print("새 표기: %d/5 통과" % n_new)
sys.exit(0 if (n_new == 5 and n_old == 0) else 1)
