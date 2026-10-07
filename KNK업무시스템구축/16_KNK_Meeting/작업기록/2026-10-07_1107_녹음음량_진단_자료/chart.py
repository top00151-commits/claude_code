# -*- coding: utf-8 -*-
"""대회의실 녹음 진단 그림 — 분별 음량 + 일치율 (이모지 안 씀)"""
import io
import re
import statistics as st

from PIL import Image, ImageDraw, ImageFont

B = "C:/Windows/Fonts/malgunbd.ttf"
R = "C:/Windows/Fonts/malgun.ttf"
f = lambda p, s: ImageFont.truetype(p, s)
F28, F20, F17, F15, F13 = f(B, 28), f(B, 20), f(R, 17), f(B, 15), f(R, 13)
F46 = f(B, 46)

v = [float(m) for m in re.findall(r"RMS_level=(-?[0-9.]+)", io.open("rms.txt").read())]
mins = [v[i * 60:(i + 1) * 60] for i in range((len(v) + 59) // 60)]
med = [st.median(m) for m in mins if m]

W, H = 1180, 790
im = Image.new("RGB", (W, H), "#ffffff")
d = ImageDraw.Draw(im)

d.text((40, 28), "대회의실 녹음 진단 — 왜 받아쓰기가 흔들렸나", font=F28, fill="#111111")
d.text((40, 70), "회의 61 「삼성 MSCC 출하 검사기」 · 2026-10-06 08:54 녹음 · 13분 38초 · 같은 파일 한 개를 구간별로 재 봄",
       font=F17, fill="#555555")

# ── 막대그림 ─────────────────────────────────────────
X0, Y0, BW, BH = 70, 150, 68, 300
TOP, BOT = -20.0, -46.0


def ypos(db):
    return Y0 + BH * (TOP - db) / (TOP - BOT)


for g in range(-20, -47, -5):
    y = ypos(g)
    d.line((X0 - 8, y, X0 + BW * len(med) + 10, y), fill="#e6e6e6")
    d.text((X0 - 58, y - 10), "%d dB" % g, font=F13, fill="#999999")

for i, m in enumerate(med):
    x = X0 + i * BW
    quiet = i < 9
    col = "#c0392b" if quiet else "#1e8449"
    d.rectangle((x + 8, ypos(m), x + BW - 10, Y0 + BH), fill=col)
    d.text((x + 16, ypos(m) - 22), "%d" % round(m), font=F15, fill=col)
    d.text((x + 20, Y0 + BH + 8), "%d분" % (i + 1), font=F13, fill="#777777")

d.text((X0 + 10, Y0 + BH + 34), "앞 9분 — 평균 -40 dB (멀다)", font=F20, fill="#c0392b")
d.text((X0 + 9 * BW + 10, Y0 + BH + 34), "뒤 5분 — -25 dB (가깝다)", font=F20, fill="#1e8449")
d.text((X0 + 10, Y0 + BH + 64), "같은 회의 안에서 소리 크기가 15 dB (거리로 약 5배) 차이났다", font=F17, fill="#333333")

# ── 일치율 두 칸 ─────────────────────────────────────
CY = 585
d.text((40, CY - 36), "같은 소리를 두 가지 방식(지금 32kbps / 원본 품질)으로 받아썼을 때 글이 일치한 비율", font=F20, fill="#111111")
for (bx, col, pct, lab, sub) in [
        (60, "#c0392b", "73.2%", "조용한 앞 9분", "글이 27% 달라진다 = AI 가 메우고 있다"),
        (600, "#1e8449", "95.4%", "소리 큰 뒤 5분", "거의 같다 = AI 가 실제로 듣고 있다")]:
    d.rectangle((bx, CY, bx + 500, CY + 150), fill="#fafafa", outline=col, width=2)
    d.text((bx + 24, CY + 22), pct, font=F46, fill=col)
    d.text((bx + 190, CY + 32), lab, font=F20, fill="#111111")
    d.text((bx + 190, CY + 62), "평균 %s" % ("-40 dB" if pct.startswith("73") else "-25 dB"), font=F17, fill="#666666")
    d.text((bx + 24, CY + 100), sub, font=F17, fill="#444444")

d.text((40, CY + 170),
       "확인한 것: 음량 키우기(+23 dB)·소음 제거·원본 품질 모두 앞 9분을 살리지 못했다. 가까이서 담은 뒤 5분만 제대로 나왔다.",
       font=F17, fill="#333333")
im.save("진단_대회의실녹음.png")
print("그림 저장 — 진단_대회의실녹음.png")
