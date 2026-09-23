#!/usr/bin/env python3
"""카드 PNG(1.png..N.png) 를 크로스페이드 영상(4:5, 1080x1350)으로 만든다.

usage: make_reel.py <cards_dir> <bgm.mp3> <out.mp4>

- 9:16 패딩/크롭 금지 — 카드 원본 비율(4:5) 그대로 발행해야 인스타 릴스 플레이어에서 잘리지 않음
- 켄번스(줌/팬)는 커버 카드(1번)에만 적용 — 나머지 카드는 정지 이미지 + 크로스페이드 전환만
  (팁/CTA 카드까지 움직이면 화면이 어지럽다는 피드백, 2026-09-23)
- 최대 줌 1.05, y 앵커는 하단 고정(위쪽에서만 잘림) — 상/하단 텍스트 잘림 방지 검증값
"""
import glob
import os
import subprocess
import sys

import imageio_ffmpeg

CLIP = 2.0
FADE = 0.35
FPS = 30
DUR = 60  # zoompan 진행 프레임 수 (CLIP*FPS)
ZMAX = 0.05


def zoom_expr():
    # 커버 카드 전용: 서서히 줌인, 하단 고정
    return f"1+{ZMAX}*on/{DUR}", "iw/2-(iw/zoom/2)", "ih-(ih/zoom)"


def main():
    cards_dir, bgm, out = sys.argv[1], sys.argv[2], sys.argv[3]
    imgs = sorted(glob.glob(os.path.join(cards_dir, "[0-9]*.png")), key=lambda p: int(os.path.basename(p).split(".")[0]))
    n = len(imgs)
    if n < 2:
        sys.exit("need >=2 cards")
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ff, "-y", "-hide_banner", "-loglevel", "error"]
    for p in imgs:
        cmd += ["-loop", "1", "-framerate", str(FPS), "-i", p]
    cmd += ["-i", bgm]
    parts = []
    for k in range(n):
        if k == 0:  # 커버 카드만 켄번스 줌인
            z, x, y = zoom_expr()
            parts.append(
                f"[{k}:v]scale=1080:1350,setsar=1,zoompan=z='{z}':x='{x}':y='{y}':d=1:s=1080x1350:fps={FPS},"
                f"trim=duration={CLIP},setpts=PTS-STARTPTS,fps={FPS},format=yuv420p[v{k}]"
            )
        else:  # 나머지는 정지 이미지 (전환은 아래 xfade 크로스페이드만)
            parts.append(
                f"[{k}:v]scale=1080:1350,setsar=1,"
                f"trim=duration={CLIP},setpts=PTS-STARTPTS,fps={FPS},format=yuv420p[v{k}]"
            )
    last = "v0"
    for k in range(1, n):
        off = round(k * (CLIP - FADE), 3)
        parts.append(f"[{last}][v{k}]xfade=transition=fade:duration={FADE}:offset={off}[x{k}]")
        last = f"x{k}"
    total = round(n * CLIP - (n - 1) * FADE, 3)
    parts.append(f"[{n}:a]atrim=0:{total},afade=t=out:st={round(total - 1, 3)}:d=1[a]")
    cmd += ["-filter_complex", ";".join(parts), "-map", f"[{last}]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", "-t", str(total), "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)
    print(f"reel -> {out} ({total}s, {os.path.getsize(out)//1024} KB)")


if __name__ == "__main__":
    main()
