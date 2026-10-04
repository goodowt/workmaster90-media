#!/usr/bin/env python3
"""드라마 릴스(10컷) 카드 HTML 생성기.

usage: gen_drama.py <story.json> <out.html> <durations.json>

루틴(에이전트)은 HTML 을 직접 쓰지 않고 story.json 만 작성한다. 스키마는 pipeline/sample/story_*.json 참고.
- 1번(훅)=코랄, 10번(CTA)=검정, 나머지 8장은 전부 흰 배경 (디자인 확정, 2026-10-04)
- 글자 수가 한도를 넘으면 에러로 종료 → 에이전트가 문장을 줄여서 다시 실행
- 컷별 노출 시간은 durations.json 으로 저장 → render 후 <cards_dir>/durations.json 으로 복사하면 make_reel.py 가 사용
"""
import html
import json
import sys

N = 10
DURATIONS = [2.5, 3.5, 2.5, 3.5, 5.0, 3.5, 4.5, 3.5, 5.5, 3.5]  # 크로스페이드 제외 ≈ 34.4s
CLS_OK = {"boss", "sen", "tea", "fri", "prof"}  # 아바타 색 (나는 항상 'me': 오른쪽·노란 말풍선)

CSS = """
:root{--ink:#141414;--sun:#FFE034;--coral:#FF4B3E;--mint:#00D2A0;--ground:#EDEEF2}
*{box-sizing:border-box}html,body{margin:0}
body{background:var(--ground);font-family:'Noto Sans KR','Malgun Gothic',sans-serif;word-break:keep-all;-webkit-font-smoothing:antialiased}
.rail{display:flex;gap:14px;padding:20px}
.card{flex:0 0 auto;width:320px;aspect-ratio:4/5;border-radius:14px;padding:26px 24px 22px;display:flex;flex-direction:column;position:relative;overflow:hidden;color:var(--ink)}
.bg-coral{background:var(--coral);color:#fff}.bg-ink{background:var(--ink);color:#fff}.bg-paper{background:#fff}
.brand{display:flex;justify-content:space-between;font-family:'IBM Plex Mono',monospace;font-size:10.5px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;opacity:.68}
.scene{font-family:'IBM Plex Mono','Noto Sans KR',monospace;font-size:11px;font-weight:700;letter-spacing:.08em;margin-top:18px;opacity:.6}
h2{font-weight:900;font-size:30px;line-height:1.3;letter-spacing:-.01em;margin:14px 0 0}
.big{font-weight:900;font-size:32px;line-height:1.28;margin:auto 0}
.hl{display:inline-block;font-style:normal;background:var(--sun);color:var(--ink);padding:2px 12px 4px;margin-top:10px;line-height:1.2;border-radius:10px}
.hlw{display:inline-block;font-style:normal;background:#fff;color:var(--coral);padding:2px 12px 4px;margin:6px 0;line-height:1.2;border-radius:10px}
.chat{display:flex;flex-direction:column;gap:12px;margin-top:22px;flex:1;justify-content:center}
.msg{display:flex;align-items:flex-end;gap:8px}.msg.me{flex-direction:row-reverse}
.av{flex:0 0 40px;height:40px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:11px;color:#fff}
.av.boss{background:var(--coral)}.av.me{background:var(--ink)}.av.sen{background:#3b6cff}.av.tea{background:#7a3bff}.av.fri{background:#0a9d7a}.av.prof{background:#e8590c}
.bub{max-width:228px;padding:11px 14px;border-radius:16px;font-size:15px;font-weight:700;line-height:1.45;background:#fff;border:2px solid var(--ink)}
.me .bub{background:var(--sun)}
.bub.mono{font-family:'IBM Plex Mono','Noto Sans KR',monospace;font-size:12.5px;font-weight:600;line-height:1.55;background:#141414;color:#fff;border-color:#141414}
.bub.mono b{color:var(--sun)}
.who{font-size:10.5px;font-weight:700;opacity:.55;margin:0 4px 3px}
.list{margin:22px 0 0;padding:0;list-style:none;display:flex;flex-direction:column;gap:12px}
.list li{display:flex;gap:12px;align-items:flex-start;font-size:17px;font-weight:700;line-height:1.4}
.list .n{flex:0 0 28px;height:28px;border-radius:50%;background:var(--ink);color:var(--sun);display:flex;align-items:center;justify-content:center;font-weight:900;font-size:14px}
.badge{display:inline-block;background:var(--ink);color:var(--sun);font-weight:900;font-size:12px;padding:5px 10px;border-radius:999px;align-self:flex-start;margin-top:14px}
.cta{font-weight:900;font-size:26px;line-height:1.35;margin:auto 0 0}
.kw{display:inline-block;background:var(--sun);color:var(--ink);padding:2px 12px;border-radius:10px;font-size:34px}
.foot{margin-top:auto;font-size:12px;font-weight:700;opacity:.6}
.box{border:2px solid var(--ink);border-radius:14px;padding:14px 16px;margin-top:22px;font-size:14px;font-weight:700;line-height:1.55}
.box .t{font-family:'IBM Plex Mono','Noto Sans KR',monospace;font-size:11px;opacity:.55;margin-bottom:8px}
.box p{margin:0 0 6px}.box mark{background:var(--sun);padding:0 4px;border-radius:4px}
table{width:100%;border-collapse:collapse;font-size:14px;font-weight:700}
th,td{border:1.5px solid var(--ink);padding:7px 8px;text-align:left}th{background:var(--sun)}
.tri{display:inline-block;border:5px solid transparent;border-top:7px solid var(--ink);margin-left:6px;vertical-align:-2px}
"""

errors = []


def check(label, text, limit):
    for ln in str(text).split("\n"):
        if len(ln) > limit:
            errors.append(f"{label}: '{ln}' 가 {len(ln)}자 (한도 {limit}자)")


def esc(t):
    return html.escape(str(t)).replace("\n", "<br>")


def card(bg, n, scene, inner):
    sc = f'<div class="scene">{esc(scene)}</div>' if scene else ""
    return (f'<section class="card {bg}"><div class="brand"><span>WORKMASTER90</span>'
            f'<span>STORY {n}/{N}</span></div>{sc}{inner}</section>\n')


def hl_lines(lines, hl, cls):
    return "<br>".join(f'<em class="{cls}">{esc(ln)}</em>' if i == hl else esc(ln) for i, ln in enumerate(lines))


def chat(cast, msgs, label):
    if not 2 <= len(msgs) <= 3:
        errors.append(f"{label}: 말풍선은 2~3개여야 함 (현재 {len(msgs)})")
    rows = []
    for who, text in msgs:
        if who not in cast:
            errors.append(f"{label}: cast 에 없는 화자 '{who}'")
            continue
        check(f"{label} 말풍선", text, 18)
        c = cast[who]
        me = who == "me"
        al = ' style="text-align:right"' if me else ""
        rows.append(f'<div class="msg{" me" if me else ""}"><div class="av {c["cls"]}">{esc(c["av"])}</div><div>'
                    f'<div class="who"{al}>{esc(c["name"])}</div><div class="bub">{esc(text)}</div></div></div>')
    return '<div class="chat">' + "".join(rows) + "</div>"


def build(s):
    cast = {k: dict(v) for k, v in s["cast"].items()}
    cast["me"]["cls"] = "me"
    for k, v in cast.items():
        v.setdefault("cls", "sen")
        if k != "me" and v["cls"] not in CLS_OK:
            errors.append(f"cast.{k}.cls '{v['cls']}' 는 {sorted(CLS_OK)} 중 하나여야 함")
        check(f"cast.{k}.av", v["av"], 4)
    c = []
    h = s["hook"]
    if len(h["lines"]) != 4:
        errors.append("hook.lines 는 정확히 4줄")
    check("hook", "\n".join(h["lines"]), 9)
    check("hook.foot", h["foot"], 26)
    c.append(card("bg-coral", 1, "", f'<div class="big">{hl_lines(h["lines"], h["hl"], "hlw")}</div><div class="foot">{esc(h["foot"])}</div>'))
    c.append(card("bg-paper", 2, s["s2"]["scene"], chat(cast, s["s2"]["msgs"], "s2")))
    b = s["s3"]
    if len(b["lines"]) != 3:
        errors.append("s3.lines 는 정확히 3줄")
    check("s3", "\n".join(b["lines"]), 9)
    c.append(card("bg-paper", 3, b["scene"], f'<div class="big">{hl_lines(b["lines"], 2, "hl")}</div>'))
    c.append(card("bg-paper", 4, s["s4"]["scene"], chat(cast, s["s4"]["msgs"], "s4")))
    k = s["s5"]
    who = cast.get(k["who"])
    if not who:
        errors.append(f"s5: cast 에 없는 화자 '{k['who']}'")
        who = cast["me"]
    check("s5.title", k["title"], 16)
    check("s5.lines", "\n".join(k["lines"]), 16)
    if len(k["lines"]) > 5:
        errors.append("s5.lines 는 5줄 이하")
    body = f'<b>{esc(k["title"])}</b><br>' + "<br>".join(esc(x) for x in k["lines"])
    c.append(card("bg-paper", 5, k["scene"], f'<div class="chat"><div class="msg"><div class="av {who["cls"]}">{esc(who["av"])}</div><div class="bub mono">{body}</div></div></div>'))
    c.append(card("bg-paper", 6, s["s6"]["scene"], chat(cast, s["s6"]["msgs"], "s6")))
    d = s["s7"]
    check("s7.foot", d.get("foot", ""), 26)
    if d["kind"] == "box":
        if not 2 <= len(d["rows"]) <= 4:
            errors.append("s7.rows 는 2~4개")
        for r in d["rows"]:
            check("s7 항목", r[0], 8)
            check("s7 설명", r[1], 14)
        inner = f'<div class="box"><div class="t">{esc(d["tag"])}</div>' + "".join(
            f'<p><mark>{esc(r[0])}</mark> {esc(r[1])}</p>' for r in d["rows"]) + "</div>"
    else:
        if len(d["head"]) not in (2, 3) or not 2 <= len(d["rows"]) <= 4:
            errors.append("s7 table: head 2~3칸, rows 2~4줄")
        for r in d["rows"] + [d["head"]]:
            if len(r) != len(d["head"]):
                errors.append("s7 table: 모든 줄의 칸 수가 head 와 같아야 함")
            for x in r:
                check("s7 칸", x, 10)
        th = "".join(f'<th>{esc(x)}<span class="tri"></span></th>' for x in d["head"])
        trs = "".join("<tr>" + "".join(f"<td>{esc(x)}</td>" for x in r) + "</tr>" for r in d["rows"])
        inner = f'<div class="box"><div class="t">{esc(d["tag"])}</div><table><tr>{th}</tr>{trs}</table></div>'
    foot = f'<div class="foot">{esc(d["foot"])}</div>' if d.get("foot") else ""
    c.append(card("bg-paper", 7, d["scene"], inner + foot))
    c.append(card("bg-paper", 8, s["s8"]["scene"], chat(cast, s["s8"]["msgs"], "s8")))
    r = s["s9"]
    if len(r["steps"]) != 3:
        errors.append("s9.steps 는 정확히 3개")
    check("s9.title", r["title"], 12)
    check("s9.steps", "\n".join(r["steps"]), 22)
    lis = "".join(f'<li><span class="n">{i}</span>{esc(x)}</li>' for i, x in enumerate(r["steps"], 1))
    c.append(card("bg-paper", 9, r["scene"], f'<h2>{esc(r["title"])}</h2><ul class="list">{lis}</ul><span class="badge">저장 필수</span>'))
    c.append(card("bg-ink", 10, "", '<div class="cta">이런 꿀팁 15개<br>PDF로 보내드려요<br><span class="kw">댓글에 "모음집"</span></div>'
                  '<div class="foot">@workmaster90 팔로우하면 매일 알려드려요</div>'))
    return c


def main():
    story, out, dur = sys.argv[1], sys.argv[2], sys.argv[3]
    s = json.load(open(story, encoding="utf-8"))
    try:
        cards = build(s)
    except KeyError as e:
        sys.exit(f"story.json 에 필수 항목 없음: {e}")
    if errors:
        sys.exit("story.json 수정 필요:\n- " + "\n- ".join(errors))
    assert len(cards) == N
    doc = ('<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>드라마 릴스</title><style>'
           + CSS + '</style></head><body><div class="rail">\n' + "".join(cards) + "</div></body></html>")
    open(out, "w", encoding="utf-8").write(doc)
    json.dump(DURATIONS, open(dur, "w", encoding="utf-8"))
    print(f"drama html -> {out} ({N} cards)")


if __name__ == "__main__":
    main()
