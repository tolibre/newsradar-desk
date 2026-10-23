# 뉴스레이다 · 정책부

CBS 정책부장용 보고 준비 페이지. 경제정책팀·사회정책팀 열 명의 뉴스레이다 판에서 **핵심 사안만** 모은다(0-74).

- 페이지: https://tolibre.github.io/newsradar-desk/ (→ `/live/`)
- 보고: 업무일 09:00 · 14:00 (다른 판과 같은 구간)

## 무엇을 모으나

| | |
|---|---|
| 범위 | 경제정책팀(김승모·김광일·서민선·이승훈·최창민) + 사회정책팀(김민재·양형욱·정다운·김동빈·박종환) 판의 **본 섹션** — 휴일 특근 당직·본인 기사·CBS 섹션은 뺀다 |
| 기준 | 사안 묶음('보고 전체' 탭 단위)에 [단독]이 있거나, 핵심매체(원본 check와 같은 목록) 3곳 이상이 같이 쓴 것. 각 판이 접어 둔 묶음(관련 약함 등)은 [단독]이 아니면 뺀다 |
| 노컷 | 기출고면 원래 판처럼 '노컷 기출고' 줄(쓴 기자), 아니면 '노컷 미출고'와 이유(○○ 단독 / 핵심매체 N곳) |
| 중복 | 같은 기사가 두 판에 걸리면 먼저 나온 섹션에만. 기획예산처는 김승모 판 것 |

새로 검색하지 않는다(네이버 호출 0). 각 판 저장소의 `docs/live/data.json`을 git으로 받아 합친다 — `tools/build_desk.py`.

## 코드

- `render_page.py`(화면)·`news_monitor.py`(라이브러리, 원본 그대로)는 `tools/make_variant.py`가 원본에서 생성한다. 직접 고치지 말 것.
- 판이 늘거나 순서를 바꾸려면 `tools/build_desk.py`의 `PAGES`와 `tools/make_variant.py`의 `GROUP_ORDER`(보고 양식 순서)를 같이 고친다.

```
git clone --depth 1 https://github.com/tolibre/news-monitor /tmp/nm
python tools/make_variant.py /tmp/nm .
python tools/build_desk.py --local <열 저장소가 있는 폴더>   # 시험
```

## 운영 (cron-job.org → workflow_dispatch)

URL `https://api.github.com/repos/tolibre/newsradar-desk/actions/workflows/newsradar-desk.yml/dispatches`, POST, 헤더는 다른 판 잡과 같음
(PAT `news-monitor-cron`에 이 저장소 추가 필요). Secrets 없음. Pages: main / docs.

| 잡 | 스케줄 | 이유 |
|---|---|---|
| desk-build | `10 * * * *` | 각 판 정시 수집(약 3~5분)이 끝난 뒤 |
| desk-precut | `35 8,13 * * 1-5` | 각 판 08:25·13:25 수집 뒤 — 09:00·14:00 보고 직전 |
