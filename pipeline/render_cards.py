#!/usr/bin/env python3
"""카드뉴스 HTML(레퍼런스 디자인)의 각 .card 를 1080x1350 PNG 로 렌더링한다.

usage: render_cards.py <html_path> <out_dir>

- 클라우드 루틴 환경의 사전 설치 Chromium(/opt/pw-browsers) + playwright 사용
- 한글 폰트는 jsDelivr(@fontsource) 로 주입 (환경에 CJK 폰트가 없음)
- 후처리: 내용 전체를 25px 위로 올려 하단 여백을 확보 (둥근 모서리 곡선 영역은 그대로 보존)
"""
import glob
import os
import sys

from PIL import Image
from playwright.sync_api import sync_playwright

W, H = 1080, 1350
SHIFT = 25            # 하단 여백 확보용(px @1080)
CUT_Y = 60            # 위쪽에서 잘라낼 띠의 시작 (모서리 곡선 반경 47px 아래, 내용 시작 y≈90 위)
INS_Y = H - 60        # 아래쪽에서 같은 높이의 띠를 끼워 넣는 위치

FB = "https://cdn.jsdelivr.net/npm/@fontsource"
KO_RANGE = "U+1100-11FF,U+3000-303F,U+3130-318F,U+A960-A97F,U+AC00-D7FF,U+FF00-FFEF"
FONT_CSS = "".join(
    f"@font-face{{font-family:'Noto Sans KR';font-weight:{w};font-style:normal;font-display:block;"
    f"src:url({FB}/noto-sans-kr/files/noto-sans-kr-korean-{w}-normal.woff2) format('woff2');"
    f"unicode-range:{KO_RANGE};}}"
    f"@font-face{{font-family:'Noto Sans KR';font-weight:{w};font-style:normal;font-display:block;"
    f"src:url({FB}/noto-sans-kr/files/noto-sans-kr-latin-{w}-normal.woff2) format('woff2');"
    f"unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,"
    f"U+2074,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD;}}"
    for w in (400, 500, 700, 900)
) + "".join(
    f"@font-face{{font-family:'IBM Plex Mono';font-weight:{w};font-style:normal;font-display:block;"
    f"src:url({FB}/ibm-plex-mono/files/ibm-plex-mono-latin-{w}-normal.woff2) format('woff2');}}"
    for w in (600, 700)
)


def find_chrome():
    hits = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"))
    return hits[-1] if hits else None


def add_bottom_margin(img: Image.Image) -> Image.Image:
    """위 CUT_Y 부터 SHIFT px 띠를 제거하고, 아래 INS_Y 위치에 같은 높이의 배경색 띠를 삽입."""
    img = img.convert("RGBA")
    if img.size != (W, H):
        img = img.resize((W, H), Image.LANCZOS)
    bg = img.getpixel((8, INS_Y - 1))  # 카드 왼쪽 안쪽 가장자리의 배경색
    top = img.crop((0, 0, W, CUT_Y))
    mid = img.crop((0, CUT_Y + SHIFT, W, INS_Y))
    bot = img.crop((0, INS_Y, W, H))
    strip = Image.new("RGBA", (W, SHIFT), bg)
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    y = 0
    for part in (top, mid, strip, bot):
        out.paste(part, (0, y))
        y += part.size[1]
    assert y == H, y
    return out


def main():
    html_path, out_dir = os.path.abspath(sys.argv[1]), sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)
    chrome = find_chrome()
    failed = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chrome, args=["--no-sandbox"]) if chrome else p.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1200, "height": 1600}, device_scale_factor=W / 320)
        page.on("requestfailed", lambda r: failed.append(r.url))
        page.goto("file://" + html_path, wait_until="load")
        page.add_style_tag(content=FONT_CSS)
        page.evaluate("document.fonts.ready")
        page.evaluate("Promise.all(['400','500','700','900'].map(w=>document.fonts.load(w+' 20px \"Noto Sans KR\"','가A')))")
        page.wait_for_timeout(800)
        cards = page.query_selector_all(".rail .card")
        if not cards:
            sys.exit("no .rail .card found")
        for i, c in enumerate(cards, 1):
            c.scroll_into_view_if_needed()
            png = c.screenshot(omit_background=True)
            tmp = os.path.join(out_dir, f"_raw{i}.png")
            with open(tmp, "wb") as f:
                f.write(png)
            add_bottom_margin(Image.open(tmp)).save(os.path.join(out_dir, f"{i}.png"))
            os.remove(tmp)
        fonts = page.evaluate("[...document.fonts].filter(f=>f.status!=='unloaded').map(f=>f.family+' '+f.weight+' '+f.status)")
        browser.close()
    print(f"rendered {len(cards)} cards -> {out_dir}")
    print("fonts:", sorted(set(fonts)))
    if failed:
        print("failed requests:", sorted(set(failed))[:10])


if __name__ == "__main__":
    main()
