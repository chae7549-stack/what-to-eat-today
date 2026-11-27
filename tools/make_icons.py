"""냉장고 파먹기 PWA 아이콘 생성 (SVG와 같은 디자인을 PNG로 렌더링)."""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SS = 4  # 슈퍼샘플링 배율


def gradient(size, c1, c2, c3):
    """대각선 3색 그라데이션."""
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    t = ((x / size) * 0.55 + (y / size) * 0.75)
    t = np.clip(t / 1.3, 0, 1)
    out = np.zeros((size, size, 3), dtype=np.float32)
    c1, c2, c3 = (np.array(c, dtype=np.float32) for c in (c1, c2, c3))
    mid = t < 0.55
    tt = t / 0.55
    out[mid] = c1 + (c2 - c1) * tt[mid][:, None]
    tt2 = (t - 0.55) / 0.45
    out[~mid] = c2 + (c3 - c2) * tt2[~mid][:, None]
    return Image.fromarray(out.astype(np.uint8), "RGB")


def rounded_mask(size, radius):
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    return mask


def star(draw, cx, cy, r, fill=(255, 255, 255, 235)):
    """4꼭지 반짝이."""
    pts = []
    for i in range(8):
        ang = math.pi / 4 * i - math.pi / 2
        rad = r if i % 2 == 0 else r * 0.34
        pts.append((cx + math.cos(ang) * rad, cy + math.sin(ang) * rad))
    draw.polygon(pts, fill=fill)


def handle_layer(w, h, length, thick, angle, fill):
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle(
        (w // 2 - length // 2, h // 2 - thick // 2, w // 2 + length // 2, h // 2 + thick // 2),
        radius=thick // 2,
        fill=fill,
    )
    return layer.rotate(angle, resample=Image.BICUBIC, expand=False)


def render(size, maskable=False):
    S = size * SS
    scale = S / 512.0

    def s(v):
        return v * scale

    art = gradient(S, (255, 186, 92), (255, 107, 61), (232, 66, 32)).convert("RGBA")

    layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    # 팬 손잡이 (뒤에 깔리도록 먼저)
    hl = handle_layer(int(s(260)), int(s(120)), int(s(150)), int(s(34)), 22, (255, 255, 255, 245))
    layer.alpha_composite(hl, (int(s(268)), int(s(210))))

    # 팬 본체
    cx, cy, r = s(238), s(284), s(116)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255, 255))
    r2 = s(96)
    d.ellipse((cx - r2, cy - r2, cx + r2, cy + r2), fill=(255, 228, 198, 255))

    # 달걀 흰자 + 노른자
    ew_w, ew_h = s(58), s(48)
    d.ellipse(
        (cx - ew_w - s(6), cy - ew_h, cx + ew_w - s(6), cy + ew_h),
        fill=(255, 255, 255, 255),
    )
    yx, yy, yr = cx + s(12), cy - s(8), s(25)
    d.ellipse((yx - yr, yy - yr, yx + yr, yy + yr), fill=(255, 176, 32, 255))
    hr = s(8)
    d.ellipse(
        (yx - yr * 0.42 - hr, yy - yr * 0.42 - hr, yx - yr * 0.42 + hr, yy - yr * 0.42 + hr),
        fill=(255, 214, 130, 255),
    )

    # 반짝이
    star(d, s(132), s(132), s(26))
    star(d, s(192), s(96), s(14))
    star(d, s(398), s(140), s(18))
    d.ellipse((s(414), s(196), s(428), s(210)), fill=(255, 255, 255, 210))

    # 접시 그림자 느낌 (팬 아래 옅은 그림자)
    shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.ellipse(
        (cx - r * 1.02, cy - r * 0.78, cx + r * 1.02, cy + r * 1.12),
        fill=(150, 42, 10, 60),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(s(14)))
    art.alpha_composite(shadow)
    art.alpha_composite(layer)

    if maskable:
        # maskable: 원형/스퀘어 마스크에서 잘리지 않게 여백 확보 → 배경 위에 80% 크기로 배치
        bg = gradient(S, (255, 186, 92), (255, 107, 61), (232, 66, 32)).convert("RGBA")
        inner = art.resize((int(S * 0.82), int(S * 0.82)), Image.LANCZOS)
        bg.alpha_composite(inner, (int(S * 0.09), int(S * 0.09)))
        out = bg
    else:
        out = art
        out.putalpha(rounded_mask(S, int(s(112))))

    return out.resize((size, size), Image.LANCZOS)


JOBS = [
    ("icon-192.png", 192, False),
    ("icon-512.png", 512, False),
    ("apple-touch-icon.png", 180, False),
    ("icon-maskable-512.png", 512, True),
]

if __name__ == "__main__":
    for name, size, maskable in JOBS:
        img = render(size, maskable)
        img.save("icons/" + name)
        print("saved icons/" + name, img.size)
