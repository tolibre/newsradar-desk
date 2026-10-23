#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""뉴스레이다 정책부장판 — 경제정책팀·사회정책팀 열 판의 화면 데이터에서 핵심 묶음만 모아 한 페이지로(0-74).

사용자(2026-10-23 10:40): "전체 출입처의 핵심 기사만 묶을 페이지를 별도로 하나 만들어도 좋겠어. 정책부장용."
  범위 = 두 팀 10명 전체 / 기준 = [단독] + 여러 매체가 받은 사안 / 노컷 출고 여부 표시(미출고 강조) / 09:00·14:00 보고.

새로 검색하지 않는다(네이버 호출 0) — 각 판이 매시 게시하는 docs/live/data.json을 읽어 합친다.
  - 섹션 = 각 판의 **본 섹션**만(휴일 특근 당직·본인 기사·CBS 섹션은 뺀다). 순서 = PAGES 순서 × 각 판 섹션 순서.
    같은 섹션 이름이 두 판에 있으면(기획예산처: 김승모·이승훈) 앞 판 것만 쓴다.
  - 선별 단위 = '보고 전체' 탭의 사안 묶음(data['reports'][i]['all']). 묶음 안에 [단독]이 있거나, 묶음 기사 매체 중
    핵심매체(원본 CORE_MEDIA_*, check 0-41과 같은 목록)가 3곳 이상이면 남긴다(CORE_MIN).
    원본 check는 같은 제목 전재 매체까지 DB에서 세지만 화면 데이터엔 전재 매체 목록이 없다 — 원본판 재생 277묶음 중 275개가
    같은 판정(10/23, 다른 2개는 전재 매체만으로 3곳을 넘은 것).
  - 노컷: 묶음 안에 노컷 기출고(nc)나 노컷 기사가 있으면 기출고 줄이 그대로 뜨고, 없으면 대표 줄에 nm(이유 문구)을 달아
    페이지가 '노컷 미출고' 표시를 그린다(원본 render_page 0-74 자리).
  - 여러 판에 같은 기사가 걸리면(복지부·노동부 공동 발표 등) 보고 안에서 먼저 나온 섹션에만 둔다(링크 기준).
  - 각 판이 접어 둔 묶음(관련 약함·교육청 '다른 지역' — 묶음 기사 전부 wk)은 [단독]이 아니면 고르지 않는다
    (첫 시험에서 '두산연강재단 과학교사 학술시찰' 같은 보도자료가 핵심매체 4곳으로 올라왔다). 고른 묶음은 wk를 지워 전부 펼친다.

  python tools/build_desk.py            # Actions: 각 저장소 data.json을 git으로 받아 docs/live/에 쓴다
  python tools/build_desk.py --local /home/claude   # 시험: 그 폴더의 저장소 사본에서 읽는다
"""
import datetime, json, os, re, subprocess, sys, tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import news_monitor as m      # 원본 그대로 복사본(라이브러리로만 씀: priority_mark·core_media·archive_past_reports)
import render_page as rp      # 생성기가 만든 정책부장판 화면

# (저장소, 기자, 팀) — 순서 = 섹션 순서. 경제정책팀(팀장 김승모 먼저), 사회정책팀(팀장 김민재 먼저).
PAGES = [
    ("newsradar-moef", "김승모", "경제정책팀"),
    ("news-monitor", "김광일", "경제정책팀"),
    ("newsradar-industry", "서민선", "경제정책팀"),
    ("newsradar-budget-agri", "이승훈", "경제정책팀"),
    ("newsradar-land", "최창민", "경제정책팀"),
    ("newsradar-gov", "김민재", "사회정책팀"),
    ("newsradar-climate-culture", "양형욱", "사회정책팀"),
    ("newsradar-welfare", "정다운", "사회정책팀"),
    ("newsradar-labor", "김동빈", "사회정책팀"),
    ("newsradar-education", "박종환", "사회정책팀"),
]
SKIP_GROUPS = {"CBS"}          # 김광일판 회사 기사 섹션 — 정책부 출입처가 아님
CORE_MIN = 3                   # 원본 CHECK_CORE_SPREAD_MIN과 같은 값
NM_DESC = ("같은 사안의 노컷뉴스 기사를 찾지 못한 핵심 묶음입니다. 노컷 기사는 각 기자 판이 모은 기사 안에서만 찾으므로, "
           "출입처 검색어에 안 걸린 노컷 기사가 있으면 기출고인데도 미출고로 보일 수 있습니다.")


def load_pages(local=None):
    out = []
    for repo, who, team in PAGES:
        try:
            if local:
                with open(os.path.join(local, repo, "docs", "live", "data.json"), encoding="utf-8") as f:
                    out.append((repo, who, team, json.load(f)))
                continue
            with tempfile.TemporaryDirectory() as d:
                subprocess.run(["git", "clone", "-q", "--depth", "1", "--filter=blob:none", "--no-checkout",
                                f"https://github.com/tolibre/{repo}", d], check=True, timeout=120)
                txt = subprocess.run(["git", "-C", d, "show", "HEAD:docs/live/data.json"], check=True,
                                     capture_output=True, timeout=120).stdout.decode("utf-8")
                out.append((repo, who, team, json.loads(txt)))
        except Exception as e:      # 한 판이 안 열려도 나머지로 만든다
            print(f"[warn] {repo}: {e}")
    return out


def core_outlet(s):
    """화면 데이터의 매체 이름(일보·신문을 뗀 짧은 이름) → 핵심매체면 그 이름."""
    s = (s or "").strip()
    for cand in (s, s + "일보", s + "신문"):
        if m.core_media(cand):
            return re.sub(r"\s*뉴스$", "", cand)
    return None


def is_nocut(it):
    return bool(it.get("nc")) or "노컷" in (it.get("s") or "")


def build(pages, now):
    base = next((d for r, _w, _t, d in pages if r == "news-monitor"), pages[0][3])
    reports = []
    for brep in base["reports"]:
        seg_ids = [s["id"] for s in brep["segments"]]
        segs = [{k: v for k, v in s.items() if k != "groups"} | {"groups": [], "raw": 0, "n": 0, "dup": 0, "x": 0}
                for s in brep["segments"]]
        all_out = []                      # [{name, c: [[[s,g,c,i], ...], ...]}]
        taken_groups, taken_links = set(), set()
        for repo, who, team, D in pages:
            rep = next((r for r in D["reports"] if r["id"] == brep["id"]), None)
            if not rep:
                continue
            duty = set(D.get("duty") or [])
            own = lambda g: (g not in duty and g not in SKIP_GROUPS and not g.endswith(" 기자") and g not in taken_groups)
            smap = {i: seg_ids.index(s["id"]) for i, s in enumerate(rep["segments"]) if s["id"] in seg_ids}
            keep_cl = {}                  # (page seg, page grp, page clu) → nm 문구 또는 ""
            kept_all = []                 # (group name, [refs])
            for a in rep.get("all", []):
                if not own(a["name"]):
                    continue
                for refs in a["c"]:
                    items = [rep["segments"][s]["groups"][g]["clusters"][c][i] for s, g, c, i in refs]
                    links = {it.get("l") for it in items if it.get("l")}
                    ex = any(it.get("m") == "🔥" for it in items)
                    core = {o for o in (core_outlet(it.get("s")) for it in items) if o}
                    if not (ex or len(core) >= CORE_MIN) or (links & taken_links):
                        continue
                    if not ex and all(it.get("wk") for it in items):
                        continue          # 그 판이 접어 둔 묶음('관련 약함'·교육청 '다른 지역')은 핵심으로 치지 않는다
                    taken_links |= links
                    nm = ""
                    if not any(is_nocut(it) for it in items):
                        exs = sorted({it.get("s") for it in items if it.get("m") == "🔥"})
                        nm = (f"{'·'.join(exs)} 단독" if exs else "") + (" · " if exs and len(core) >= CORE_MIN else "") + \
                             (f"핵심매체 {len(core)}곳" if len(core) >= CORE_MIN else "")
                    for s, g, c, i in refs:
                        keep_cl.setdefault((s, g, c), nm)
                    kept_all.append((a["name"], refs, nm))
            if not kept_all:
                for a in rep.get("all", []):
                    if own(a["name"]):
                        taken_groups.add(a["name"])
                continue
            # 구간 데이터: 남긴 묶음만, 섹션(그룹) 순서는 그 판 그대로
            remap = {}                    # (page s, page g, page c) → (new s, new g, new c)
            gnames = []
            for ps, seg in enumerate(rep["segments"]):
                if ps not in smap:
                    continue
                ns = smap[ps]
                for pg, grp in enumerate(seg["groups"]):
                    if not own(grp["name"]):
                        continue
                    cls = []
                    for pc, clu in enumerate(grp["clusters"]):
                        if (ps, pg, pc) not in keep_cl:
                            continue
                        nm = keep_cl[(ps, pg, pc)]
                        items = []
                        for it in clu:
                            it = {k: v for k, v in it.items() if k != "wk"}
                            if nm:
                                it["nm"] = nm
                            items.append(it)
                        remap[(ps, pg, pc)] = (ns, None, len(cls))
                        cls.append(items)
                    if not cls:
                        continue
                    if grp["name"] not in gnames:
                        gnames.append(grp["name"])
                    n = sum(len(c) for c in cls)
                    dup = sum(1 for c in cls for it in c if it.get("d"))
                    ng = len(segs[ns]["groups"])
                    segs[ns]["groups"].append({"name": grp["name"], "clusters": cls, "n": n, "dup": dup})
                    segs[ns]["n"] += n; segs[ns]["raw"] += n; segs[ns]["dup"] += dup
                    for k, v in list(remap.items()):
                        if k[0] == ps and k[1] == pg and v[1] is None:
                            remap[k] = (v[0], ng, v[2])
            for name, refs, nm in kept_all:
                nrefs = [[*remap[(s, g, c)], i] for s, g, c, i in refs if (s, g, c) in remap]
                if not nrefs:
                    continue
                ent = next((x for x in all_out if x["name"] == name), None)
                if not ent:
                    ent = {"name": name, "c": []}
                    all_out.append(ent)
                ent["c"].append(nrefs)
            for a in rep.get("all", []):
                if own(a["name"]):
                    taken_groups.add(a["name"])
        reports.append({k: v for k, v in brep.items() if k not in ("segments", "all", "byline")}
                       | {"segments": segs, "all": all_out})
    last = max((d.get("last_seen") or "" for _r, _w, _t, d in pages), default="")
    return {"generated": now.isoformat(), "last_seen": last, "reports": reports, "nm": NM_DESC,
            "src": [{"repo": r, "who": w, "team": t, "gen": d.get("generated", "")} for r, w, t, d in pages]}


def main():
    local = sys.argv[sys.argv.index("--local") + 1] if "--local" in sys.argv else None
    now = datetime.datetime.now(m.KST)
    pages = load_pages(local)
    if len(pages) < len(PAGES) // 2:
        raise SystemExit(f"판 데이터를 절반도 못 읽었습니다({len(pages)}/{len(PAGES)}) — 쓰지 않습니다.")
    data = build(pages, now)
    rp.publish_live(data)
    added, removed = m.archive_past_reports(data, now, rp.LIVE_DIR)
    for r in data["reports"]:
        print(r["title"], "| 묶음", sum(len(g["clusters"]) for s in r["segments"] for g in s["groups"]),
              "| 미출고", sum(1 for s in r["segments"] for g in s["groups"] for c in g["clusters"] if c[0].get("nm")))
    print(f"판 {len(pages)}/{len(PAGES)} · 지난 보고 +{added} -{removed}")


if __name__ == "__main__":
    main()
