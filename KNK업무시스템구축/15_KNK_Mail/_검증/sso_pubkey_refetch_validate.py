# -*- coding: utf-8 -*-
"""KNK Eum MAIL — 이음 서명키가 바뀌었을 때 SSO 공개키 재조회 검증 (WORKS z1100 과 같은 수리)

실행:  15_KNK_Mail 루트에서
    python _검증/sso_pubkey_refetch_validate.py

- 네트워크 없음: sso_client.httpx 를 가짜 이음으로 바꿔 끼운다(공개키 요청 횟수를 센다).
- 시험용 키쌍은 이 스크립트 안에서만 만들고 버린다(출력하지 않음).
- 근거: 10_KNK_Messenger/작업기록/2026-09-15_2229_이음_SSO서명키_사본없음_원인영향_보관방법_대표결정요청.md 7장
"""
import os, sys, time
from types import SimpleNamespace

try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

VAL_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(VAL_DIR)
sys.path.insert(0, PROJECT)

import jwt as pyjwt  # noqa
from cryptography.hazmat.primitives import serialization  # noqa
from cryptography.hazmat.primitives.asymmetric import rsa  # noqa

from app import sso_client as sso  # noqa

ok = True
def chk(n, c, detail=""):
    global ok; print(("[OK] " if c else "[FAIL] ") + n + (f"  ({detail})" if detail and not c else "")); ok = ok and bool(c)


def keypair():
    k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv = k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                           serialization.NoEncryption())
    pub = k.public_key().public_bytes(serialization.Encoding.PEM,
                                      serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    return priv, pub.strip()


class FakeMessenger:
    def __init__(self): self.pem = None; self.status = 200; self.calls = 0
    def get(self, url, **_kw):
        if "/api/sso/public-key" not in url: raise AssertionError(f"예상 밖 호출: {url}")
        self.calls += 1
        if self.status != 200: return SimpleNamespace(status_code=self.status, text="unavailable")
        return SimpleNamespace(status_code=200, text=self.pem)


def token(priv, *, aud=None, iss=None, exp_in=600):
    now = int(time.time())
    return pyjwt.encode({"sub": "TEST001", "aud": aud or sso.SSO_AUDIENCE, "iss": iss or sso.SSO_ISSUER,
                         "iat": now, "exp": now + exp_in}, priv, algorithm="RS256")


def open_cooldown(): sso._PUBKEY_CACHE["forced_at"] = 0


A_PRIV, A_PUB = keypair(); B_PRIV, B_PUB = keypair(); C_PRIV, C_PUB = keypair()
fake = FakeMessenger(); sso.httpx = fake

chk("audience=knk-mail", sso.SSO_AUDIENCE == "knk-mail")

# 준비: 옛 키 A 로 캐시
sso.invalidate_public_key_cache(); open_cooldown(); fake.pem = A_PUB
chk("준비: 캐시에 옛 키 A", sso.get_public_key() == A_PUB and fake.calls == 1)

# 1. 키 교체 → 1회 재조회로 통과
fake.pem = B_PUB; n = fake.calls
p = sso.verify_token(token(B_PRIV))
chk("1. 새 키 B 토큰 → 재조회 후 통과", bool(p) and p.get("sub") == "TEST001")
chk("1. 공개키 요청은 딱 1회", fake.calls == n + 1, f"{fake.calls - n}회")
chk("1. 캐시가 새 키 B 로 바뀜", sso._PUBKEY_CACHE["pem"] == B_PUB)

# 2~5. 서명은 맞지만 다른 이유로 틀림 → 재조회 없음
open_cooldown(); n = fake.calls
chk("2. 만료 토큰 → 거부", sso.verify_token(token(B_PRIV, exp_in=-120)) is None)
chk("3. audience 불일치(haist-works) → 거부", sso.verify_token(token(B_PRIV, aud="haist-works")) is None)
chk("4. issuer 불일치 → 거부", sso.verify_token(token(B_PRIV, iss="https://evil.example/")) is None)
chk("5. 형식 깨진 토큰 → 거부", sso.verify_token("not.a.jwt") is None)
chk("2~5. 네 건 모두 공개키 재조회 없음", fake.calls == n, f"{fake.calls - n}회")

# 6. 이음 503 → 옛 캐시 유지
open_cooldown(); fake.status = 503; n = fake.calls
chk("6. 이음 503 + 모르는 키 C → 거부", sso.verify_token(token(C_PRIV)) is None)
chk("6. 재조회는 시도함(1회)", fake.calls == n + 1, f"{fake.calls - n}회")
chk("6. 옛 캐시(B) 그대로 유지", sso._PUBKEY_CACHE["pem"] == B_PUB)
chk("6. 이음이 멈춰도 B 토큰은 계속 통과", bool(sso.verify_token(token(B_PRIV))))
fake.status = 200

# 7. 폭주 방지
open_cooldown(); fake.pem = B_PUB; n = fake.calls
chk("7. 위조 토큰 20회 → 전부 거부", all(sso.verify_token(token(C_PRIV)) is None for _ in range(20)))
chk("7. 이음 공개키 요청은 1회뿐", fake.calls - n <= 1, f"{fake.calls - n}회")

# 8. 최소 간격 지나면 다시 받음
fake.pem = C_PUB; n = fake.calls
chk("8. 간격 안: 새 키 C 토큰은 아직 거부", sso.verify_token(token(C_PRIV)) is None and fake.calls == n)
sso._PUBKEY_CACHE["forced_at"] = time.time() - getattr(sso, "_PUBKEY_FORCE_REFRESH_MIN_SEC", 30) - 1
chk("8. 간격 지남: 새 키 C 토큰 → 재조회 후 통과", bool(sso.verify_token(token(C_PRIV))))
chk("8. 그때 요청 1회", fake.calls == n + 1, f"{fake.calls - n}회")

print("\nRESULT:", "ALL PASS" if ok else "HAS FAILURES")
sys.exit(0 if ok else 1)
