# -*- coding: utf-8 -*-
"""z1191z141 (대표 11-24 「진행」): 수주(호기)마다 최종 견적서가 무엇인지 — 셋 중 하나로 정한다.

  🟢 ok   = 이 수주에 따로 올린 견적서가 있음(금액이 맞거나 「확인했음」)
  🔗 link = 따로 올린 것이 없어 같은 관리번호 안 견적서를 따라감
           찾는 순서: 앞 수주(가까운 것부터)의 견적서 → 관리번호 견적서(order_id 없음) · 단가(또는 합계)가 같은 첫 견적서
           단가를 비교할 수 없으면(어느 쪽이든 금액을 못 읽음) 관리번호 견적서를 그대로 따라감
  ⚠ diff = 관리번호 견적서의 금액이 이 수주와 다름(막지 않음 · 「확인했음」 한 번이면 🔗) · 또는 이 수주 견적서 금액이 다름(z105 그대로)
  none   = 따라갈 견적서가 없음(관리번호 견적서가 없고 앞 수주 견적서도 금액이 다르거나 없음)

  「같은 금액」 = 통화가 적혀 있으면 같아야 하고, 원화 1원 · 외화 0.01 차이까지 같음(z105 _z105_amt_same 과 같은 규칙).
  견적서 단가 = 읽은 값 unit_price · 없으면 amount ÷ qty(qty 있을 때) · 수주 단가 = 그 수주 품목 줄 단가가 모두 같을 때 그 값.
  견적서 「같다」 = 단가가 같음 또는 공급가 합계가 수주 합계와 같음(둘 중 하나).
  데이터 연결성 규칙: 자동 연결은 금액이 분명히 같은 것 · 비교 못 하면 관리번호 견적서(대표가 「모든 수주가 따라간다」고 정한 자리)만.

  z1191z156 (대표 11-25 정하고 11-26 「진행하자」): 견적서는 수주번호에만 붙는다 — 관리번호 견적서 자리는 없앰.
  부르는 곳(main.py _z105_board · _z141_project · _z150_docs)은 proj_file 에 늘 None 을 넘긴다 →
  결과는 🟢 이 수주 견적 · 🔗 금액 같은 앞 수주 견적 · ⚠ 이 수주 견적 금액 다름 · none 뿐(via 'proj' 는 생기지 않음).
  수주번호 없는 옛 견적서는 판정에 안 쓰고 「⚠ 수주 칸 확인 필요」에서 사람이 수주를 고른다.

  z1191z160 (대표 11-26 「견적서·발주서 내용을 검토하는 기능을 빼줘 · 사용자들이 등록하는 걸 믿고 진행 ·
    발주서·견적서가 무조건 하나만 등록되는 건 아니야 · 여러 개 등록될 수 있게 제한을 풀어줘」):
  · 위 🔗·⚠ 판정(금액 비교 · 앞 수주 견적 따라가기 · 「확인했음」)은 모두 없앰 — 아래 resolve 는 수주마다 그 수주에 올린 견적서 전부만 돌려준다
  · 한 수주에 견적서가 여러 장이면 모두 같은 자격(「최종」·「이전」 없음) · 올린 순서(최근 위)
  · 견적서가 없는 수주는 「없음」 — 다른 수주 견적서를 저절로 이어 붙이지 않는다(사용자가 고르지 않은 것을 연결하지 않음)
"""


def num(v):
    try:
        x = float(str(v).replace(",", "").strip())
        return x if x == x else None
    except (TypeError, ValueError):
        return None


def q_price(fields):
    """견적서 읽은 칸 → (단가, 합계, 통화)."""
    fd = fields or {}
    amt = num(fd.get("amount"))
    up = num(fd.get("unit_price"))
    qty = num(fd.get("qty"))
    if up is None and amt is not None and qty:
        up = amt / qty
    return up, amt, (fd.get("currency") or "").upper()



def resolve(orders, own, proj_file=None, acks=None):
    """z1191z160: orders = 취소 뺀 수주 [{id, …}] · own = {수주 id: [그 수주에 올린 견적서 줄 …]}(한 장만 넘겨도 됨)
       → {수주 id: {st('ok'|'none'), fs([견적서 줄 · 최근 위])}} — 금액 비교·따라가기 없음(proj_file·acks 는 옛 부르는 곳 호환용 · 쓰지 않음)."""
    out = {}
    for o in orders:
        fs = own.get(o["id"]) or []
        if isinstance(fs, dict):
            fs = [fs]
        fs = sorted(fs, key=lambda x: x.get("id") or 0, reverse=True)
        out[o["id"]] = {"st": "ok" if fs else "none", "fs": fs}
    return out
