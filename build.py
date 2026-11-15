#!/usr/bin/env python3
"""Build nicholasnorris.com into ./docs (the folder GitHub Pages publishes).

Content lives in ./content (paintings.json, installation-views.json, cv.html, site.json)
and full-size photos in ./originals. Run:  python3 build.py
"""
import html
import json
import re
import shutil
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
ORIG = ROOT / "originals"
OUT = ROOT / "docs"

LARGE = 1600   # long edge for the painting viewer
THUMB = 640    # square thumbnails for the grid
WIDE = 1600    # width for installation views

site = json.loads((CONTENT / "site.json").read_text())
paintings = json.loads((CONTENT / "paintings.json").read_text())
installs = json.loads((CONTENT / "installation-views.json").read_text())
cv_html = (CONTENT / "cv.html").read_text()
esc = html.escape


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.strip().lower()).strip("-")


def save_jpeg(im, dest, quality=84):
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(dest, "JPEG", quality=quality, optimize=True, progressive=True)


def resized(src, dest, long_edge=None, width=None, square=None):
    """Write a web-sized copy of src, skipping if it is already up to date."""
    if dest.exists() and dest.stat().st_mtime >= src.stat().st_mtime:
        return Image.open(dest).size
    im = ImageOps.exif_transpose(Image.open(src))
    if square:
        im = ImageOps.fit(im, (square, square), Image.LANCZOS)
    elif long_edge:
        im.thumbnail((long_edge, long_edge), Image.LANCZOS)
    elif width and im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    save_jpeg(im, dest, 80 if square else 84)
    return im.size


NAV = [
    ("index.html", "Home", "primary"),
    ("paintings.html", "Paintings", "primary"),
    ("installation-views.html", "Installation Views", "primary"),
    ("cv.html", "CV", "secondary"),
    ("contact.html", "Contact", "secondary"),
]


def page(filename, title, body, extra_sidebar="", scripts="", og_image=None, base=""):
    full_title = site["name"] if filename == "index.html" else f"{title} | {site['name']}"
    def links(group):
        out = []
        for href, label, g in NAV:
            if g != group:
                continue
            cur = ' aria-current="page"' if href == filename else ""
            out.append(f'<li><a href="{href}"{cur}>{esc(label)}</a></li>')
        return "\n        ".join(out)
    og = og_image or f"img/installation-views/{site['home_image']}"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">{base}
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(full_title)}</title>
  <meta name="description" content="{esc(site['description'])}">
  <meta property="og:title" content="{esc(full_title)}">
  <meta property="og:description" content="{esc(site['description'])}">
  <meta property="og:image" content="{site['url']}/{og}">
  <link rel="canonical" href="{site['url']}/{'' if filename == 'index.html' else filename.replace('.html', '')}">
  <link rel="stylesheet" href="assets/style.css">
</head>
<body data-site="{esc(site['name'])}" data-title="{esc(full_title)}">
  <aside class="sidebar">
    <a class="site-title" href="index.html">{esc(site['name'])}</a>
    <nav aria-label="Main">
      <ul class="nav-primary">
        {links('primary')}
      </ul>
      <ul class="nav-secondary">
        {links('secondary')}
      </ul>
    </nav>{extra_sidebar}
  </aside>
  <main>
{body}
  </main>{scripts}
</body>
</html>
"""


CAPTION = """
      <div class="caption{cls}" data-caption hidden>
        <div class="title"></div>
        <div class="year"></div>
        <div class="medium"></div>
        <div class="size"></div>
        <div class="controls">
          <a class="prev" href="#">Prev</a> / <a class="next" href="#">Next</a><br>
          <a class="show-thumbs" href="#thumbnails">Show thumbnails</a>
        </div>
      </div>"""


def build():
    if OUT.exists():
        for p in OUT.iterdir():
            if p.name != "img":  # keep resized images so rebuilds are fast
                shutil.rmtree(p) if p.is_dir() else p.unlink()
    OUT.mkdir(exist_ok=True)
    shutil.copytree(ROOT / "assets", OUT / "assets", dirs_exist_ok=True)

    # Paintings
    works, cells = [], []
    seen = set()
    for p in paintings:
        slug = slugify(p["title"])
        while slug in seen or slug == "thumbnails":
            slug += "-2"
        seen.add(slug)
        src = ORIG / "paintings" / p["image"]
        stem = Path(p["image"]).stem
        large = f"img/paintings/{stem}.jpg"
        thumb = f"img/paintings/thumbs/{stem}.jpg"
        resized(src, OUT / large, long_edge=LARGE)
        resized(src, OUT / thumb, square=THUMB)
        alt = f"{p['title']}, {p['year']}. {p['medium']}, {p['size']}."
        works.append({"slug": slug, "title": p["title"], "year": p["year"],
                      "medium": p["medium"], "size": p["size"], "large": large})
        cells.append(f'      <a href="#{slug}"><img src="{thumb}" alt="{esc(alt)}" loading="lazy" width="{THUMB}" height="{THUMB}"></a>')
    data = json.dumps(works, ensure_ascii=False).replace("</", "<\\/")
    body = f"""    <div class="grid">
{chr(10).join(cells)}
    </div>
    <div class="viewer" hidden>
      <img alt="">
    </div>{CAPTION.format(cls=' mobile-caption')}
    <script type="application/json" id="paintings-data">{data}</script>"""
    (OUT / "paintings.html").write_text(page(
        "paintings.html", "Paintings", body,
        extra_sidebar=CAPTION.format(cls=""),
        scripts='\n  <script src="assets/gallery.js"></script>',
        og_image=works[0]["large"] if works else None))

    # Installation views
    figs = []
    for item in installs:
        src = ORIG / "installation-views" / item["image"]
        rel = f"img/installation-views/{Path(item['image']).stem}.jpg"
        w, h = resized(src, OUT / rel, width=WIDE)
        cap = f"\n        <figcaption>{esc(item['caption'])}</figcaption>" if item.get("caption") else ""
        figs.append(f'      <figure><img src="{rel}" alt="Installation view" loading="lazy" width="{w}" height="{h}">{cap}</figure>')
    (OUT / "installation-views.html").write_text(page(
        "installation-views.html", "Installation Views",
        f'    <div class="column stack">\n{chr(10).join(figs)}\n    </div>'))

    # Home
    home_rel = f"img/installation-views/{Path(site['home_image']).stem}.jpg"
    w, h = Image.open(OUT / home_rel).size
    (OUT / "index.html").write_text(page(
        "index.html", "Home",
        f'    <div class="column stack">\n      <img src="{home_rel}" alt="Nicholas Norris, installation view" width="{w}" height="{h}">\n    </div>'))

    # CV and contact
    (OUT / "cv.html").write_text(page("cv.html", "CV", f'    <div class="cv">\n{cv_html}\n    </div>'))
    (OUT / "contact.html").write_text(page(
        "contact.html", "Contact",
        f'    <div class="contact"><p>{esc(site["email_display"])}</p></div>'))

    # Old Squarespace addresses forward to the new pages
    for old, new in [("page-cv.html", "cv.html"), ("new-page-1.html", "contact.html")]:
        (OUT / old).write_text(
            f'<!DOCTYPE html><meta charset="utf-8"><title>Moved</title>'
            f'<meta http-equiv="refresh" content="0; url={new}"><link rel="canonical" href="{new}">'
            f'<a href="{new}">Continue</a>\n')
    (OUT / "404.html").write_text(page("404.html", "Not found",
        '    <div class="contact"><p>Page not found. <a href="index.html">Go to the homepage</a>.</p></div>',
        base='\n  <base href="/">'))
    (OUT / ".nojekyll").write_text("")
    if site.get("domain"):
        (OUT / "CNAME").write_text(site["domain"] + "\n")

    print(f"Built {len(works)} paintings, {len(figs)} installation views into {OUT}")


if __name__ == "__main__":
    build()
