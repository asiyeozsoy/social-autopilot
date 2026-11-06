"""Show (and optionally update) each brand's Facebook Page info, and the matching Instagram bio.

python tools/fb_page_info.py            # read only
python tools/fb_page_info.py --apply    # write website + about from LINKS below
"""
import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from autopilot.platforms.base import creds  # noqa: E402
from autopilot.platforms.facebook import API, page_token, system_token  # noqa: E402
from autopilot.platforms.instagram import api_base  # noqa: E402

LINKS = json.loads((Path(__file__).with_name("fb_links.json")).read_text())

for brand, info in LINKS.items():
    print(f"===== {brand}")
    try:
        token = creds(brand, "IG_TOKEN")
        ig = requests.get(f"{api_base(token)}/{creds(brand, 'IG_USER_ID')}",
                          params={"fields": "username,biography,website", "access_token": token}, timeout=30).json()
        print("IG:", json.dumps(ig, ensure_ascii=False))
    except Exception as e:  # noqa: BLE001
        print("IG read failed:", e)
    pid = creds(brand, "FB_PAGE_ID")
    tok = page_token(pid)
    fields = "name,about,website,description,link"
    print("FB before:", json.dumps(requests.get(f"{API}/{pid}", params={"fields": fields, "access_token": tok}, timeout=30).json(), ensure_ascii=False))
    perms = requests.get(f"{API}/me/permissions", params={"access_token": system_token()}, timeout=30).json()
    print("token perms:", [p["permission"] for p in perms.get("data", []) if p.get("status") == "granted"])
    if "--apply" in sys.argv:
        for key in ("website", "about"):
            r = requests.post(f"{API}/{pid}", data={key: info[key], "access_token": tok}, timeout=30).json()
            print(f"set {key}:", r)
        print("FB after:", json.dumps(requests.get(f"{API}/{pid}", params={"fields": fields, "access_token": tok}, timeout=30).json(), ensure_ascii=False))
