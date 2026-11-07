"""상품 목록으로 유튜브 쇼츠(1080x1920 세로) 영상을 만든다. Pillow + ffmpeg 사용."""

from __future__ import annotations

import io
import subprocess
import tempfile
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from coupang import Product

W, H = 1080, 1920
FPS = 30
BG_TOP, BG_BOTTOM = (255, 236, 214), (255, 200, 170)
ACCENT = (235, 70, 50)
DARK = (34, 30, 28)
MUTED = (110, 100, 95)

FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "C:/Windows/Fonts/malgunbd.ttf",
]
KR_INDEX = 1  # NotoSansCJK .ttc 안의 한국어(KR) 서체 번호


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            index = KR_INDEX if "NotoSansCJK" in path else 0
            return ImageFont.truetype(path, size, index=index)
    raise RuntimeError("한글 폰트를 찾지 못했습니다. (Ubuntu: sudo apt-get install fonts-noto-cjk)")


def _background() -> Image.Image:
    top = Image.new("RGB", (1, 2), BG_TOP)
    top.putpixel((0, 1), BG_BOTTOM)
    return top.resize((W, H), Image.BILINEAR)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, width: int, max_lines: int) -> list[str]:
    lines: list[str] = []
    line = ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) <= width:
            line = trial
            continue
        if line:
            lines.append(line)
        line = word
        while draw.textlength(line, font=font) > width:  # 공백 없는 긴 단어 자르기
            cut = len(line)
            while cut > 1 and draw.textlength(line[:cut], font=font) > width:
                cut -= 1
            lines.append(line[:cut])
            line = line[cut:]
    if line:
        lines.append(line)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while last and draw.textlength(last + "…", font=font) > width:
            last = last[:-1]
        lines[-1] = last + "…"
    return lines


def _center(draw: ImageDraw.ImageDraw, y: int, text: str, font: ImageFont.FreeTypeFont, fill: tuple) -> int:
    """가운데 정렬로 한 줄 그리고 다음 y 반환."""
    box = draw.textbbox((0, 0), text, font=font)
    draw.text(((W - (box[2] - box[0])) / 2, y), text, font=font, fill=fill)
    return y + int((box[3] - box[1]) * 1.35)


def _ad_badge(draw: ImageDraw.ImageDraw) -> None:
    f = _font(34)
    text = "광고 · 쿠팡 파트너스 활동으로 수수료를 받습니다"
    tw = draw.textlength(text, font=f)
    x, y = (W - tw) / 2, 90
    draw.rounded_rectangle((x - 24, y - 12, x + tw + 24, y + 52), 30, fill=(255, 255, 255))
    draw.text((x, y), text, font=f, fill=MUTED)


def fetch_image(url: str) -> Image.Image | None:
    if not url:
        return None
    if not url.startswith(("http://", "https://")):  # 저장소 안의 이미지 파일
        path = Path(url)
        return Image.open(path).convert("RGB") if path.exists() else None
    try:
        resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        return Image.open(io.BytesIO(resp.content)).convert("RGB")
    except Exception as exc:  # 이미지가 없어도 영상은 만든다
        print(f"  ! 이미지 불러오기 실패 ({exc.__class__.__name__}): {url}")
        return None


def intro_slide(keyword: str, count: int) -> Image.Image:
    img = _background()
    d = ImageDraw.Draw(img)
    _ad_badge(d)
    y = 640
    for line in _wrap(d, keyword, _font(130), W - 140, 2):
        y = _center(d, y, line, _font(130), DARK)
    y += 30
    y = _center(d, y, f"추천 TOP {count}", _font(150), ACCENT)
    _center(d, y + 80, "끝까지 보고 골라보세요", _font(52), MUTED)
    return img


def product_slide(rank: int, p: Product, photo: Image.Image | None) -> Image.Image:
    img = _background()
    d = ImageDraw.Draw(img)
    _ad_badge(d)

    # 순위 배지
    f_rank = _font(110)
    d.ellipse((W / 2 - 95, 210, W / 2 + 95, 400), fill=ACCENT)
    _center(d, 228, str(rank), f_rank, (255, 255, 255))

    # 상품 사진 카드
    card = (90, 450, W - 90, 450 + 900)
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (card[0], card[1] + 14, card[2], card[3] + 14), 48, fill=(0, 0, 0, 60)
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    img.paste(shadow, (0, 0), shadow)
    d.rounded_rectangle(card, 48, fill=(255, 255, 255))
    inner = (card[2] - card[0] - 80, card[3] - card[1] - 80)
    if photo is not None:
        fitted = ImageOps.contain(photo, inner, Image.LANCZOS)
        img.paste(fitted, (card[0] + 40 + (inner[0] - fitted.width) // 2, card[1] + 40 + (inner[1] - fitted.height) // 2))
    else:
        _center(d, card[1] + 380, "상품 이미지", _font(60), MUTED)

    # 상품명, 가격
    y = card[3] + 60
    f_name = _font(58)
    for line in _wrap(d, p.name, f_name, W - 160, 2):
        y = _center(d, y, line, f_name, DARK)
    y += 20
    price = f"{p.price:,}원" if p.price else "가격은 링크에서 확인"
    y = _center(d, y, price, _font(96), ACCENT)
    if p.is_rocket:
        f = _font(44)
        text = "로켓배송"
        tw = d.textlength(text, font=f)
        d.rounded_rectangle(((W - tw) / 2 - 28, y + 4, (W + tw) / 2 + 28, y + 76), 36, fill=(52, 120, 246))
        d.text(((W - tw) / 2, y + 12), text, font=f, fill=(255, 255, 255))
    return img


def outro_slide() -> Image.Image:
    img = _background()
    d = ImageDraw.Draw(img)
    _ad_badge(d)
    y = 700
    y = _center(d, y, "구매 링크는", _font(120), DARK)
    y = _center(d, y, "프로필 링크에서!", _font(120), ACCENT)
    _center(d, y + 120, "구독 · 좋아요 부탁드려요", _font(60), MUTED)
    return img


def _render_clip(slide: Path, seconds: float, out: Path) -> None:
    frames = int(seconds * FPS)
    vf = (
        f"scale={W * 2}:{H * 2},"
        f"zoompan=z='1+0.06*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d={frames}:s={W}x{H}:fps={FPS},"
        f"fade=t=in:st=0:d=0.25,fade=t=out:st={seconds - 0.25}:d=0.25,format=yuv420p"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(slide), "-vf", vf,
         "-t", str(seconds), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", str(out)],
        check=True,
    )


def build_video(
    keyword: str,
    products: list[Product],
    out_path: str | Path,
    seconds_per_product: float = 3.5,
    music: str | Path | None = None,
) -> Path:
    """쇼츠 영상 생성. 순위는 N위 → 1위 카운트다운 순서."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    slides: list[tuple[Image.Image, float]] = [(intro_slide(keyword, len(products)), 2.5)]
    ranked = list(enumerate(products, 1))
    for rank, p in reversed(ranked):
        slides.append((product_slide(rank, p, fetch_image(p.image)), seconds_per_product))
    slides.append((outro_slide(), 2.5))

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        listing = []
        for i, (img, sec) in enumerate(slides):
            png, clip = tmpdir / f"s{i}.png", tmpdir / f"c{i}.mp4"
            img.save(png)
            _render_clip(png, sec, clip)
            listing.append(f"file '{clip}'")
        (tmpdir / "list.txt").write_text("\n".join(listing))
        total = sum(sec for _, sec in slides)
        audio = (
            ["-stream_loop", "-1", "-i", str(music)]
            if music
            else ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
        )
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(tmpdir / "list.txt"),
             *audio, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
             "-t", str(total), "-movflags", "+faststart", str(out_path)],
            check=True,
        )
    return out_path


def save_preview(keyword: str, products: list[Product], out_dir: str | Path) -> list[Path]:
    """영상 없이 슬라이드 이미지만 저장 (빠른 확인용)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    imgs = [intro_slide(keyword, len(products))]
    imgs += [product_slide(r, p, fetch_image(p.image)) for r, p in reversed(list(enumerate(products, 1)))]
    imgs.append(outro_slide())
    for i, im in enumerate(imgs):
        path = out_dir / f"slide{i}.png"
        im.save(path)
        paths.append(path)
    return paths
