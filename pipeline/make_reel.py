#!/usr/bin/env python3
"""카드 PNG(1.png..N.png) 를 크로스페이드 영상(4:5, 1080x1350)으로 만든다.

usage: make_reel.py <cards_dir> <bgm.mp3> <out.mp4>

- 9:16 패딩/크롭 금지 — 카드 원본 비율(4:5) 그대로 발행해야 인스타 릴스 플레이어에서 잘리지 않음
- 켄번스(줌/팬)는 커버 카드(1번)에만 적용 — 나머지 카드는 정지 이미지 + 크로스페이드 전환만
  (팁/CTA 카드까지 움직이면 화면이 어지럽다는 피드백, 2026-09-23)
- 커버 줌은 첫 PUNCH_FRAMES 동안 빠르게 확대(펀치인)한 뒤 정지 — 스크롤을 멈추는
  "훅" 역할. 예전의 2초짜리 느린 등속 줌은 체감이 안 돼서 폐기 (후킹 강화, 2026-09-28)
- 최대 줌 1.06, 중앙 고정(위·아래 균등하게 ~38px) — 상/하단 텍스트 잘림 방지
"""
import glob
import os
import subprocess
import sys

import imageio_ffmpeg

CLIP = float(os.environ.get("WM_CLIP", "2.0"))  # 드라마 릴스는 1.5 (빠른 컷)
FADE = 0.35
FPS = 30
PUNCH_FRAMES = 12  # 0.4초 @ 30fps 안에 줌 완료
ZMAX = 0.06  # 중앙 고정 기준 위·아래 각 ~38px 만 잘림 (라벨·배지 안전)


def zoom_expr():
    # 커버 카드 전용: 0.4초 안에 빠르게 펀치인 후 정지, 중앙 고정
    # (하단 고정 + 줌 1.10 은 위쪽 123px 가 잘려 상단 라벨/제목이 짤렸음 — 2026-10-04 수정)
    z = f"if(lte(on,{PUNCH_FRAMES}),1+{ZMAX}*on/{PUNCH_FRAMES},1+{ZMAX})"
    return z, "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"


def main():
    cards_dir, bgm, out = sys.argv[1], sys.argv[2], sys.argv[3]
    imgs = sorted(glob.glob(os.path.join(cards_dir, "[0-9]*.png")), key=lambda p: int(os.path.basename(p).split(".")[0]))
    n = len(imgs)
    if n < 2:
        sys.exit("need >=2 cards")
    # 컷별 노출 시간(초): <cards_dir>/durations.json (예: [2.5,3.5,...]) 이 있으면 사용 — 글자 양에 맞춰 읽을 시간 확보
    dur = [CLIP] * n
    dj = os.path.join(cards_dir, "durations.json")
    if os.path.exists(dj):
        import json
        dur = [float(x) for x in json.load(open(dj, encoding="utf-8"))]
        if len(dur) != n:
            sys.exit(f"durations.json has {len(dur)} items, need {n}")
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ff, "-y", "-hide_banner", "-loglevel", "error"]
    for p in imgs:
        cmd += ["-loop", "1", "-framerate", str(FPS), "-i", p]
    cmd += ["-stream_loop", "-1", "-i", bgm]  # BGM(12초)이 영상보다 짧으면 반복 — 끝에서 페이드아웃
    parts = []
    for k in range(n):
        if k == 0:  # 커버 카드만 켄번스 줌인
            z, x, y = zoom_expr()
            parts.append(
                f"[{k}:v]scale=1080:1350,setsar=1,zoompan=z='{z}':x='{x}':y='{y}':d=1:s=1080x1350:fps={FPS},"
                f"trim=duration={dur[k]},setpts=PTS-STARTPTS,fps={FPS},format=yuv420p[v{k}]"
            )
        else:  # 나머지는 정지 이미지 (전환은 아래 xfade 크로스페이드만)
            parts.append(
                f"[{k}:v]scale=1080:1350,setsar=1,"
                f"trim=duration={dur[k]},setpts=PTS-STARTPTS,fps={FPS},format=yuv420p[v{k}]"
            )
    last = "v0"
    for k in range(1, n):
        off = round(sum(dur[:k]) - k * FADE, 3)
        parts.append(f"[{last}][v{k}]xfade=transition=fade:duration={FADE}:offset={off}[x{k}]")
        last = f"x{k}"
    total = round(sum(dur) - (n - 1) * FADE, 3)
    parts.append(f"[{n}:a]atrim=0:{total},afade=t=out:st={round(total - 1, 3)}:d=1[a]")
    cmd += ["-filter_complex", ";".join(parts), "-map", f"[{last}]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", "-t", str(total), "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)
    print(f"reel -> {out} ({total}s, {os.path.getsize(out)//1024} KB)")


if __name__ == "__main__":
    main()
