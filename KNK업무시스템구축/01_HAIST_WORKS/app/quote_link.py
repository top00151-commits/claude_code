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
"""


def num(v):
    try:
        x = float(str(v).replace(",", "").strip())
        return x if x == x else None
    except (TypeError, ValueError):
        return None


def same(a, ccy_a, b, ccy_b):
    """None = 비교 못 함 · True/False."""
    if a is None or b is None:
        return None
    ca, cb = (ccy_a or "").upper(), (ccy_b or "KRW").upper()
    if ca and ca != cb:
        return False
    return abs(float(a) - float(b)) < (1 if cb == "KRW" else 0.01)


def q_price(fields):
    """견적서 읽은 칸 → (단가, 합계, 통화)."""
    fd = fields or {}
    amt = num(fd.get("amount"))
    up = num(fd.get("unit_price"))
    qty = num(fd.get("qty"))
    if up is None and amt is not None and qty:
        up = amt / qty
    return up, amt, (fd.get("currency") or "").upper()


def o_price(total, currency, item_prices):
    """수주 → (단가 · 품목 줄 단가가 모두 같을 때만, 합계, 통화)."""
    ps = [num(x) for x in (item_prices or [])]
    ps = [x for x in ps if x is not None and x > 0]
    up = ps[0] if ps and all(abs(x - ps[0]) < 0.005 for x in ps) else None
    return up, num(total), (currency or "KRW").upper()


def match(qf, op):
    """견적서(q_price) ↔ 수주(o_price) — True 같음 · False 다름 · None 비교 못 함."""
    qup, qamt, qcur = qf
    oup, otot, ocur = op
    r1 = same(qup, qcur, oup, ocur)
    r2 = same(qamt, qcur, otot, ocur)
    if r1 or r2:
        return True
    if r1 is None and r2 is None:
        return None
    return False


def resolve(orders, own, proj_file, acks):
    """orders: 취소 뺀 수주 [{id, order_no, price(o_price)}] (발주일·id 순)
       own: {수주 id: 파일{id, price(q_price), amt_ack_at …}} · proj_file: 관리번호 견적서 파일 또는 None
       acks: {수주 id: 확인한 파일 id}(따라간 견적과 금액 다름 「확인했음」)
       → {수주 id: {st, f, via('own'|'so'|'proj'|''), via_so, cmp, acked}}"""
    out = {}
    for i, o in enumerate(orders):
        f = own.get(o["id"])
        if f:
            m = match(f["price"], o["price"])
            st = "diff" if (m is False and not f.get("amt_ack_at")) else "ok"
            out[o["id"]] = {"st": st, "f": f, "via": "own", "via_so": "", "cmp": m, "acked": bool(f.get("amt_ack_at"))}
            continue
        cands = []
        for prev in reversed(orders[:i]):
            pf = own.get(prev["id"])
            if pf:
                cands.append((pf, "so", prev.get("order_no") or ""))
        if proj_file:
            cands.append((proj_file, "proj", ""))
        hit = None
        for cf, via, vso in cands:
            if match(cf["price"], o["price"]) is True:
                hit = (cf, via, vso, True)
                break
        if not hit and proj_file and match(proj_file["price"], o["price"]) is None:
            hit = (proj_file, "proj", "", None)
        if hit:
            out[o["id"]] = {"st": "link", "f": hit[0], "via": hit[1], "via_so": hit[2], "cmp": hit[3], "acked": False}
            continue
        if proj_file:   # 따라갈 자리 = 관리번호 견적서(대표 「모든 수주가 따라간다」) — 금액이 달라 ⚠
            ack = acks.get(o["id"]) == proj_file["id"]
            out[o["id"]] = {"st": "link" if ack else "diff", "f": proj_file, "via": "proj", "via_so": "",
                            "cmp": False, "acked": ack}
            continue
        # 관리번호 견적서가 없고 앞 수주 견적서도 금액이 달라 따라갈 것이 없음 = 없음(이 수주 견적서를 올릴 자리)
        out[o["id"]] = {"st": "none", "f": None, "via": "", "via_so": "", "cmp": None, "acked": False}
    return out
