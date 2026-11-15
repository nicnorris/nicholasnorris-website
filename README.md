# nicholasnorris.com

Static site for Nicholas Norris. No CMS, no database.

## Layout

- `content/paintings.json`: the paintings, in display order (title, year, medium, size, image file)
- `content/installation-views.json`: installation photos, in display order
- `content/cv.html`: the CV
- `content/site.json`: name, contact text, homepage image, domain
- `originals/`: full-size photos (paintings and installation views)
- `assets/`: stylesheet and the gallery script
- `build.py`: makes web-sized images and writes the finished site into `docs/`
- `docs/`: the finished site. GitHub Pages publishes this folder.

## Adding a painting

1. Put the photo in `originals/paintings/`, e.g. `19-fern.jpg`.
2. Add an entry to `content/paintings.json` where it should appear:
   `{"title": "Fern", "year": "2026", "medium": "Oil on canvas", "size": "48 x 40 in", "image": "19-fern.jpg"}`
3. Run `python3 build.py` (needs Python 3 with Pillow).
4. Commit and push. The live site updates in a minute or two.

Each painting has its own link: `paintings.html#<title-in-lowercase-with-dashes>`.
