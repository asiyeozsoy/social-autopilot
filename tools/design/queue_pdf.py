"""Phone-friendly dark PDF of the queue: a calendar overview, then one page per item.

python tools/design/queue_pdf.py out.pdf 2026-11-02 2026-11-25 [brand/glob ...]
"""
import datetime as dt
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

import yaml
from PIL import Image as PILImage
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[2]
G = "/usr/share/fonts/truetype/google-fonts/"
for n, f in (("Pop", "Poppins-Regular.ttf"), ("PopM", "Poppins-Medium.ttf"), ("PopB", "Poppins-Bold.ttf")):
    pdfmetrics.registerFont(TTFont(n, G + f))
BG, INK, MUTED, ACC, LINE = HexColor("#121010"), HexColor("#efe7dc"), HexColor("#a3968d"), HexColor("#f0b04a"), HexColor("#2c2623")
PINK = HexColor("#f08f8a")
W, H = 110 * mm, 200 * mm
S = lambda n, **k: ParagraphStyle(n, **k)
h1 = S("h1", fontName="PopB", fontSize=17, leading=21, textColor=INK, spaceAfter=3)
h2 = S("h2", fontName="PopB", fontSize=12, leading=15, textColor=INK, spaceAfter=2)
lab = S("lab", fontName="PopM", fontSize=7.8, leading=10, textColor=ACC, spaceBefore=5, spaceAfter=1)
body = S("b", fontName="Pop", fontSize=9, leading=12.6, textColor=INK)
small = S("s", fontName="Pop", fontSize=7.8, leading=10.5, textColor=MUTED)
cell = S("c", fontName="Pop", fontSize=7.2, leading=8.8, textColor=INK)
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍⭐↔-↪]")
DAYS = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
NAMES = {"tinynotes": "TinyNotes", "factyeap": "Factyeap"}
TMP = Path(tempfile.mkdtemp())


def clean(t):
    return escape(EMOJI.sub("", t)).replace("\n", "<br/>").strip()


def thumb(folder, spec, width=520):
    ig = spec["platforms"].get("instagram") or next(iter(spec["platforms"].values()))
    src = folder / ig["media"][0]
    out = TMP / f"{folder.parent.name}_{folder.name}.jpg"
    if src.suffix == ".mp4":
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-sseof", "-0.6", "-i", str(src),
                        "-frames:v", "1", str(TMP / "f.png")], check=True)
        src = TMP / "f.png"
    im = PILImage.open(src).convert("RGB")
    im = im.resize((width, int(im.height * width / im.width)), PILImage.LANCZOS)
    im.save(out, quality=82)
    return out, im.width / im.height, len(ig["media"])


def main(out, start, end, globs):
    start, end = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    items = []
    for pf in sorted(ROOT.glob("content/*/*/post.yaml")):
        spec = yaml.safe_load(pf.read_text())
        t = dt.datetime.fromisoformat(str(spec["publish_at"]))
        if start <= t.date() <= end:
            items.append((t, pf.parent, spec))
    items.sort(key=lambda x: x[0])
    story = [Paragraph("Kasım takvimi", h1), Paragraph(f"{start.day}–{end.day} Kasım 2026 · Üsküp saati", small), Spacer(1, 3 * mm)]
    rows = [[Paragraph("<b>Gün</b>", cell), Paragraph("<b>TinyNotes</b>", cell), Paragraph("<b>Factyeap</b>", cell)]]
    d = start
    while d <= end:
        cols = {"tinynotes": [], "factyeap": []}
        for t, folder, spec in items:
            if t.date() == d:
                kind = "video" if "youtube" in spec["platforms"] or spec["platforms"].get("instagram", spec["platforms"].get("facebook", {})).get("kind") in ("reel", "video") else "post"
                cols[spec["brand"]].append(f"{t:%H:%M} {kind}")
        if d.weekday() in (1, 3, 5) and d >= dt.date(2026, 11, 3) and d <= dt.date(2026, 11, 17):
            cols["factyeap"].append("<font color='#f08f8a'>ayı videosu*</font>")
        rows.append([Paragraph(f"{DAYS[d.weekday()]} {d.day}", cell),
                     Paragraph("<br/>".join(cols["tinynotes"]) or "–", cell),
                     Paragraph("<br/>".join(cols["factyeap"]) or "–", cell)])
        d += dt.timedelta(days=1)
    tbl = Table(rows, colWidths=[16 * mm, 35 * mm, 35 * mm])
    tbl.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.3, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                             ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5)]))
    story += [tbl, Spacer(1, 2 * mm),
              Paragraph("* Higgsfield ayı videoları: sen ürettikçe kuyruğa girer.", small), PageBreak()]
    shown = [x for x in items if any(x[1].match(g) for g in globs)] if globs else items
    for t, folder, spec in shown:
        kind = "Video" if spec["platforms"].get("instagram", spec["platforms"].get("facebook", {})).get("kind") in ("reel", "video") else "Post"
        path, ratio, count = thumb(folder, spec)
        story += [Paragraph(f"{NAMES[spec['brand']]} · {DAYS[t.weekday()]} {t.day} Kasım · {t:%H:%M}", h2),
                  Paragraph(kind + (" (son kare)" if kind == "Video" else ""), small), Spacer(1, 2 * mm)]
        iw = 40 * mm if ratio < 0.7 else 58 * mm
        story += [Image(str(path), width=iw, height=iw / ratio), Spacer(1, 2 * mm)]
        p = spec["platforms"]
        story += [Paragraph("INSTAGRAM", lab), Paragraph(clean(p["instagram"]["caption"]), body)]
        if "tiktok" in p:
            story += [Paragraph("TIKTOK", lab), Paragraph(clean(p["tiktok"]["caption"]), body)]
        if "youtube" in p:
            story += [Paragraph("YOUTUBE SHORTS", lab), Paragraph(clean(p["youtube"]["title"]), body)]
        story.append(PageBreak())

    def bg(c, doc):
        c.saveState()
        c.setFillColor(BG)
        c.rect(0, 0, W, H, stroke=0, fill=1)
        c.setFont("Pop", 7)
        c.setFillColor(MUTED)
        c.drawRightString(W - 10 * mm, 7 * mm, str(doc.page))
        c.restoreState()

    SimpleDocTemplate(out, pagesize=(W, H), leftMargin=12 * mm, rightMargin=12 * mm, topMargin=11 * mm,
                      bottomMargin=12 * mm, title="Kasım takvimi").build(story, onFirstPage=bg, onLaterPages=bg)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])
