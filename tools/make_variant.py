#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""뉴스레이다 정책부장판 생성기(0-74).

원본(tolibre/news-monitor)의 render_page.py에서 화면 문구·저장키·보고 양식 순서만 바꿔 쓰고,
news_monitor.py는 **그대로 복사**한다(tools/build_desk.py가 라이브러리로만 쓴다 — 수집·DB 없음).

  python tools/make_variant.py <원본 저장소 경로> [<출력 경로, 기본=이 저장소>]

치환마다 원본 등장 횟수를 검사하고, 다르면 아무 파일도 쓰지 않는다. 함수는 바꾸지 않는다.
"""
import hashlib, os, re, shutil, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

STORE_PREFIX = "nm-desk-"     # 브라우저 저장키 — 다른 판(nm-live-·nm-moef-·…·nm-land-·nm-ba-)과 달라야 한다
# 보고 양식 순서 = 섹션 순서(build_desk.PAGES 순서 × 각 판 섹션). 보고 양식은 이 순서로 출입처별로 나온다.
GROUP_ORDER = ["재경부", "기획예산처", "국가데이터처", "관세청",
               "방미통위", "공정위", "과기정통부", "우주항공청",
               "산업부", "중기부", "개인정보위", "대미투자",
               "농식품부", "국토부",
               "총리실", "행안부", "권익위", "소방청", "인사처", "중수청",
               "기후부", "문체부",
               "복지부", "질병청", "식약처", "성평등부", "국민연금", "건보공단",
               "노동부", "노동", "교육부", "교육청"]
REPORT_ORDER_JS = "[" + ",".join(f"'{g}'" for g in GROUP_ORDER) + "]"
RP = "render_page.py"

REPLACEMENTS = [
    (RP, "var REPORT_ORDER = ['방미통위','공정위','과기정통부','우주항공청'];", f"var REPORT_ORDER = {REPORT_ORDER_JS};", 2, False),
    (RP, "출입처 순서(방미통위 → 공정위 → 과기정통부 → 우주청 → 2진)", "출입처 순서(경제정책팀 → 사회정책팀)", 2, False),
    (RP, "'nm-live-", f"'{STORE_PREFIX}", 6, False),
    (RP, '<button type="button" id="sync" class="sync off"',
         '<button type="button" id="sync" class="sync off" style="display:none"', 1, False),
    (RP, "<title>뉴스레이다</title>", "<title>뉴스레이다 · 정책부</title>", 1, False),
    (RP, "document.title = '뉴스레이다 · ' + r.title;", "document.title = '뉴스레이다(정책부) · ' + r.title;", 1, False),
    # 본인 기사 섹션이 없는 판 — 꼬리말의 '맨 끝 섹션' 설명을 정책부장판 설명으로 바꾼다.
    (RP, r"legendItem\('맨 끝 섹션', '[^']*'\) \+",
         "legendItem('정책부장판', '경제정책팀·사회정책팀 열 판에서 [단독]이 있거나 핵심매체 3곳 이상이 같이 쓴 사안만 모았습니다. 섹션은 각 기자의 출입처 순서입니다(휴일 특근·본인 기사 섹션 없음). 매시 정각 각 판 수집 뒤 10분에 갱신합니다.') +", 1, True),
    (RP, "체크한 기사와 ‘여기까지 확인’은 이 기기에 저장되고, 머리줄 <b>기기 연동</b>을 켜면 다른 기기와 맞춰집니다(내 GitHub 비공개 gist). · <a href=\"../\">최신 다이제스트</a> · <a href=\"../archive/\">지난 다이제스트</a></p>",
         "체크한 기사와 ‘여기까지 확인’은 이 기기(브라우저)에만 저장됩니다 — PC와 폰은 따로 기억합니다.</p>", 1, False),
]
COPY_AS_IS = ["news_monitor.py"]
FORBIDDEN = {RP: ["nm-live-", "기기 연동</b>", "방미통위 → 공정위", "‘김광일 기자’"]}


def md5(b):
    return hashlib.md5(b).hexdigest()


def apply(src):
    with open(os.path.join(src, RP), encoding="utf-8") as f:
        text = f.read()
    errors = []
    for fname, old, new, count, is_re in REPLACEMENTS:
        found = len(re.findall(old, text)) if is_re else text.count(old)
        if found != count:
            errors.append(f"{fname}: {old[:60]!r} — {count}번이어야 하는데 {found}번")
            continue
        text = re.sub(old, lambda _m: new, text) if is_re else text.replace(old, new)
    if errors:
        raise SystemExit("원본이 예상과 달라 생성을 멈춥니다(아무 파일도 쓰지 않음):\n  " + "\n  ".join(errors))
    bad = [f"{p!r}: {l.strip()[:80]}" for l in text.splitlines() for p in FORBIDDEN[RP]
           if p in l and not l.strip().startswith(("#", "//"))]
    if bad:
        raise SystemExit("원본 고유 문자열이 남았습니다:\n  " + "\n  ".join(bad))
    return text


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    src = os.path.abspath(sys.argv[1])
    dst = os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), ".."))
    text = apply(src)
    with open(os.path.join(dst, RP), "w", encoding="utf-8") as f:
        f.write(text)
    for fn in COPY_AS_IS:
        shutil.copyfile(os.path.join(src, fn), os.path.join(dst, fn))
    for fn in [RP] + COPY_AS_IS:
        with open(os.path.join(src, fn), "rb") as a, open(os.path.join(dst, fn), "rb") as b:
            print(f"{fn:18s} 원본 {md5(a.read())} → 생성 {md5(b.read())}")


if __name__ == "__main__":
    main()
