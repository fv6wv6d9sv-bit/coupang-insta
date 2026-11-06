import hashlib
import hmac
from unittest.mock import MagicMock

from caption import DISCLOSURE, MAX_CAPTION, build_caption
from coupang import CoupangClient, Product, make_authorization
from instagram import InstagramClient


def resp(data, code=200):
    r = MagicMock(status_code=code)
    r.json.return_value = data
    return r


def test_signature_format():
    now = 1700000000  # 2023-11-14 22:13:20 UTC
    h = make_authorization("GET", "/p", "a=1", "AK", "SK", now=now)
    msg = "231114T221320Z" + "GET" + "/p" + "a=1"
    sig = hmac.new(b"SK", msg.encode(), hashlib.sha256).hexdigest()
    assert h == f"CEA algorithm=HmacSHA256, access-key=AK, signed-date=231114T221320Z, signature={sig}"


def test_search_parses_products():
    s = MagicMock()
    s.request.return_value = resp({"rCode": "0", "data": {"productData": [
        {"productName": "이어폰", "productPrice": 1000, "productImage": "i", "productUrl": "u", "isRocket": True}]}})
    ps = CoupangClient("a", "b", session=s).search("이어폰", 50)
    assert ps == [Product("이어폰", 1000, "i", "u", True)]
    url = s.request.call_args.args[1]
    assert "limit=10" in url and "keyword=%EC%9D%B4" in url


def test_caption_has_disclosure_and_limit():
    ps = [Product("상품" * 30, 12345, "i", "u")] * 10
    c = build_caption("무선 이어폰", ps, ["이어폰"] * 40)
    assert DISCLOSURE in c and "12,345원" in c and "#무선이어폰" in c
    assert len(c) <= MAX_CAPTION


def test_carousel_flow():
    s = MagicMock()
    ids = iter(["c1", "c2", "parent", "post"])
    s.post.side_effect = lambda url, data, timeout: resp({"id": next(ids)})
    s.get.return_value = resp({"status_code": "FINISHED"})
    ig = InstagramClient("123", "tok", session=s, poll_interval=0)
    assert ig.publish_carousel(["a.jpg", "b.jpg"], "cap") == "post"
    parent = s.post.call_args_list[2].kwargs["data"]
    assert parent["media_type"] == "CAROUSEL" and parent["children"] == "c1,c2"
    assert s.post.call_args_list[3].args[0].endswith("/123/media_publish")


def test_publish_flow_updates_page(tmp_path, monkeypatch):
    import json

    import main

    kw = tmp_path / "k.txt"
    kw.write_text("# 주석\n이어폰\n보조배터리\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    for k in ["COUPANG_ACCESS_KEY", "COUPANG_SECRET_KEY", "IG_USER_ID", "IG_ACCESS_TOKEN"]:
        monkeypatch.setenv(k, "x")
    searched = []
    monkeypatch.setattr(main.CoupangClient, "search", lambda self, k, n, sub_id=None: searched.append(k) or main.SAMPLE)
    monkeypatch.setattr(main.InstagramClient, "publish_carousel", lambda self, urls, cap: "m1")

    out = str(tmp_path / "docs")
    assert main.main(["--keywords-file", str(kw), "--publish", "--out", out]) == 0
    assert main.main(["--keywords-file", str(kw), "--publish", "--out", out]) == 0
    assert searched == ["이어폰", "보조배터리"]
    posts = json.loads((tmp_path / "docs/posts.json").read_text(encoding="utf-8"))
    assert [p["media_id"] for p in posts] == ["m1", "m1"]
    page = (tmp_path / "docs/index.html").read_text(encoding="utf-8")
    assert page.index("보조배터리") < page.index("이어폰")  # 최신순
    assert "link.coupang.com/a/sample1" in page


def test_instagram_login_token_autodetects_host_and_user_id(monkeypatch):
    monkeypatch.delenv("IG_GRAPH_BASE", raising=False)
    s = MagicMock()
    s.get.return_value = resp({"user_id": "1789", "username": "me"})
    ig = InstagramClient(None, "IGAAxyz", session=s)
    assert ig.user_id == "1789"
    assert s.get.call_args.args[0] == "https://graph.instagram.com/v23.0/me"
    assert InstagramClient("1", "EAAxyz", session=s).base.startswith("https://graph.facebook.com/")
