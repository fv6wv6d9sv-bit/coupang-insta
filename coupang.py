"""쿠팡 파트너스 Open API 클라이언트 (상품 검색, 딥링크 생성)."""

from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import requests

DOMAIN = "https://api-gateway.coupang.com"
BASE = "/v2/providers/affiliate_open_api/apis/openapi"


@dataclass
class Product:
    name: str
    price: int
    image: str
    url: str  # 파트너스 수익 링크
    is_rocket: bool = False


def make_authorization(
    method: str, path: str, query: str, access_key: str, secret_key: str, now: float | None = None
) -> str:
    """쿠팡 CEA HMAC-SHA256 서명 헤더를 만든다. query는 '?' 없이 전달."""
    signed_date = time.strftime("%y%m%dT%H%M%SZ", time.gmtime(now))
    message = signed_date + method + path + query
    signature = hmac.new(secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()
    return (
        f"CEA algorithm=HmacSHA256, access-key={access_key}, "
        f"signed-date={signed_date}, signature={signature}"
    )


class CoupangClient:
    def __init__(self, access_key: str, secret_key: str, session: requests.Session | None = None):
        self.access_key = access_key
        self.secret_key = secret_key
        self.session = session or requests.Session()

    def _request(self, method: str, path: str, params: dict | None = None, body: dict | None = None) -> dict:
        query = urlencode(params or {})
        headers = {
            "Authorization": make_authorization(method, path, query, self.access_key, self.secret_key),
            "Content-Type": "application/json;charset=UTF-8",
        }
        url = DOMAIN + path + (f"?{query}" if query else "")
        resp = self.session.request(method, url, headers=headers, json=body, timeout=30)
        try:
            data = resp.json()
        except ValueError:
            resp.raise_for_status()
            raise
        if resp.status_code >= 400 or str(data.get("rCode", "0")) != "0":
            raise RuntimeError(f"쿠팡 API 오류 ({resp.status_code}): {data}")
        return data

    def search(self, keyword: str, limit: int = 5, sub_id: str | None = None) -> list[Product]:
        """키워드로 상품 검색 (limit 최대 10)."""
        params: dict = {"keyword": keyword, "limit": max(1, min(limit, 10))}
        if sub_id:
            params["subId"] = sub_id
        data = self._request("GET", f"{BASE}/products/search", params=params)
        items = (data.get("data") or {}).get("productData") or []
        return [
            Product(
                name=p["productName"],
                price=int(p.get("productPrice") or 0),
                image=p["productImage"],
                url=p["productUrl"],
                is_rocket=bool(p.get("isRocket")),
            )
            for p in items
        ]

    def deeplink(self, coupang_urls: list[str]) -> list[str]:
        """일반 쿠팡 상품 URL을 파트너스 단축 링크로 변환."""
        data = self._request("POST", f"{BASE}/v1/deeplink", body={"coupangUrls": coupang_urls})
        return [d["shortenUrl"] for d in data.get("data", [])]
