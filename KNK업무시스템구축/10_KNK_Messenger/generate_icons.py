"""KNK 메신저 PWA 아이콘 생성 — 간단 "KNK" 글자 버전 (KNK 레드 적용).

구성:
  - KNK 레드 그라데이션 배경 (#A5282C → #6B1015) + 둥근 모서리
  - 흰색 "KNK" 글자 (시스템 굵은 폰트)
  - 우하단 흰 말풍선 닷 + KNK 레드 테두리·점

실행: py generate_icons.py
"""
import os
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "icons")
os.makedirs(OUT, exist_ok=True)


def find_font(size):
    candidates = [
        "C:/Windows/Fonts/malgunbd.ttf",
        "C:/Windows/Fonts/malgun.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    return ImageFont.load_default()


def make_icon(px):
    img = Image.new("RGBA", (px, px), (0, 0, 0, 0))

    # KNK 레드 그라데이션 (#A5282C → #6B1015)
    radius = int(px * 0.19)
    grad = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for y in range(px):
        t = y / px
        r = int(165 + (107 - 165) * t)
        g = int(40 + (16 - 40) * t)
        b = int(44 + (21 - 44) * t)
        gd.line([(0, y), (px, y)], fill=(r, g, b, 255))

    # 둥근 모서리 마스크
    mask = Image.new("L", (px, px), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle((0, 0, px, px), radius=radius, fill=255)
    img.paste(grad, (0, 0), mask)

    draw = ImageDraw.Draw(img)

    # KNK 텍스트 (흰색)
    font_size = int(px * 0.32)
    font = find_font(font_size)
    text = "KNK"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (px - tw) // 2 - bbox[0]
    ty = (px - th) // 2 - bbox[1] - int(px * 0.04)
    draw.text((tx, ty), text, font=font, fill=(255, 255, 255, 255))

    # 우하단 흰 말풍선 닷 (KNK 레드 테두리)
    dot_r = int(px * 0.10)
    dot_cx = int(px * 0.74)
    dot_cy = int(px * 0.74)
    draw.ellipse(
        (dot_cx - dot_r, dot_cy - dot_r, dot_cx + dot_r, dot_cy + dot_r),
        fill=(255, 255, 255, 255),
        outline=(165, 40, 44, 255),
        width=max(2, int(px * 0.012)),
    )
    # 말풍선 안 ··· 점 (KNK 레드)
    pd_r = max(1, int(px * 0.012))
    for i in range(3):
        cx = dot_cx + (i - 1) * int(px * 0.04)
        draw.ellipse(
            (cx - pd_r, dot_cy - pd_r, cx + pd_r, dot_cy + pd_r),
            fill=(165, 40, 44, 255),
        )

    return img


if __name__ == "__main__":
    for size in (192, 512):
        out = os.path.join(OUT, f"icon-{size}.png")
        make_icon(size).save(out)
        print(f"wrote {out}")
    print("KNK 아이콘 생성 완료 (간단 KNK 텍스트 + KNK 레드).")
