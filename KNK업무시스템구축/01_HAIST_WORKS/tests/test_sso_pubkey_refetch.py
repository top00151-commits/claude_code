# -*- coding: utf-8 -*-
"""SSO 공개키 재조회 — 이음 서명키가 바뀌었을 때 WORKS 로그인 검증 (z1100)

실행:  01_HAIST_WORKS 루트에서
    python tests/test_sso_pubkey_refetch.py

배경: 이음(메신저)이 서명키를 새로 만들면, 옛 공개키를 1시간 캐시하고 있는 WORKS 는
  새 토큰을 '서명 불일치'로 거부한다. 이때 공개키를 1회 다시 받아 재검증해야 하는데,
  예전 코드는 InvalidSignatureError 를 InvalidTokenError 에서 먼저 잡아 재조회 분기가 죽어 있었다.
  근거: 10_KNK_Messenger/작업기록/2026-09-15_2229_이음_SSO서명키_사본없음_원인영향_보관방법_대표결정요청.md 7장

- 네트워크 없음: sso_client.httpx 를 가짜 이음으로 바꿔 끼운다(공개키 요청 횟수를 센다).
- 시험용 키쌍은 이 스크립트 안에서만 만들고 버린다(출력하지 않음).

⚠ 종료코드: FAIL 이 있으면 1, 전부 통과면 0.
"""
import os
import sys
import time
from types import SimpleNamespace

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # 01_HAIST_WORKS
sys.path.insert(0, ROOT)

import jwt as pyjwt  # noqa: E402
from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: E402

from app import sso_client as sso  # noqa: E402

ok = True


def chk(name, cond, detail=""):
    global ok
    print(("[OK] " if cond else "[FAIL] ") + name + (f"  ({detail})" if detail and not cond else ""))
    ok = ok and bool(cond)


def keypair():
    k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv = k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                           serialization.NoEncryption())
    pub = k.public_key().public_bytes(serialization.Encoding.PEM,
                                      serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    return priv, pub.strip()


class FakeMessenger:
    """가짜 이음 /api/sso/public-key — 요청 횟수·응답 상태를 조종한다."""

    def __init__(self):
        self.pem = None
        self.status = 200
        self.calls = 0

    def get(self, url, **_kw):
        if "/api/sso/public-key" not in url:
            raise AssertionError(f"예상 밖 호출: {url}")
        self.calls += 1
        if self.status != 200:
            return SimpleNamespace(status_code=self.status, text="unavailable")
        return SimpleNamespace(status_code=200, text=self.pem)


def token(priv, *, aud=None, iss=None, exp_in=600, **extra):
    now = int(time.time())
    body = {"sub": "TEST001", "aud": aud or sso.SSO_AUDIENCE, "iss": iss or sso.SSO_ISSUER,
            "iat": now, "exp": now + exp_in}
    body.update(extra)
    return pyjwt.encode(body, priv, algorithm="RS256")


def open_cooldown():
    """강제 재조회 최소 간격을 지난 상태로 만든다(시험 사이 간섭 제거)."""
    sso._PUBKEY_CACHE["forced_at"] = 0


A_PRIV, A_PUB = keypair()   # 옛 키
B_PRIV, B_PUB = keypair()   # 새로 만든 키
C_PRIV, C_PUB = keypair()   # 이음이 모르는 키(위조·다른 서버)

fake = FakeMessenger()
sso.httpx = fake

# ── 준비: 옛 키 A 로 캐시 채움 ───────────────────────────────
sso.invalidate_public_key_cache()
open_cooldown()
fake.pem = A_PUB
chk("준비: 캐시에 옛 키 A", sso.get_public_key() == A_PUB and fake.calls == 1)

# ── 1. 키 교체: 이음은 B, 캐시는 A → 1회 재조회로 통과 ─────────
fake.pem = B_PUB
n = fake.calls
p = sso.verify_token(token(B_PRIV))
chk("1. 새 키 B 토큰 → 재조회 후 통과", bool(p) and p.get("sub") == "TEST001")
chk("1. 공개키 요청은 딱 1회", fake.calls == n + 1, f"{fake.calls - n}회")
chk("1. 캐시가 새 키 B 로 바뀜", sso._PUBKEY_CACHE["pem"] == B_PUB)

n = fake.calls
chk("1. 다음 B 토큰은 요청 없이 통과", bool(sso.verify_token(token(B_PRIV))) and fake.calls == n)

# ── 2~5. 서명은 맞지만 다른 이유로 틀린 토큰 → 재조회 없음 ─────
open_cooldown()
n = fake.calls
chk("2. 만료 토큰 → 거부", sso.verify_token(token(B_PRIV, exp_in=-120)) is None)
chk("2. 만료 토큰은 공개키 재조회 없음", fake.calls == n, f"{fake.calls - n}회")

chk("3. audience 불일치 → 거부", sso.verify_token(token(B_PRIV, aud="other-app")) is None)
chk("3. audience 불일치는 재조회 없음", fake.calls == n, f"{fake.calls - n}회")

chk("4. issuer 불일치 → 거부", sso.verify_token(token(B_PRIV, iss="https://evil.example/")) is None)
chk("4. issuer 불일치는 재조회 없음", fake.calls == n, f"{fake.calls - n}회")

chk("5. 형식 깨진 토큰 → 거부", sso.verify_token("not.a.jwt") is None)
chk("5. 형식 깨진 토큰은 재조회 없음", fake.calls == n, f"{fake.calls - n}회")

svc_b = token(B_PRIV, aud="knk-fx", purpose="fx_rates")
chk("5b. 서비스 토큰(aud knk-fx)으로 로그인 불가", sso.verify_token(svc_b) is None)
chk("5b. 그때도 재조회 없음", fake.calls == n, f"{fake.calls - n}회")

# ── 6. 이음 503 → 옛 캐시 유지 ───────────────────────────────
open_cooldown()
fake.status = 503
n = fake.calls
chk("6. 이음 503 + 모르는 키 C 토큰 → 거부", sso.verify_token(token(C_PRIV)) is None)
chk("6. 재조회는 시도함(1회)", fake.calls == n + 1, f"{fake.calls - n}회")
chk("6. 옛 캐시(B) 그대로 유지", sso._PUBKEY_CACHE["pem"] == B_PUB)
n = fake.calls
chk("6. 이음이 멈춰도 B 토큰은 계속 통과", bool(sso.verify_token(token(B_PRIV))) and fake.calls == n)
fake.status = 200

# ── 7. 폭주 방지: 서명 틀린 토큰 연타 → 재조회는 최소 간격당 1회 ──
open_cooldown()
fake.pem = B_PUB
n = fake.calls
rejected = all(sso.verify_token(token(C_PRIV)) is None for _ in range(20))
chk("7. 위조 토큰 20회 → 전부 거부", rejected)
chk("7. 이음 공개키 요청은 1회뿐", fake.calls - n <= 1, f"{fake.calls - n}회")

# ── 8. 최소 간격이 지나면 다시 받음 (연타 직후 진짜 교체) ────────
fake.pem = C_PUB
n = fake.calls
chk("8. 간격 안: 새 키 C 토큰은 아직 거부", sso.verify_token(token(C_PRIV)) is None and fake.calls == n)
sso._PUBKEY_CACHE["forced_at"] = time.time() - getattr(sso, "_PUBKEY_FORCE_REFRESH_MIN_SEC", 30) - 1
chk("8. 간격 지남: 새 키 C 토큰 → 재조회 후 통과", bool(sso.verify_token(token(C_PRIV))))
chk("8. 그때 요청 1회", fake.calls == n + 1, f"{fake.calls - n}회")

# ── 9. 서비스 토큰(환율 · aud knk-fx) 도 같은 규칙 ───────────────
AUD, PURPOSE = "knk-fx", "fx_rates"
sso.invalidate_public_key_cache()
open_cooldown()
fake.pem = A_PUB
sso.get_public_key()
fake.pem = B_PUB
n = fake.calls
p = sso.verify_service_token(token(B_PRIV, aud=AUD, purpose=PURPOSE), PURPOSE, AUD)
chk("9. 서비스 토큰: 새 키 B → 재조회 후 통과", bool(p) and p.get("purpose") == PURPOSE)
chk("9. 서비스 토큰: 요청 1회", fake.calls == n + 1, f"{fake.calls - n}회")

open_cooldown()
n = fake.calls
chk("9. 서비스 토큰: 만료 → 거부",
    sso.verify_service_token(token(B_PRIV, aud=AUD, purpose=PURPOSE, exp_in=-120), PURPOSE, AUD) is None)
chk("9. 서비스 토큰: purpose 불일치 → 거부",
    sso.verify_service_token(token(B_PRIV, aud=AUD, purpose="other"), PURPOSE, AUD) is None)
chk("9. 서비스 토큰: 로그인 토큰(aud haist-works) → 거부",
    sso.verify_service_token(token(B_PRIV, purpose=PURPOSE), PURPOSE, AUD) is None)
chk("9. 서비스 토큰: 위 3건 재조회 없음", fake.calls == n, f"{fake.calls - n}회")

fake.status = 503
chk("9. 서비스 토큰: 이음 503 + 키 C → 거부",
    sso.verify_service_token(token(C_PRIV, aud=AUD, purpose=PURPOSE), PURPOSE, AUD) is None)
chk("9. 서비스 토큰: 옛 캐시(B) 유지", sso._PUBKEY_CACHE["pem"] == B_PUB)
fake.status = 200

print("\nRESULT:", "ALL PASS" if ok else "HAS FAILURES")
sys.exit(0 if ok else 1)
