# -*- coding: utf-8 -*-
"""z1191z136 (대표 11-24 「나는 생일이 음력 2월 9일 · 음력 계산해서 표현」): 음력 → 양력(한국 시간) — 설치 없는 계산

  · 음력 달의 첫날 = 합삭(달이 해와 겹치는 순간 · Meeus 『Astronomical Algorithms』 49장)이 든 한국 날짜
  · 몇 월인지 = 그 달이 품은 중기(中氣): 1월 우수(330°) · 2월 춘분(0°) · 3월 곡우(30°) … 12월 대한(300°)
    → m월 첫날 = 그 해 m월 중기 날짜 이전(같은 날 포함) 가장 늦은 합삭 날 → 윤달이 끼어도 맞다(중기 없는 달 = 윤달)
  · 해의 겉보기 황경 = Meeus 25장 간단식(약 0.01°) · 중기 날짜는 반으로 나눠 찾기
  · 검증: 공휴일 표(부처님오신날 음력 4/8 · 추석 8/15 · 2024~2036 · 윤달 있는 해 포함) — 시험 파일
"""
import math
from datetime import date, datetime, timedelta

_KST = 9


def _jd_to_kst_date(jd):
    return (datetime(1970, 1, 1) + timedelta(days=jd - 2440587.5 + _KST / 24.0)).date()


def _new_moon_jd(k):
    """k번째 합삭(2000-01-06 기준) 순간의 율리우스일(UT 근사 · ΔT 약 70초 뺌)."""
    T = k / 1236.85
    jde = 2451550.09766 + 29.530588861 * k + 0.00015437 * T ** 2 - 0.000000150 * T ** 3 + 0.00000000073 * T ** 4
    E = 1 - 0.002516 * T - 0.0000074 * T ** 2
    r, s = math.radians, math.sin
    M = r(2.5534 + 29.10535670 * k - 0.0000014 * T ** 2 - 0.00000011 * T ** 3)
    Mp = r(201.5643 + 385.81693528 * k + 0.0107582 * T ** 2 + 0.00001238 * T ** 3 - 0.000000058 * T ** 4)
    F = r(160.7108 + 390.67050284 * k - 0.0016118 * T ** 2 - 0.00000227 * T ** 3 + 0.000000011 * T ** 4)
    O = r(124.7746 - 1.56375588 * k + 0.0020672 * T ** 2 + 0.00000215 * T ** 3)
    c = (-0.40720 * s(Mp) + 0.17241 * E * s(M) + 0.01608 * s(2 * Mp) + 0.01039 * s(2 * F) + 0.00739 * E * s(Mp - M)
         - 0.00514 * E * s(Mp + M) + 0.00208 * E * E * s(2 * M) - 0.00111 * s(Mp - 2 * F) - 0.00057 * s(Mp + 2 * F)
         + 0.00056 * E * s(2 * Mp + M) - 0.00042 * s(3 * Mp) + 0.00042 * E * s(M + 2 * F) + 0.00038 * E * s(M - 2 * F)
         - 0.00024 * E * s(2 * Mp - M) - 0.00017 * s(O) - 0.00007 * s(Mp + 2 * M) + 0.00004 * s(2 * Mp - 2 * F)
         + 0.00004 * s(3 * M) + 0.00003 * s(Mp + M - 2 * F) + 0.00003 * s(2 * Mp + 2 * F) - 0.00003 * s(Mp + M + 2 * F)
         + 0.00003 * s(Mp - M + 2 * F) - 0.00002 * s(Mp - M - 2 * F) - 0.00002 * s(3 * Mp + M) + 0.00002 * s(4 * Mp))
    return jde + c - 69.0 / 86400.0


def _sun_lon(jd):
    """해의 겉보기 황경(도) — Meeus 25장 간단식."""
    T = (jd - 2451545.0) / 36525.0
    L0 = 280.46646 + 36000.76983 * T + 0.0003032 * T * T
    M = math.radians(357.52911 + 35999.05029 * T - 0.0001537 * T * T)
    C = ((1.914602 - 0.004817 * T - 0.000014 * T * T) * math.sin(M) + (0.019993 - 0.000101 * T) * math.sin(2 * M)
         + 0.000289 * math.sin(3 * M))
    om = math.radians(125.04 - 1934.136 * T)
    return (L0 + C - 0.00569 - 0.00478 * math.sin(om)) % 360.0


def _jd(d):
    return (datetime(d.year, d.month, d.day) - datetime(1970, 1, 1)).total_seconds() / 86400.0 + 2440587.5


def _term_date(year, deg):
    """그 해(양력)에 해가 deg 도에 닿는 한국 날짜(중기)."""
    approx = date(year, 3, 20) + timedelta(days=round(((deg % 360) / 360.0) * 365.2422))
    if deg >= 330 or deg < 0:   # 우수(330°)는 2월 — 그 해 안에서 찾음
        approx = date(year, 2, 19)
    a, b = _jd(approx) - 20, _jd(approx) + 20
    def diff(j):
        x = (_sun_lon(j) - deg + 540.0) % 360.0 - 180.0
        return x
    for _ in range(60):
        mid = (a + b) / 2
        if diff(mid) < 0:
            a = mid
        else:
            b = mid
    return _jd_to_kst_date((a + b) / 2)


def _lny(year):
    """설날(음력 1월 1일) — 공휴일 라이브러리 표(한국천문연구원 기준)를 그대로 쓴다. 없으면 None."""
    try:
        from holidays.calendars import _ChineseLunisolar
        from holidays.calendars.chinese import KOREAN_CALENDAR
        v = _ChineseLunisolar(KOREAN_CALENDAR).lunar_new_year_date(year)
        v = v[0] if isinstance(v, tuple) else v
        return v if isinstance(v, date) else None
    except Exception:
        return None


def _nm_k_on(d):
    k = round((d.year + (d.timetuple().tm_yday - 1) / 365.25 - 2000) * 12.3685)
    for kk in range(k - 2, k + 3):
        if _jd_to_kst_date(_new_moon_jd(kk)) == d:
            return kk
    return None


# 중기 규칙과 한국천문연구원 윤달이 다른 해(「2033년 문제」 · 윤11월로 정함) — 그 윤달 전 달은 설날부터 달을 센다
_LEAP_FIXED = {2033: 11}


def _month_start(year, m):
    """음력 year년 m월 1일(양력 date)."""
    lny = _lny(year)
    if m == 1 and lny:
        return lny
    if lny and year in _LEAP_FIXED and m <= _LEAP_FIXED[year]:
        k0 = _nm_k_on(lny)
        if k0 is not None:
            return _jd_to_kst_date(_new_moon_jd(k0 + m - 1))
    term = _term_date(year, (330 + 30 * (m - 1)) % 360 if m >= 1 else 330)
    k = round((term.year + (term.timetuple().tm_yday - 1) / 365.25 - 2000) * 12.3685)
    best = None
    for kk in range(k - 3, k + 3):
        d = _jd_to_kst_date(_new_moon_jd(kk))
        if d <= term and (best is None or d > best):
            best = d
    return best


def lunar_to_solar(year, m, d):
    """음력 year년 m월 d일 → 양력 date(평달). 그 달에 d일이 없으면(29일까지인 달의 30일) 그 달 마지막 날."""
    s = _month_start(year, m)
    nxt = _month_start(year, m + 1) if m < 12 else _month_start(year + 1, 1)
    last = (nxt - s).days if nxt else 30
    return s + timedelta(days=min(d, last) - 1)


def is_lunar_md_today(lmd, today):
    """lmd = 「MM-DD」(음력) · today = 양력 date → 오늘이 그 음력 날인가(올해 · 연초면 지난해 음력도 봄)."""
    try:
        m, d = (int(x) for x in str(lmd).split("-"))
    except Exception:
        return False
    for y in (today.year, today.year - 1):
        try:
            if lunar_to_solar(y, m, d) == today:
                return True
        except Exception:
            continue
    return False
