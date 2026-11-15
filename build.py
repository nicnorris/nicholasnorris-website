#!/usr/bin/env python3
"""Build nicholasnorris.com into ./docs (the folder GitHub Pages publishes).

Content lives in ./content (paintings.json, installation-views.json, cv.html, site.json,
shows/*.json) and full-size photos in ./originals. Run:  python3 build.py
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
shows_dir = CONTENT / "shows"
shows = sorted(
    (json.loads(p.read_text()) for p in shows_dir.glob("*.json")),
    key=lambda s: s.get("menu_order", 99),
) if shows_dir.exists() else []
esc = html.escape


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.strip().lower()).strip("-")


def save_jpeg(im, dest, quality=84):
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(dest, "JPEG", quality=quality, optimize=True, progressive=True)


def resized(src, dest, long_edge=None, width=None, square=None):
    """Write a web-sized copy of src (never upscaled), skipping if already up to date."""
    if dest.exists() and dest.stat().st_mtime >= src.stat().st_mtime:
        return Image.open(dest).size
    im = ImageOps.exif_transpose(Image.open(src))
    if square:
        im = ImageOps.fit(im, (min(square, im.width, im.height),) * 2, Image.LANCZOS)
    elif long_edge:
        im.thumbnail((long_edge, long_edge), Image.LANCZOS)
    elif width and im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    save_jpeg(im, dest, 80 if square else 84)
    return im.size


def nav_items():
    items = [
        ("index.html", "Home", "primary"),
        ("paintings.html", "Paintings", "primary"),
        ("installation-views.html", "Installation Views", "primary"),
    ]
    items += [(f"{s['slug']}.html", s["title"], "shows") for s in shows if s.get("menu", True)]
    items += [("cv.html", "CV", "secondary"), ("contact.html", "Contact", "secondary")]
    return items


def page(filename, title, body, extra_sidebar="", scripts="", og_image=None, base=""):
    full_title = site["name"] if filename == "index.html" else f"{title} | {site['name']}"

    def links(group):
        out = []
        for href, label, g in nav_items():
            if g != group:
                continue
            cur = ' aria-current="page"' if href == filename else ""
            out.append(f'<li><a href="{href}"{cur}>{esc(label)}</a></li>')
        return "\n        ".join(out)

    show_links = links("shows")
    show_block = f"""
      <ul class="nav-shows">
        {show_links}
      </ul>""" if show_links else ""
    og = og_image or f"img/installation-views/{Path(site['home_image']).stem}.jpg"
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
      </ul>{show_block}
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

GALLERY_SCRIPT = '\n  <script src="assets/gallery.js"></script>'


def gallery(items, orig_dir, img_dir):
    """Thumbnail grid + one-at-a-time viewer for a list of works.

    Returns (grid_html, viewer_html, works) where works feeds the viewer script.
    """
    works, cells, seen = [], [], set()
    for p in items:
        slug = slugify(p["title"])
        while slug in seen or slug == "thumbnails":
            slug += "-2"
        seen.add(slug)
        src = orig_dir / p["image"]
        stem = Path(p["image"]).stem
        large = f"{img_dir}/{stem}.jpg"
        thumb = f"{img_dir}/thumbs/{stem}.jpg"
        resized(src, OUT / large, long_edge=LARGE)
        tw, th = resized(src, OUT / thumb, square=THUMB)
        alt = f"{p['title']}, {p['year']}. {p['medium']}, {p['size']}."
        works.append({"slug": slug, "title": p["title"], "year": p["year"],
                      "medium": p["medium"], "size": p["size"], "large": large})
        cells.append(f'      <a href="#{slug}"><img src="{thumb}" alt="{esc(alt)}" loading="lazy" width="{tw}" height="{th}"></a>')
    data = json.dumps(works, ensure_ascii=False).replace("</", "<\\/")
    grid = f"""    <div class="grid">
{chr(10).join(cells)}
    </div>"""
    viewer = f"""
    <div class="viewer" hidden>
      <img alt="">
    </div>{CAPTION.format(cls=' mobile-caption')}
    <script type="application/json" id="paintings-data">{data}</script>"""
    return grid, viewer, works


def build_show(show):
    slug = show["slug"]
    base_orig = ORIG / "shows" / slug
    img_dir = f"img/shows/{slug}"

    def install_img(name, eager=False):
        rel = f"{img_dir}/installation-views/{Path(name).stem}.jpg"
        w, h = resized(base_orig / "installation-views" / name, OUT / rel, width=WIDE)
        lazy = "" if eager else ' loading="lazy"'
        return f'        <img src="{rel}" alt="{esc(show["title"])}, installation view"{lazy} width="{w}" height="{h}">'

    grid, viewer, works = gallery(show.get("works", []), base_orig / "works", f"{img_dir}/works")

    meta = [esc(show.get("kind", "")), esc(f"{show['venue']}, {show['city']}"), esc(show["dates"])]
    meta_html = "\n".join(f"        <p>{m}</p>" for m in meta if m)

    paras = show.get("text_paragraphs", [])
    credit = f'\n        <p class="credit">Text by {esc(show["text_credit"])}</p>' if show.get("text_credit") and paras else ""

    def text_block(nums, last=False):
        ps = "\n".join(f"        <p>{esc(paras[n - 1], quote=False)}</p>" for n in nums)
        return f'      <div class="show-text">\n{ps}{credit if last else ""}\n      </div>'

    used, figs = set(), []
    if show.get("sequence") and paras:
        # Photos and essay paragraphs woven together, in the order the show file lists them
        parts = []
        steps = show["sequence"]
        for i, step in enumerate(steps):
            if step.get("image"):
                parts.append(f'      <div class="column stack">\n{install_img(step["image"], eager=(i == 0))}\n      </div>')
                used.add(step["image"])
            if step.get("paragraphs"):
                parts.append(text_block(step["paragraphs"], last=(i == len(steps) - 1)))
        # Any installation views not placed in the sequence go after it
        rest = [install_img(n) for n in show.get("installation_views", []) if n not in used]
        if rest:
            parts.append(f'      <div class="column stack">\n{chr(10).join(rest)}\n      </div>')
        figs = [s for s in show["sequence"] if s.get("image")] + rest
        middle = "\n".join(parts)
    else:
        figs = [install_img(n, eager=(i == 0)) for i, n in enumerate(show.get("installation_views", []))]
        middle = f'      <div class="column stack">\n{chr(10).join(figs)}\n      </div>'

    if paras and not show.get("sequence"):
        middle += "\n" + text_block(range(1, len(paras) + 1), last=True)
        text = ""
    elif paras:
        text = ""
    elif show.get("text_link"):
        by = f' by {esc(show["text_credit"])}' if show.get("text_credit") else ""
        text = f'      <div class="show-text"><p><a href="{esc(show["text_link"])}">Read the exhibition text{by}</a></p></div>'
    else:
        text = ""

    links = " · ".join(f'<a href="{esc(l["url"])}">{esc(l["label"])}</a>' for l in show.get("links", []))
    foot = []
    if links:
        foot.append(f"        <p>{links}</p>")
    if show.get("image_credit"):
        foot.append(f"        <p>{esc(show['image_credit'])}</p>")
    foot_html = "\n".join(foot)

    body = f"""    <div class="show" data-hide-in-viewer>
      <header class="show-head">
        <h1>{esc(show['title'])}</h1>
{meta_html}
      </header>
{text}
{middle}
      {'<h2 class="show-works">Works</h2>' if works else ''}
    </div>
{grid}{viewer}
    <footer class="show-foot" data-hide-in-viewer>
{foot_html}
    </footer>"""
    og = f"{img_dir}/installation-views/{Path(show['installation_views'][0]).stem}.jpg" if show.get("installation_views") else None
    (OUT / f"{slug}.html").write_text(page(
        f"{slug}.html", show["title"], body,
        extra_sidebar=CAPTION.format(cls=""),
        scripts=GALLERY_SCRIPT if works else "",
        og_image=og))
    return len(works), len(figs)


def build():
    if OUT.exists():
        for p in OUT.iterdir():
            if p.name != "img":  # keep resized images so rebuilds are fast
                shutil.rmtree(p) if p.is_dir() else p.unlink()
    OUT.mkdir(exist_ok=True)
    shutil.copytree(ROOT / "assets", OUT / "assets", dirs_exist_ok=True)

    # Paintings
    grid, viewer, works = gallery(paintings, ORIG / "paintings", "img/paintings")
    (OUT / "paintings.html").write_text(page(
        "paintings.html", "Paintings", grid + viewer,
        extra_sidebar=CAPTION.format(cls=""),
        scripts=GALLERY_SCRIPT,
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

    # Shows
    show_counts = [build_show(s) for s in shows]

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

    print(f"Built {len(works)} paintings, {len(figs)} installation views, "
          f"{len(shows)} show page(s) {show_counts} into {OUT}")


if __name__ == "__main__":
    build()
