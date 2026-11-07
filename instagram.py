"""Instagram API 게시 클라이언트 (이미지 / 캐러셀 / 릴스).

두 가지 토큰을 모두 지원:
- 인스타그램 로그인 토큰 (IGAA...로 시작) → graph.instagram.com  ※ 페이스북 페이지 불필요
- 페이스북 로그인 토큰 (EAA...로 시작)   → graph.facebook.com
필요 조건: 인스타그램 '비즈니스' 또는 '크리에이터' 계정.
"""

from __future__ import annotations

import os
import time

import requests

API_VERSION = "v23.0"


def graph_base(token: str) -> str:
    override = os.environ.get("IG_GRAPH_BASE")
    if override:
        return override.rstrip("/")
    host = "graph.instagram.com" if token.startswith("IG") else "graph.facebook.com"
    return f"https://{host}/{API_VERSION}"


class InstagramError(RuntimeError):
    pass


class InstagramClient:
    def __init__(
        self,
        user_id: str | None,
        access_token: str,
        session: requests.Session | None = None,
        poll_interval: float = 5.0,
    ):
        self.token = access_token
        self.base = graph_base(access_token)
        self.session = session or requests.Session()
        self.poll_interval = poll_interval
        self.user_id = user_id or self._lookup_user_id()

    def _lookup_user_id(self) -> str:
        """IG_USER_ID를 안 넣었으면 토큰으로 계정 ID를 조회 (인스타그램 로그인 토큰 전용)."""
        if "graph.instagram.com" in self.base:
            return str(self._call("GET", "me", fields="user_id,username")["user_id"])
        # 페이스북/통합 로그인 토큰(EAA...): 연결된 페이지의 인스타그램 계정을 찾음
        pages = self._call("GET", "me/accounts", fields="instagram_business_account").get("data", [])
        for page in pages:
            ig = page.get("instagram_business_account")
            if ig and ig.get("id"):
                return str(ig["id"])
        raise InstagramError(
            "토큰으로 인스타그램 계정 ID를 찾지 못했습니다. GitHub Secret에 IG_USER_ID 를 직접 넣어 주세요."
        )

    def _call(self, method: str, path: str, **params: object) -> dict:
        params["access_token"] = self.token
        url = f"{self.base}/{path}"
        if method == "GET":
            resp = self.session.get(url, params=params, timeout=60)
        else:
            resp = self.session.post(url, data=params, timeout=60)
        data = resp.json()
        if "error" in data:
            raise InstagramError(data["error"].get("message", str(data["error"])))
        return data

    def _create(self, **params: object) -> str:
        return self._call("POST", f"{self.user_id}/media", **params)["id"]

    def _wait(self, container_id: str, timeout: float = 600) -> None:
        """컨테이너 처리 완료(FINISHED)까지 대기. 영상은 수 분 걸릴 수 있음."""
        deadline = time.monotonic() + timeout
        while True:
            status = self._call("GET", container_id, fields="status_code").get("status_code")
            if status in (None, "FINISHED", "PUBLISHED"):
                return
            if status in ("ERROR", "EXPIRED"):
                raise InstagramError(f"미디어 처리 실패: {container_id} ({status})")
            if time.monotonic() > deadline:
                raise InstagramError(f"미디어 처리 시간 초과: {container_id}")
            time.sleep(self.poll_interval)

    def _publish(self, creation_id: str) -> str:
        self._wait(creation_id)
        return self._call("POST", f"{self.user_id}/media_publish", creation_id=creation_id)["id"]

    def publish_image(self, image_url: str, caption: str) -> str:
        return self._publish(self._create(image_url=image_url, caption=caption))

    def publish_carousel(self, image_urls: list[str], caption: str) -> str:
        if not 2 <= len(image_urls) <= 10:
            raise ValueError("캐러셀은 이미지 2~10장이 필요합니다")
        children = []
        for u in image_urls:
            cid = self._create(image_url=u, is_carousel_item="true")
            self._wait(cid)
            children.append(cid)
        return self._publish(
            self._create(media_type="CAROUSEL", children=",".join(children), caption=caption)
        )

    def publish_reel(self, video_url: str, caption: str, share_to_feed: bool = True) -> str:
        cid = self._create(
            media_type="REELS",
            video_url=video_url,
            caption=caption,
            share_to_feed="true" if share_to_feed else "false",
        )
        return self._publish(cid)
