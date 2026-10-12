#!/usr/bin/env python3
"""숏 드라마 릴스(5컷, ~15초) 카드 HTML 생성기.

usage: gen_short.py <story.json> <out.html> <durations.json>

2026-10-12 진단: 평균 시청 시간이 1.7초(34초 영상에서도, 11초 영상에서도 동일) → 첫 장면에서 90% 이탈.
그래서 34초 10컷 드라마(gen_drama.py)를 5컷 ~15초로 줄이고, 첫 컷은 큰 글씨 3줄만 둔다.
- 컷 구성: ① 훅(코랄) ② 문제 대화(흰) ③ 해결 비법(흰, '저장 필수') ④ 결과 화면(흰) ⑤ CTA(검정, 자동)
- "STORY n/N" 같은 길이 표시는 제거 (긴 영상처럼 보여 이탈을 부름)
- 컷 2~4 하단에 댓글 키워드 안내 바 (CTA 가 34초 지점이라 아무도 못 보던 문제 보완)
- 컷별 노출 시간은 글자 수로 계산 (읽을 시간 확보), 합계가 한도를 넘으면 에러 → 문장을 줄여 다시 실행
- 스키마는 pipeline/sample/story_short_*.json 참고
"""
import html
import json
import sys

from gen_drama import CLS_OK, CSS as BASE_CSS

N = 5
MAX_TOTAL = 17.0   # 크로스페이드(0.35s x 4) 제외 후 영상 길이 한도(초)
FADE = 0.35
BAR = '댓글 "모음집" → 꿀팁 PDF 받기'

CSS = BASE_CSS + """
.hook .big{font-size:36px;line-height:1.22;letter-spacing:-.02em}
.hook .hlw{padding:2px 8px 4px}
.chip{border:1.5px solid rgba(255,255,255,.85);border-radius:999px;padding:2px 9px;font-family:'Noto Sans KR','Malgun Gothic',sans-serif;font-size:11px;letter-spacing:0;opacity:1;text-transform:none}
.has-bar{padding-bottom:62px}
.trick{flex:1;display:flex;flex-direction:column;justify-content:center;gap:18px}
.trick .chat{flex:0 0 auto;margin-top:0}
.trick .badge{margin-top:0}
.ctabar{position:absolute;left:24px;right:24px;bottom:24px;background:var(--ink);color:var(--sun);font-size:11.5px;font-weight:900;text-align:center;padding:6px 10px;border-radius:999px}
"""

errors = []


def check(label, text, limit):
    for ln in str(text).split("\n"):
        if len(ln) > limit:
            errors.append(f"{label}: '{ln}' 가 {len(ln)}자 (한도 {limit}자)")


def esc(t):
    return html.escape(str(t)).replace("\n", "<br>")


def nchars(*parts):
    return sum(len(str(p).replace("\n", "").replace(" ", "")) for p in parts)


def card(bg, scene, inner, right="", bar=True, extra=""):
    sc = f'<div class="scene">{esc(scene)}</div>' if scene else ""
    rt = f'<span class="chip">{esc(right)}</span>' if right else "<span></span>"
    cls = f"card {bg}" + (" has-bar" if bar else "") + (f" {extra}" if extra else "")
    b = f'<div class="ctabar">{esc(BAR)}</div>' if bar else ""
    return (f'<section class="{cls}"><div class="brand"><span>WORKMASTER90</span>{rt}</div>{sc}{inner}{b}</section>\n')


def chat(cast, msgs, label):
    if len(msgs) != 2:
        errors.append(f"{label}: 말풍선은 정확히 2개여야 함 (현재 {len(msgs)})")
    rows = []
    for who, text in msgs:
        if who not in cast:
            errors.append(f"{label}: cast 에 없는 화자 '{who}'")
            continue
        check(f"{label} 말풍선", text, 13)
        if len(str(text).split("\n")) > 2:
            errors.append(f"{label}: 말풍선은 2줄 이하")
        c = cast[who]
        me = who == "me"
        al = ' style="text-align:right"' if me else ""
        rows.append(f'<div class="msg{" me" if me else ""}"><div class="av {c["cls"]}">{esc(c["av"])}</div><div>'
                    f'<div class="who"{al}>{esc(c["name"])}</div><div class="bub">{esc(text)}</div></div></div>')
    return '<div class="chat">' + "".join(rows) + "</div>"


def secs(chars, lo=2.4, hi=4.5):
    return round(min(hi, max(lo, 1.0 + chars / 12)), 1)


def build(s):
    cast = {k: dict(v) for k, v in s["cast"].items()}
    cast["me"]["cls"] = "me"
    for k, v in cast.items():
        v.setdefault("cls", "sen")
        if k != "me" and v["cls"] not in CLS_OK:
            errors.append(f"cast.{k}.cls '{v['cls']}' 는 {sorted(CLS_OK)} 중 하나여야 함")
        check(f"cast.{k}.av", v["av"], 4)
    if not str(s.get("topic", "")).strip():
        errors.append("topic (오늘 주제 한 줄) 이 필요함")

    cards, dur = [], []

    # ① 훅 — 첫 1.5초 안에 읽혀야 한다: 3줄, 줄당 7자
    h = s["hook"]
    if len(h["lines"]) != 3:
        errors.append("hook.lines 는 정확히 3줄")
    check("hook", "\n".join(h["lines"]), 7)
    check("hook.label", h["label"], 8)
    check("hook.foot", h["foot"], 22)
    lines = "<br>".join(f'<em class="hlw">{esc(x)}</em>' if i == h["hl"] else esc(x) for i, x in enumerate(h["lines"]))
    cards.append(card("bg-coral", "", f'<div class="big">{lines}</div><div class="foot">{esc(h["foot"])}</div>',
                      right=h["label"], bar=False, extra="hook"))
    dur.append(2.4)

    # ② 문제 상황 대화
    b = s["s2"]
    cards.append(card("bg-paper", b["scene"], chat(cast, b["msgs"], "s2")))
    dur.append(secs(nchars(*[m[1] for m in b["msgs"]])))

    # ③ 해결 비법 (단축키/프롬프트/사이트 이름)
    k = s["s3"]
    who = cast.get(k["who"])
    if not who:
        errors.append(f"s3: cast 에 없는 화자 '{k['who']}'")
        who = cast["me"]
    check("s3.title", k["title"], 14)
    check("s3.lines", "\n".join(k["lines"]), 15)
    if not 2 <= len(k["lines"]) <= 3:
        errors.append("s3.lines 는 2~3줄")
    body = f'<b>{esc(k["title"])}</b><br>' + "<br>".join(esc(x) for x in k["lines"])
    inner = (f'<div class="trick"><div class="chat"><div class="msg"><div class="av {who["cls"]}">{esc(who["av"])}</div>'
             f'<div class="bub mono">{body}</div></div></div><span class="badge">저장 필수</span></div>')
    cards.append(card("bg-paper", k["scene"], inner))
    dur.append(secs(nchars(k["title"], *k["lines"]) + 6))

    # ④ 결과 화면 (예시)
    d = s["s4"]
    check("s4.foot", d.get("foot", ""), 22)
    if "(예시)" not in d["tag"]:
        errors.append("s4.tag 에는 반드시 '(예시)' 포함")
    if d["kind"] == "box":
        if not 2 <= len(d["rows"]) <= 3:
            errors.append("s4.rows 는 2~3개")
        for r in d["rows"]:
            check("s4 항목", r[0], 8)
            check("s4 설명", r[1], 12)
        inner = f'<div class="box"><div class="t">{esc(d["tag"])}</div>' + "".join(
            f'<p><mark>{esc(r[0])}</mark> {esc(r[1])}</p>' for r in d["rows"]) + "</div>"
        txt = [x for r in d["rows"] for x in r]
    else:
        if len(d["head"]) not in (2, 3) or not 2 <= len(d["rows"]) <= 3:
            errors.append("s4 table: head 2~3칸, rows 2~3줄")
        for r in d["rows"] + [d["head"]]:
            if len(r) != len(d["head"]):
                errors.append("s4 table: 모든 줄의 칸 수가 head 와 같아야 함")
            for x in r:
                check("s4 칸", x, 10)
        th = "".join(f'<th>{esc(x)}<span class="tri"></span></th>' for x in d["head"])
        trs = "".join("<tr>" + "".join(f"<td>{esc(x)}</td>" for x in r) + "</tr>" for r in d["rows"])
        inner = f'<div class="box"><div class="t">{esc(d["tag"])}</div><table><tr>{th}</tr>{trs}</table></div>'
        txt = list(d["head"]) + [x for r in d["rows"] for x in r]
    foot = f'<div class="foot">{esc(d["foot"])}</div>' if d.get("foot") else ""
    cards.append(card("bg-paper", d["scene"], inner + foot))
    dur.append(secs(nchars(*txt, d.get("foot", ""))))

    # ⑤ CTA — 댓글 키워드 '모음집' 은 ManyChat 플로우와 맞물려 있으므로 바꾸지 말 것
    cards.append(card("bg-ink", "", '<div class="cta">꿀팁 15개<br>PDF로 보내드려요<br><span class="kw">댓글에 "모음집"</span></div>'
                      '<div class="foot">@workmaster90 팔로우하면 매일 알려드려요</div>', bar=False))
    dur.append(2.8)

    total = round(sum(dur) - (N - 1) * FADE, 2)
    if total > MAX_TOTAL:
        errors.append(f"영상이 {total}초 (한도 {MAX_TOTAL}초) — s2/s3/s4 글자를 줄이세요 (컷별 초: {dur})")
    return cards, dur, total


def main():
    story, out, dur_path = sys.argv[1], sys.argv[2], sys.argv[3]
    s = json.load(open(story, encoding="utf-8"))
    try:
        cards, dur, total = build(s)
    except KeyError as e:
        sys.exit(f"story.json 에 필수 항목 없음: {e}")
    if errors:
        sys.exit("story.json 수정 필요:\n- " + "\n- ".join(errors))
    assert len(cards) == N
    doc = ('<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>숏 드라마 릴스</title><style>'
           + CSS + '</style></head><body><div class="rail">\n' + "".join(cards) + "</div></body></html>")
    open(out, "w", encoding="utf-8").write(doc)
    json.dump(dur, open(dur_path, "w", encoding="utf-8"))
    print(f"short html -> {out} ({N} cards, {total}s, cut seconds {dur})")


if __name__ == "__main__":
    main()
