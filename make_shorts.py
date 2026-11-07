"""쿠팡 파트너스 상품으로 유튜브 쇼츠 영상 + 제목/설명 만들기.

상품 고르는 방법 (자동 선택):
  1) COUPANG_ACCESS_KEY/SECRET_KEY 가 있으면 → 쿠팡 API 검색 (keywords.txt 순서대로)
  2) 없으면 → products.csv 에 직접 적은 상품 사용

예시:
  python make_shorts.py --demo                 # 샘플로 영상 만들어 보기
  python make_shorts.py                        # 오늘 영상 만들기 (output/)
  python make_shorts.py "무선 이어폰"            # 키워드 지정 (API 모드)
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path

from caption import build_link_page, build_shorts_text
from coupang import CoupangClient, Product
from main import SAMPLE, load_env, load_posts, pick_keyword
from shorts import build_video


def load_csv_groups(path: str) -> list[tuple[str, list[Product]]]:
    """products.csv → [(키워드, 상품목록)] (파일에 나온 순서 유지)."""
    groups: dict[str, list[Product]] = {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = csv.DictReader(line for line in f if line.strip() and not line.lstrip().startswith("#"))
        for row in rows:
            kw, name, link = (row.get(k, "").strip() for k in ("keyword", "name", "link"))
            if not (kw and name and link):
                continue
            price = int("".join(ch for ch in row.get("price", "") if ch.isdigit()) or 0)
            groups.setdefault(kw, []).append(Product(name, price, (row.get("image") or "").strip(), link))
    return list(groups.items())


def choose_products(args: argparse.Namespace, posts: list[dict]) -> tuple[str, list[Product]]:
    if args.demo:
        return args.keyword or "무선 이어폰", SAMPLE[: args.count]
    if os.environ.get("COUPANG_ACCESS_KEY") and os.environ.get("COUPANG_SECRET_KEY"):
        keyword = args.keyword or pick_keyword(args.keywords_file, posts)
        cp = CoupangClient(os.environ["COUPANG_ACCESS_KEY"], os.environ["COUPANG_SECRET_KEY"])
        return keyword, cp.search(keyword, args.count, sub_id=os.environ.get("COUPANG_SUB_ID") or None)
    groups = load_csv_groups(args.products_file) if Path(args.products_file).exists() else []
    if not groups:
        sys.exit(
            "상품이 없습니다. 쿠팡 API 키를 GitHub Secrets에 넣거나, "
            f"{args.products_file} 에 상품을 적어 주세요."
        )
    if args.keyword:
        match = [g for g in groups if g[0] == args.keyword]
        if not match:
            sys.exit(f"{args.products_file} 에 '{args.keyword}' 키워드가 없습니다.")
        return match[0][0], match[0][1][: args.count]
    keyword, products = groups[len(posts) % len(groups)]
    return keyword, products[: args.count]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="쿠팡 파트너스 → 유튜브 쇼츠 영상 만들기")
    ap.add_argument("keyword", nargs="?", help="키워드 (비우면 순서대로 자동 선택)")
    ap.add_argument("--count", type=int, default=5, help="상품 수 (기본 5)")
    ap.add_argument("--keywords-file", default="keywords.txt")
    ap.add_argument("--products-file", default="products.csv")
    ap.add_argument("--music", help="배경음악 mp3 경로 (선택)")
    ap.add_argument("--link-url", default=os.environ.get("LINK_PAGE_URL", ""), help="설명란에 넣을 링크 페이지 주소")
    ap.add_argument("--out", default="output", help="영상/글 저장 폴더")
    ap.add_argument("--docs", default="docs", help="링크 페이지 폴더 (GitHub Pages)")
    ap.add_argument("--record", action="store_true", help="게시 기록과 링크 페이지 갱신")
    ap.add_argument("--demo", action="store_true", help="샘플 상품으로 만들어 보기")
    args = ap.parse_args(argv)
    load_env()

    docs = Path(args.docs)
    posts_path = docs / "posts.json"
    posts = load_posts(posts_path)
    keyword, products = choose_products(args, posts)
    if not products:
        print(f"'{keyword}' 상품을 찾지 못했습니다.")
        return 1

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    print(f"🎬 '{keyword}' 상품 {len(products)}개로 영상 만드는 중...")
    video = build_video(keyword, products, out / "shorts.mp4", music=args.music)
    title, description = build_shorts_text(keyword, products, args.link_url)
    (out / "title.txt").write_text(title, encoding="utf-8")
    (out / "description.txt").write_text(description, encoding="utf-8")
    (out / "release.md").write_text(
        "### 1. 영상 다운로드\n아래 Assets 의 **shorts.mp4** 를 눌러 저장하세요.\n\n"
        f"### 2. 제목 (복사)\n```\n{title}\n```\n\n### 3. 설명 (복사)\n```\n{description}\n```\n\n"
        "### 4. 업로드할 때\n- 유튜브 앱 ＋ → 동영상 업로드 → 저장한 영상 선택\n"
        "- **세부정보 > 유료 프로모션 포함**을 켜 주세요 (광고 표시 의무)\n"
        "- 원하면 앱에서 배경음악(사운드)을 추가하세요\n",
        encoding="utf-8",
    )
    print(f"✅ 영상: {video}\n제목: {title}\n\n{description}")

    if args.record and not args.demo:
        posts.append({"time": time.strftime("%Y-%m-%d %H:%M:%S"), "keyword": keyword,
                      "products": [asdict(p) for p in products]})
        docs.mkdir(parents=True, exist_ok=True)
        posts_path.write_text(json.dumps(posts, ensure_ascii=False, indent=1), encoding="utf-8")
        title_env = os.environ.get("LINK_PAGE_TITLE") or "추천템 모음"
        (docs / "index.html").write_text(build_link_page(posts, title_env), encoding="utf-8")
        print(f"링크 페이지 갱신: {docs / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
