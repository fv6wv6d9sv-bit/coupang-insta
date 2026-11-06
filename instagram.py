"""Instagram Graph API 게시 클라이언트 (이미지 / 캐러셀 / 릴스).

필요 조건: 페이스북 페이지와 연결된 인스타그램 '비즈니스' 또는 '크리에이터' 계정,
instagram_content_publish 권한이 있는 액세스 토큰.
"""

from __future__ import annotations

import os
import time

import requests

GRAPH_BASE = os.environ.get("IG_GRAPH_BASE", "https://graph.facebook.com/v23.0")


class InstagramError(RuntimeError):
    pass


class InstagramClient:
    def __init__(
        self,
        user_id: str,
        access_token: str,
        session: requests.Session | None = None,
        poll_interval: float = 5.0,
    ):
        self.user_id = user_id
        self.token = access_token
        self.session = session or requests.Session()
        self.poll_interval = poll_interval

    def _call(self, method: str, path: str, **params: object) -> dict:
        params["access_token"] = self.token
        url = f"{GRAPH_BASE}/{path}"
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
