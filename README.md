# 쿠팡 파트너스 → 유튜브 쇼츠 자동 제작

매일 아침 GitHub가 쿠팡 상품으로 **쇼츠 영상(세로 1080x1920)과 제목·설명**을 만들어
**Releases** 페이지에 올려 둡니다. 휴대폰으로 받아서 유튜브 앱에 올리기만 하면 됩니다.

## 매일 할 일 (1분)
1. 저장소 오른쪽의 **Releases** (또는 `/releases` 주소) → 맨 위 항목
2. **shorts.mp4** 눌러 저장
3. 유튜브 앱 ＋ → 영상 선택 → 제목/설명 붙여넣기 → **유료 프로모션 포함** 켜기 → 업로드

## 상품 넣는 방법 (둘 중 하나)
- **쿠팡 Open API 키가 있으면**: Settings > Secrets and variables > Actions 에
  `COUPANG_ACCESS_KEY`, `COUPANG_SECRET_KEY` 등록 → `keywords.txt` 키워드를 순서대로 자동 검색
- **키가 없으면**: `products.csv` 에 파트너스 '링크 생성'으로 만든 링크를 직접 적기
  (같은 keyword 끼리 한 영상, 위에서부터 하루 한 묶음)

## 링크 페이지 (프로필 링크)
쇼츠 설명란 링크는 눌리지 않으므로, 상품 링크 모음 페이지를 채널 프로필 링크에 겁니다.
Settings > Pages > Deploy from a branch > `main` / `/docs` → `https://아이디.github.io/coupang-insta/`

## 바꾸기
- 만드는 시간: `.github/workflows/shorts.yml` 의 `cron` (UTC 기준)
- 배경음악: 저작권 없는 음악을 `music.mp3` 로 올리면 자동으로 들어감 (또는 유튜브 앱에서 추가)
- 지금 바로 만들기: Actions > 유튜브 쇼츠 영상 만들기 > Run workflow

## 로컬 실행
```bash
pip install -r requirements.txt   # + ffmpeg, 한글 폰트 필요
python make_shorts.py --demo
```

인스타그램 자동 게시(`main.py`, `post.yml`)도 남아 있으며 수동 실행만 켜져 있습니다.
