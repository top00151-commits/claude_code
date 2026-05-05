"""아이콘 PNG 생성 — PIL로 KNK 로고 스타일 직접 그리기.

매번 SVG → PNG 변환할 필요 없게 정적 PNG 두 장(192/512) 생성.
실행: py generate_icons.py
"""
import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

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
    draw = ImageDraw.Draw(img)

    # 둥근 사각형 + 그라데이션
    radius = int(px * 0.19)
    bg = Image.new("RGBA", (px, px), (37, 99, 235, 255))
    grad = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for y in range(px):
        t = y / px
        r = int(37 + (30 - 37) * t)
        g = int(99 + (58 - 99) * t)
        b = int(235 + (138 - 235) * t)
        gd.line([(0, y), (px, y)], fill=(r, g, b, 255))
    bg = grad

    # 라운드 마스크
    mask = Image.new("L", (px, px), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle((0, 0, px, px), radius=radius, fill=255)
    img.paste(bg, (0, 0), mask)

    # KNK 텍스트
    font_size = int(px * 0.32)
    font = find_font(font_size)
    text = "KNK"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (px - tw) // 2 - bbox[0]
    ty = (px - th) // 2 - bbox[1] - int(px * 0.04)
    draw = ImageDraw.Draw(img)
    draw.text((tx, ty), text, font=font, fill=(255, 255, 255, 255))

    # 우하단 노란 말풍선 닷
    dot_r = int(px * 0.10)
    dot_cx = int(px * 0.74)
    dot_cy = int(px * 0.74)
    draw.ellipse(
        (dot_cx - dot_r, dot_cy - dot_r, dot_cx + dot_r, dot_cy + dot_r),
        fill=(254, 229, 0, 255),
        outline=(30, 58, 138, 255),
        width=max(2, int(px * 0.012)),
    )
    # 말풍선 안 ··· 점
    pd_r = max(1, int(px * 0.012))
    for i in range(3):
        cx = dot_cx + (i - 1) * int(px * 0.04)
        draw.ellipse(
            (cx - pd_r, dot_cy - pd_r, cx + pd_r, dot_cy + pd_r),
            fill=(30, 58, 138, 255),
        )

    return img


for size in (192, 512):
    p = os.path.join(OUT, f"icon-{size}.png")
    make_icon(size).save(p)
    print("wrote", p)

print("아이콘 생성 완료.")
