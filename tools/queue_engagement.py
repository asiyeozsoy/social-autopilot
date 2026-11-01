"""Render and queue the weekly engagement carousels for both brands.

python tools/queue_engagement.py tools/design/engagement_batch1.json [HHMM]
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools" / "design"))
import end_cards  # noqa: E402
import factyeap_render as fr  # noqa: E402
import interactive  # noqa: E402

TZ = "+01:00"
SIZES = ("instagram", "tiktok")


def caption(lines):
    return "\n\n".join(lines)


def write_spec(dst, brand, date, hhmm, ig_files, tt_files, ig, tt):
    spec = {
        "brand": brand,
        "publish_at": f"{date}T{hhmm[:2]}:{hhmm[2:]}:00{TZ}",
        "platforms": {
            "instagram": {"kind": "carousel" if len(ig_files) > 1 else "image", "media": ig_files, "caption": caption(ig)},
            "tiktok": {"kind": "photo", "media": tt_files, "caption": caption(tt)},
        },
    }
    (dst / "post.yaml").write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print("queued", dst.relative_to(ROOT))


def tinynotes(item, hhmm):
    dst = ROOT / "content" / "tinynotes" / f"{item['date']}_{hhmm}_{item['slug']}"
    dst.mkdir(parents=True, exist_ok=True)
    slides = [{"cover": item["cover"]}] + [{"note": n, "hook": f"note no. {i}"} for i, n in enumerate(item["notes"], 1)]
    with tempfile.TemporaryDirectory() as tmp:
        spec = Path(tmp) / "s.json"
        spec.write_text(json.dumps([{"id": "c", "type": "carousel", "slides": slides}]))
        wm = Path(tmp) / "wm"
        wm.mkdir()
        for f in (ROOT / "brand").glob("*.png"):
            (wm / f.name).write_bytes(f.read_bytes())
        subprocess.run([sys.executable, "-I", str(ROOT / "tools/design/tinynotes_render.py"), tmp, tmp, str(spec)], check=True,
                       stdout=subprocess.DEVNULL)
        for f in sorted((Path(tmp) / "c").glob("*.png")):
            if not f.name.startswith("youtube"):
                (dst / f.name).write_bytes(f.read_bytes())
    k = len(slides) + 1
    for p in SIZES:
        end_cards.tinynotes_end(p, item["end"][0], item["end"][1], n=len(item["notes"])).save(dst / f"{p}_{k:02d}.png")
    files = {p: sorted(x.name for x in dst.glob(f"{p}_*.png")) for p in SIZES}
    write_spec(dst, "tinynotes", item["date"], hhmm, files["instagram"], files["tiktok"], item["ig"], item["tt"])


def factyeap(item, hhmm):
    dst = ROOT / "content" / "factyeap" / f"{item['date']}_{hhmm}_{item['slug']}"
    dst.mkdir(parents=True, exist_ok=True)
    if item["kind"] == "owl_grid":
        for p in SIZES:
            interactive.owl_grid(p).save(dst / f"{p}.png")
        write_spec(dst, "factyeap", item["date"], hhmm, ["instagram.png"], ["tiktok.png"], item["ig"], item["tt"])
        return
    label, line = item["cover"].split("|")
    slides = [(label, line, None)] + [(f"TYPE #{i}", t, "yeap.") for i, t in enumerate(item["types"], 1)]
    fr.carousel(dst, slides, seed=item["slug"])
    k = len(slides) + 1
    for p in SIZES:
        end_cards.factyeap_end(p, item["end"][0], item["end"][1], n=len(item["types"])).save(dst / f"{p}_{k:02d}.png")
    files = {p: sorted(x.name for x in dst.glob(f"{p}_*.png")) for p in SIZES}
    write_spec(dst, "factyeap", item["date"], hhmm, files["instagram"], files["tiktok"], item["ig"], item["tt"])


def main(spec_file, hhmm="1200"):
    data = json.loads(Path(spec_file).read_text(encoding="utf-8"))
    for item in data.get("tinynotes", []):
        tinynotes(item, hhmm)
    for item in data.get("factyeap", []):
        factyeap(item, hhmm)


if __name__ == "__main__":
    main(sys.argv[1], *(sys.argv[2:3]))
