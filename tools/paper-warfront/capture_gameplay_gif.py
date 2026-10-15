"""Capture a short native Windows battle and encode it as the README GIF.

The observer advances the real compiled Godot pack and saves viewport frames;
the GIF is presentation evidence, not a performance or Android-hardware claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PACK = ROOT / "release/3.0.0-rc41-night-lantern-components/windows/PaperWarfront.exe"
DEFAULT_OUTPUT = ROOT / "docs/media/paper-warfront-gameplay.gif"


def find_godot() -> str:
    candidates = [
        ROOT / ".tools/godot/Godot_v4.7.2-stable_win64_console.exe",
        ROOT / ".tools/godot/Godot_v4.7.2-stable_win64.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    configured = shutil.which("godot") or shutil.which("Godot_v4.7.2-stable_win64_console.exe")
    if configured:
        return configured
    raise SystemExit("Godot 4.7.2 not found; configure .tools/godot or PATH")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", type=Path, default=DEFAULT_PACK)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--duration", type=float, default=10.0)
    parser.add_argument("--interval", type=float, default=0.75)
    parser.add_argument("--capture-dir", type=Path, help="Optional fresh capture directory; otherwise use a new ignored QA folder")
    args = parser.parse_args()
    pack = args.pack.resolve()
    if not pack.is_file():
        raise SystemExit(f"compiled Windows pack not found: {pack}")
    if args.duration <= 0 or args.interval <= 0:
        raise SystemExit("duration and interval must be positive")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg not found in PATH")

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.capture_dir:
        capture_dir = args.capture_dir.resolve()
        capture_dir.mkdir(parents=True, exist_ok=False)
    else:
        qa_root=ROOT/'output/qa/godot/readme-captures'
        qa_root.mkdir(parents=True,exist_ok=True)
        capture_dir=Path(tempfile.mkdtemp(prefix='gameplay-',dir=qa_root))
    observer = capture_dir / "observer.gd"
    shutil.copyfile(ROOT / "tools/paper-warfront/probe_realtime_battle.gd", observer)
    godot_cmd = [
        find_godot(),
        "--main-pack",
        str(pack),
        "--resolution",
        "1280x720",
        "--script",
        str(observer),
        "--",
        "--output",
        str(capture_dir),
        "--map",
        "map.01.04",
        "--duration",
        str(args.duration),
        "--fps-cap",
        "30",
        "--capture-interval",
        str(args.interval),
    ]
    subprocess.run(godot_cmd, cwd=ROOT, check=True)
    frames = sorted(capture_dir.glob("*-battle.png"))
    if len(frames) < 3:
        raise SystemExit(f"native capture produced too few frames: {len(frames)}")

    palette = (
        "fps=8,scale=960:-1:flags=lanczos,split[s0][s1];"
        "[s0]palettegen=stats_mode=diff:max_colors=128[p];"
        "[s1][p]paletteuse=dither=sierra2_4a"
    )
    encode_cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-framerate",
        "8",
        "-start_number",
        "1",
        "-i",
        str(capture_dir / "%02d-battle.png"),
        "-vf",
        palette,
        "-loop",
        "0",
        str(output),
    ]
    subprocess.run(encode_cmd, cwd=ROOT, check=True)
    report=json.loads((capture_dir/'report.json').read_text(encoding='utf-8'))
    def digest(path):
        h=hashlib.sha256()
        with path.open('rb') as f:
            for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
        return h.hexdigest()
    metadata={
        'version':report['version'],'source':'native Windows exported pack; normal paid rules, AI autoplayer',
        'pack_sha256':digest(pack),'gif_sha256':digest(output),'frames':len(frames),
        'capture_interval_seconds':args.interval,'playback_fps':8,'requested_duration_seconds':args.duration,
        'simulation_seconds':report['simulation_seconds'],'capacity_fixture':report['capacity_fixture'],
        'map':report['config']['map'],'renderer':report['renderer'],'adapter':report['video_adapter'],
        'observer_sha256':digest(observer),'passed':report['passed'],
        'scope':'Selected PNG viewport captures encoded at 8 FPS; elapsed gameplay is condensed. Not human-input, performance, or Android hardware evidence.'
    }
    output.with_suffix('.capture.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"created {output} from {len(frames)} native battle frames")


if __name__ == "__main__":
    main()
