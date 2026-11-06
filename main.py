"""쿠팡 파트너스 상품 → 인스타그램 게시 자동화.

예시:
  python main.py "무선 이어폰" --demo              # 키 없이 샘플로 미리보기
  python main.py "무선 이어폰" --count 5            # 실제 검색, 게시는 안 함
  python main.py "무선 이어폰" --count 5 --publish  # 인스타그램에 캐러셀 게시
  python main.py --keywords-file keywords.txt --publish   # 키워드를 돌아가며 자동 선택
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path

from caption import build_caption, build_link_page
from coupang import CoupangClient, Product
from instagram import InstagramClient

SAMPLE = [
    Product("샘플 무선 블루투스 이어폰 노이즈캔슬링", 39900, "https://example.com/1.jpg", "https://link.coupang.com/a/sample1", True),
    Product("샘플 오픈형 이어폰 초경량 생활방수", 25900, "https://example.com/2.jpg", "https://link.coupang.com/a/sample2"),
    Product("샘플 게이밍 저지연 무선 이어버드", 49000, "https://example.com/3.jpg", "https://link.coupang.com/a/sample3", True),
]


def load_env(path: str = ".env") -> None:
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def need(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        sys.exit(f"환경변수 {name} 가 없습니다. (GitHub: Settings > Secrets and variables > Actions)")
    return v


def load_posts(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def pick_keyword(keywords_file: str, posts: list[dict]) -> str:
    """키워드 목록을 게시 횟수 기준으로 순서대로 돌아가며 선택."""
    lines = Path(keywords_file).read_text(encoding="utf-8").splitlines()
    keywords = [k.strip() for k in lines if k.strip() and not k.strip().startswith("#")]
    if not keywords:
        sys.exit(f"{keywords_file} 에 키워드가 없습니다.")
    return keywords[len(posts) % len(keywords)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="쿠팡 파트너스 → 인스타그램 자동 게시")
    ap.add_argument("keyword", nargs="?", help="검색 키워드 (예: 무선 이어폰)")
    ap.add_argument("--keywords-file", help="키워드 목록 파일 (한 줄에 하나, 순서대로 사용)")
    ap.add_argument("--count", type=int, default=5, help="상품 수 (1~10, 기본 5)")
    ap.add_argument("--tags", nargs="*", default=[], help="추가 해시태그")
    ap.add_argument("--publish", action="store_true", help="실제로 인스타그램에 게시 (없으면 미리보기만)")
    ap.add_argument("--reel-video-url", help="공개 접근 가능한 mp4 URL을 주면 릴스로 게시")
    ap.add_argument("--demo", action="store_true", help="API 키 없이 샘플 데이터로 미리보기")
    ap.add_argument("--out", default="docs", help="링크 페이지/기록 폴더 (GitHub Pages용, 기본 docs)")
    ap.add_argument("--title", default=os.environ.get("LINK_PAGE_TITLE", "추천템 모음"), help="링크 페이지 제목")
    args = ap.parse_args(argv)
    load_env()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    posts_path = out / "posts.json"
    posts = load_posts(posts_path)

    keyword = args.keyword or (args.keywords_file and pick_keyword(args.keywords_file, posts))
    if not keyword:
        ap.error("키워드 또는 --keywords-file 이 필요합니다")

    if args.demo:
        products = SAMPLE[: args.count]
    else:
        cp = CoupangClient(need("COUPANG_ACCESS_KEY"), need("COUPANG_SECRET_KEY"))
        products = cp.search(keyword, args.count, sub_id=os.environ.get("COUPANG_SUB_ID") or None)
    if not products:
        print(f"'{keyword}' 검색 결과가 없습니다.")
        return 1

    caption = build_caption(keyword, products, args.tags)
    new_post = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "keyword": keyword,
        "products": [asdict(p) for p in products],
    }

    print("=" * 40, "\n캡션 미리보기\n" + "=" * 40)
    print(caption)
    print("\n이미지:", *[p.image for p in products], sep="\n  ")

    if not args.publish or args.demo:
        preview = out / "preview.html"
        preview.write_text(build_link_page(posts + [new_post], args.title), encoding="utf-8")
        print(f"\n[미리보기 모드] 링크 페이지 미리보기: {preview}")
        print("게시하려면 --publish 를 붙이세요.")
        return 0

    ig = InstagramClient(os.environ.get("IG_USER_ID") or None, need("IG_ACCESS_TOKEN"))
    if args.reel_video_url:
        media_id = ig.publish_reel(args.reel_video_url, caption)
    elif len(products) >= 2:
        media_id = ig.publish_carousel([p.image for p in products], caption)
    else:
        media_id = ig.publish_image(products[0].image, caption)
    print(f"\n✅ 게시 완료: media id {media_id}")

    new_post["media_id"] = media_id
    posts.append(new_post)
    posts_path.write_text(json.dumps(posts, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "index.html").write_text(build_link_page(posts, args.title), encoding="utf-8")
    print(f"링크 페이지 갱신: {out / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
