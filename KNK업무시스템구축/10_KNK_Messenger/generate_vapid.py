"""VAPID 키 페어 1회 생성 — 운영 시 한번만 실행, .env에 저장.

생성:
  py generate_vapid.py
출력:
  - data/vapid_private.pem (서버 보관)
  - 콘솔에 VAPID_PUBLIC_KEY (클라이언트 subscription 시 필요)
"""
import os
import sys
import base64
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

sys.stdout.reconfigure(encoding="utf-8")

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(APP_DIR, "data")
os.makedirs(DATA, exist_ok=True)

PRIV_PEM = os.path.join(DATA, "vapid_private.pem")

if os.path.exists(PRIV_PEM):
    with open(PRIV_PEM, "rb") as f:
        priv = serialization.load_pem_private_key(f.read(), password=None)
    print(f"[OK] 기존 키 발견: {PRIV_PEM}")
else:
    priv = ec.generate_private_key(ec.SECP256R1())
    pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    with open(PRIV_PEM, "wb") as f:
        f.write(pem)
    print(f"[OK] 신규 키 저장: {PRIV_PEM}")

# 공개키 raw 65바이트 (0x04 || x32 || y32) → base64url
pub = priv.public_key().public_bytes(
    encoding=serialization.Encoding.X962,
    format=serialization.PublicFormat.UncompressedPoint,
)
pub_b64u = base64.urlsafe_b64encode(pub).rstrip(b"=").decode()
print()
print("VAPID_PUBLIC_KEY (클라이언트용 base64url):")
print(pub_b64u)
print()
print("→ static/js 또는 /api/push/vapid_public 통해 클라이언트에 전달.")
