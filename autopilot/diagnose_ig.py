"""Diagnose which Instagram accounts a key can reach (prints no secrets)."""
import os, sys, requests
brand = sys.argv[1]
tok = os.environ[f"{brand.upper()}_IG_TOKEN"]
want = os.environ[f"{brand.upper()}_IG_USER_ID"]
v = os.environ.get("GRAPH_API_VERSION") or "v22.0"
def short(j):
    return str(j.get("error", {}).get("message", j))[:160] if "error" in j else str(j)[:200]
for host in ("graph.facebook.com", "graph.instagram.com"):
    for path, fields in ((want, "username"), ("me", "id,name,username,user_id"), ("me/accounts", "name,instagram_business_account{id,username}")):
        try:
            j = requests.get(f"https://{host}/{v}/{path}", params={"fields": fields, "access_token": tok}, timeout=30).json()
        except Exception as e:
            j = {"error": {"message": str(e)}}
        print(f"::warning::{brand} {host}/{path if path != want else '<account>'}: {short(j)}")
