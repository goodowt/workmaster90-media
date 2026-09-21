#!/usr/bin/env python3
"""GitHub(jsDelivr) 에 올라간 카드 PNG/릴스 mp4 를 인스타그램(@workmaster90)에 발행한다.

usage: publish.py --sha <commit> --date YYYY-MM-DD --caption <caption.txt> [--dry-run] [--only carousel|reel]

env: IG_TOKEN (장기 토큰), IG_USER_ID (선택, 기본 28435954872737257), IG_TOKEN_EXPIRES (YYYY-MM-DD, 선택)
- 캡션은 UTF-8 파일에서 읽어 urllib 로 인코딩 (curl 사용 금지: 한글/이모지 깨짐)
- --dry-run: 토큰 확인 + 미디어 URL 접근/Content-Type 확인만. 컨테이너 생성/발행 안 함.
"""
import argparse
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://graph.instagram.com/v21.0"
CDN = "https://cdn.jsdelivr.net/gh/goodowt/workmaster90-media"
NUM_CARDS = 7


def call(method, path, **params):
    token = os.environ["IG_TOKEN"]
    params["access_token"] = token
    data = urllib.parse.urlencode(params).encode("utf-8")
    url = f"{API}/{path}"
    req = urllib.request.Request(url + ("?" + data.decode() if method == "GET" else ""),
                                 data=data if method == "POST" else None, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        sys.exit(f"API {method} {path} failed: {e.code} {body}")


def head(url):
    req = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.headers.get("Content-Type")


def wait_ready(cid, tries=40):
    for _ in range(tries):
        st = call("GET", cid, fields="status_code")["status_code"]
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            sys.exit(f"container {cid} status {st}")
        time.sleep(5)
    sys.exit(f"container {cid} not ready in time")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sha", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--caption", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", choices=["carousel", "reel"])
    a = ap.parse_args()

    uid = os.environ.get("IG_USER_ID", "28435954872737257")
    exp = os.environ.get("IG_TOKEN_EXPIRES")
    if exp:
        left = (datetime.date.fromisoformat(exp) - datetime.date.today()).days
        print(f"TOKEN_DAYS_LEFT={left}")
        if left < 14:
            print("WARNING: IG token expires soon — ask the user to refresh it")

    me = call("GET", "me", fields="username")
    print("account:", me.get("username"))
    if me.get("username") != "workmaster90":
        sys.exit("unexpected account, abort")

    caption = open(a.caption, encoding="utf-8").read().strip()
    base = f"{CDN}@{a.sha}/posts/{a.date}"
    imgs = [f"{base}/cards/{i}.png" for i in range(1, NUM_CARDS + 1)]
    reel = f"{base}/reel.mp4"

    for u in imgs + [reel]:
        code, ctype = head(u)
        print("media", code, ctype, u.rsplit("/", 1)[-1])

    if a.dry_run:
        print("DRY RUN OK — nothing published")
        return

    if a.only in (None, "carousel"):
        kids = [call("POST", f"{uid}/media", image_url=u, is_carousel_item="true")["id"] for u in imgs]
        c = call("POST", f"{uid}/media", media_type="CAROUSEL", children=",".join(kids), caption=caption)["id"]
        wait_ready(c)
        pid = call("POST", f"{uid}/media_publish", creation_id=c)["id"]
        print("CAROUSEL", call("GET", pid, fields="permalink").get("permalink"))

    if a.only in (None, "reel"):
        c = call("POST", f"{uid}/media", media_type="REELS", video_url=reel, caption=caption)["id"]
        wait_ready(c, tries=60)
        pid = call("POST", f"{uid}/media_publish", creation_id=c)["id"]
        print("REEL", call("GET", pid, fields="permalink").get("permalink"))


if __name__ == "__main__":
    main()
