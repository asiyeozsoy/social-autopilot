"""Re-encode queued videos to a spec every platform accepts:
H.264 high, yuv420p, fixed 30 fps, closed 2 s GOP, AAC-LC stereo 48 kHz 128 kbps, faststart.

python tools/normalize_videos.py content
"""
import json
import subprocess
import sys
from pathlib import Path


def ok(v: Path) -> bool:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,channels,sample_rate",
                          "-of", "json", str(v)], capture_output=True, text=True).stdout
    a = [s for s in json.loads(out)["streams"] if s["codec_type"] == "audio"]
    return bool(a) and a[0].get("channels") == 2 and a[0].get("sample_rate") == "48000"


for v in sorted(Path(sys.argv[1]).rglob("*.mp4")):
    if ok(v):
        continue
    tmp = v.with_suffix(".tmp.mp4")
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", str(v),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-profile:v", "high", "-pix_fmt", "yuv420p",
                    "-r", "30", "-g", "60", "-keyint_min", "60", "-sc_threshold", "0", "-flags", "+cgop",
                    "-c:a", "aac", "-ac", "2", "-ar", "48000", "-b:a", "128k", "-movflags", "+faststart", str(tmp)], check=True)
    tmp.replace(v)
    print("normalized", v)
