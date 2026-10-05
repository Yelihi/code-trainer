# 구조와 이벤트 지도

공개 주소: https://yelihi.github.io/code-trainer/

- `overview.json` / `overview.html`: Archify로 검증한 전체 구조. 원본 소스 커밋을 고정한 구현 링크 포함.
- `overview.svg`: 같은 HTML의 Viewer에서 내보낸 README 미리보기.
- `journeys.json`: 검토한 사용자·운영 이벤트 7개와 실제 함수 참조.
- `build.py` / `scan.mjs`: Python AST와 TypeScript 컴파일러로 이름 있는 제품·운영 함수를 추출. 앱을 실행하거나 DB·환경 파일을 읽지 않음.
- `index.html` / `site.css` / `site.js`: 영역 → 파일 → 함수 → 이벤트·호출을 중첩해서 탐색하는 정적 문서.
- `overview.receipt.json` / `verification.json`: 스펙·HTML SHA-256과 결정적 검사, 브라우저 측정, 별도 시각 검토 결과.

## 갱신

```sh
npm --prefix frontend ci --ignore-scripts
python3 docs/architecture/build.py .architecture-site
python3 -m http.server 8025 --bind 127.0.0.1 --directory .architecture-site
```

함수 목록은 테스트와 문서 생성 도구를 제외한 Git 추적 Python·TypeScript·JavaScript 소스에서 생성합니다. 익명 콜백은 상위 함수의 호출·이벤트로 표시합니다. 연결된 호출은 이름/임포트/컴파일러 심볼로 해석한 저장소 함수이며, 외부 라이브러리·객체 메서드·해석할 수 없는 동적 호출은 별도로 표시합니다. 브라우저 이벤트와 조건 분기는 정적 참조이므로 실제 런타임 추적으로 해석하지 않습니다.

`main` push마다 `.github/workflows/pages.yml`이 현재 커밋의 함수 목록을 생성하고 명시적으로 허용한 문서 파일만 GitHub Pages에 게시합니다. [GitHub 공식 Pages workflow](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)를 따릅니다. 문서 경로와 Pages workflow만 바뀌면 제품 배포는 생략합니다. 함수 연결이 사라지거나 구조도 해시가 검증 기록과 달라지면 문서 빌드가 실패하므로 설명도 함께 갱신해야 합니다.

전체 구조나 이벤트 의미가 바뀌면 `overview.json`, `journeys.json`을 검토하고 Archify로 다시 검증·전달한 뒤 SVG를 내보냅니다. 함수 목록의 소스 SHA는 페이지 상단, 구조도 자체의 기준 SHA는 `overview.json`에 있습니다. 두 갱신 주기를 혼동하지 않습니다.

설명은 한국어이며 Archify의 고정 Viewer UI와 HTML lang은 영어입니다. README는 정적 SVG를 표시하고 클릭하면 GitHub Pages의 탐색 화면으로 이동합니다.

Archify Viewer는 [MIT 라이선스](ARCHIFY-LICENSE.txt)를 따릅니다. HTML에 포함된 JetBrains Mono 글꼴의 OFL 고지도 원본에 보존합니다.
