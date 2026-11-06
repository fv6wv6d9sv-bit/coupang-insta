# 쿠팡 파트너스 → 인스타그램 자동 게시

매일 정해진 시간에 GitHub Actions가 `keywords.txt`의 키워드를 순서대로 골라
쿠팡 상품을 검색하고, 인스타그램에 캐러셀로 게시합니다.
상품 링크는 GitHub Pages(`docs/index.html`)에 모아 프로필 링크로 씁니다.

## GitHub 설정 (휴대폰 브라우저로도 가능)
1. **Secrets 등록**: Settings > Secrets and variables > Actions > New repository secret
   - `COUPANG_ACCESS_KEY`, `COUPANG_SECRET_KEY`, `IG_USER_ID`, `IG_ACCESS_TOKEN`
   - (선택, Variables 탭) `COUPANG_SUB_ID`, `LINK_PAGE_TITLE`
2. **Pages 켜기**: Settings > Pages > Source: Deploy from a branch > `main` / `/docs`
   → 주소(`https://아이디.github.io/저장소이름/`)를 인스타 프로필 링크에 등록
3. **테스트**: Actions > 인스타그램 자동 게시 > Run workflow (publish 체크 해제 시 미리보기만)

## 바꾸기
- 키워드: `keywords.txt` 수정
- 게시 시간: `.github/workflows/post.yml`의 `cron` (UTC 기준, 한국시간 -9시간)

## 로컬 실행
```bash
pip install -r requirements.txt
cp .env.example .env
python main.py "무선 이어폰" --demo
python main.py --keywords-file keywords.txt --publish
```

## 주의
- 인스타 캡션 링크는 클릭되지 않으므로 Pages 링크 페이지를 프로필에 거세요.
- Meta 액세스 토큰은 종류에 따라 만료됩니다(장기 사용자 토큰 약 60일). 만료되지 않는
  페이지 토큰이나 시스템 사용자 토큰을 쓰거나, 만료 전에 Secret을 갱신하세요.
  게시가 실패하면 GitHub가 이메일로 알려줍니다.
- 광고 고지 문구는 캡션과 링크 페이지에 자동 포함됩니다. 지우지 마세요.
- 같은 내용을 과하게 반복 게시하면 계정이 제한될 수 있습니다.
