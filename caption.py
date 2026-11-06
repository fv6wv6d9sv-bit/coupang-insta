"""인스타그램 캡션 / 링크 페이지 생성."""

from __future__ import annotations

import html

from coupang import Product

DISCLOSURE = "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
MAX_CAPTION = 2200
MAX_HASHTAGS = 30


def _short(name: str, n: int = 40) -> str:
    return name if len(name) <= n else name[: n - 1] + "…"


def build_hashtags(keyword: str, extra: list[str] | None = None) -> list[str]:
    base = [keyword.replace(" ", ""), "쿠팡추천", "쿠팡파트너스", "추천템", "쇼핑추천"]
    tags: list[str] = []
    for t in base + (extra or []):
        t = t.lstrip("#").replace(" ", "")
        if t and t not in tags:
            tags.append(t)
    return ["#" + t for t in tags[:MAX_HASHTAGS]]


def build_caption(
    keyword: str,
    products: list[Product],
    extra_tags: list[str] | None = None,
    link_hint: str = "👉 구매 링크는 프로필 링크에서 확인하세요!",
) -> str:
    head = f"[광고] {DISCLOSURE}\n\n🛒 {keyword} 추천 TOP {len(products)}\n"
    tail = f"\n{link_hint}\n\n" + " ".join(build_hashtags(keyword, extra_tags))
    lines = []
    for i, p in enumerate(products, 1):
        rocket = " 🚀로켓배송" if p.is_rocket else ""
        lines.append(f"{i}. {_short(p.name)}\n   💰 {p.price:,}원{rocket}")
    body = "\n".join(lines)
    # 2200자 제한: 넘치면 뒤쪽 상품부터 줄임
    while len(head) + len(body) + len(tail) > MAX_CAPTION and lines:
        lines.pop()
        body = "\n".join(lines)
    return head + body + "\n" + tail


def _card(i: int, p: dict) -> str:
    rocket = " · 🚀로켓배송" if p.get("is_rocket") else ""
    return (
        f'<a class="card" href="{html.escape(p["url"])}" target="_blank" rel="sponsored noopener">'
        f'<img src="{html.escape(p["image"])}" alt="" loading="lazy"><div><b>{i}. '
        f"{html.escape(_short(p['name'], 60))}</b><span>{p['price']:,}원{rocket}</span></div></a>"
    )


def build_link_page(posts: list[dict], title: str = "추천템 모음") -> str:
    """프로필 링크(GitHub Pages)용 정적 HTML. posts는 최신순으로 표시."""
    sections = []
    for post in reversed(posts):
        cards = "\n".join(_card(i, p) for i, p in enumerate(post["products"], 1))
        sections.append(
            f"<section><h3>🛒 {html.escape(post['keyword'])} <small>{html.escape(post['time'][:10])}</small></h3>"
            f"{cards}</section>"
        )
    body = "\n".join(sections) or "<p>아직 게시물이 없습니다.</p>"
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><style>
body{{font-family:system-ui,sans-serif;max-width:480px;margin:0 auto;padding:16px;background:#fafafa;color:#222}}
.notice{{font-size:12px;color:#666;background:#eee;padding:8px;border-radius:8px}}
h3 small{{font-weight:normal;color:#888;font-size:12px}}
.card{{display:flex;gap:12px;align-items:center;background:#fff;border-radius:12px;padding:10px;margin:10px 0;
text-decoration:none;color:inherit;box-shadow:0 1px 3px #0001}}
.card img{{width:72px;height:72px;object-fit:cover;border-radius:8px;flex:none}}
.card span{{display:block;color:#e44;margin-top:4px}}
</style></head><body><h2>{html.escape(title)}</h2>
<p class="notice">{DISCLOSURE}</p>
{body}
</body></html>
"""
