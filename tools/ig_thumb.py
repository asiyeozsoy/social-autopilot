"""Download an Instagram reel's thumbnail so the cover can be checked.

python tools/ig_thumb.py <brand> <media_id> [out.jpg]
"""
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from autopilot.platforms.base import creds  # noqa: E402
from autopilot.platforms.instagram import api_base  # noqa: E402

brand, mid = sys.argv[1], sys.argv[2]
out = Path(sys.argv[3] if len(sys.argv) > 3 else "thumb.jpg")
tok = creds(brand, "IG_TOKEN")
info = requests.get(f"{api_base(tok)}/{mid}", params={"fields": "thumbnail_url,permalink,media_product_type", "access_token": tok},
                    timeout=30).json()
print({k: v for k, v in info.items() if k != "thumbnail_url"})
out.write_bytes(requests.get(info["thumbnail_url"], timeout=60).content)
print("saved", out, out.stat().st_size)
