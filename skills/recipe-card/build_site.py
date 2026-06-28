#!/usr/bin/env python3
"""Build a single self-contained HTML carousel of every recipe card.

Usage:
    build_site.py [RECIPE.md ...] [-o index.html]

With no recipe arguments, it globs every `anthony/*.md` and `clare/*.md`
relative to the repo root. Each recipe is rendered with the same
`render_html()` used for the PDFs and embedded as a style-isolated
`<iframe srcdoc>`, so each slide looks exactly like its printed card. The
output is one standalone file (no assets, no server needed) with prev/next
buttons, arrow-key navigation, and a recipe picker.
"""
import argparse
import glob
import html
import os

import recipe_card

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Recipes</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  :root { --card-w: 576px; --card-h: 384px; }
  body {
    background: #efe9da;
    color: #2b2b2b;
    font-family: "Optima", "Gill Sans", Avenir, sans-serif;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 18px;
    padding: 24px 16px;
  }
  header { text-align: center; }
  h1 {
    font-family: "Didot", "Bodoni 72", "Baskerville", Georgia, serif;
    font-weight: 400;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    font-size: 22px;
  }
  .meta {
    margin-top: 4px;
    font-size: 12px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #6f685a;
  }

  .stage { display: flex; align-items: center; gap: 22px; }

  .frame-wrap {
    width: calc(var(--card-w) * var(--scale));
    height: calc(var(--card-h) * var(--scale));
    box-shadow: 0 14px 40px rgba(0, 0, 0, 0.22);
    border-radius: 3px;
    overflow: hidden;
    background: #fdfcf7;
  }
  .frame-wrap iframe {
    width: var(--card-w);
    height: var(--card-h);
    border: 0;
    transform: scale(var(--scale));
    transform-origin: top left;
    display: block;
  }

  .nav {
    border: 1px solid #b9b1a0;
    background: #fbf8f0;
    color: #2b2b2b;
    width: 46px;
    height: 46px;
    border-radius: 50%;
    font-size: 20px;
    cursor: pointer;
    flex: none;
    transition: background 0.15s, transform 0.1s;
  }
  .nav:hover { background: #fff; }
  .nav:active { transform: scale(0.94); }

  .controls { display: flex; align-items: center; gap: 14px; }
  .counter { font-size: 12px; letter-spacing: 0.12em; color: #6f685a; min-width: 64px; text-align: center; }
  select {
    font: inherit;
    font-size: 13px;
    padding: 6px 10px;
    border: 1px solid #b9b1a0;
    border-radius: 4px;
    background: #fbf8f0;
    color: #2b2b2b;
    max-width: 70vw;
  }
  .hint { font-size: 11px; letter-spacing: 0.1em; color: #8a8275; text-transform: uppercase; }
</style>
</head>
<body>
  <header>
    <h1>Family Recipes</h1>
    <div class="meta" id="label"></div>
  </header>

  <div class="stage">
    <button class="nav" id="prev" aria-label="Previous recipe">&#8249;</button>
    <div class="frame-wrap">
      <iframe id="card" title="Recipe card"></iframe>
    </div>
    <button class="nav" id="next" aria-label="Next recipe">&#8250;</button>
  </div>

  <div class="controls">
    <span class="counter" id="counter"></span>
    <select id="picker"></select>
  </div>
  <div class="hint">Use &#8592; / &#8594; arrow keys to flip</div>

<script>
const RECIPES = {data};

const card = document.getElementById('card');
const label = document.getElementById('label');
const counter = document.getElementById('counter');
const picker = document.getElementById('picker');
let i = 0;

RECIPES.forEach((r, n) => {
  const opt = document.createElement('option');
  opt.value = n;
  opt.textContent = r.title + ' — ' + r.author;
  picker.appendChild(opt);
});

function show(n) {
  i = (n + RECIPES.length) % RECIPES.length;
  const r = RECIPES[i];
  card.srcdoc = r.html;
  label.textContent = r.author;
  counter.textContent = (i + 1) + ' / ' + RECIPES.length;
  picker.value = i;
}

document.getElementById('prev').onclick = () => show(i - 1);
document.getElementById('next').onclick = () => show(i + 1);
picker.onchange = (e) => show(+e.target.value);
document.addEventListener('keydown', (e) => {
  if (e.key === 'ArrowLeft') show(i - 1);
  else if (e.key === 'ArrowRight') show(i + 1);
});

function fit() {
  const sw = (window.innerWidth - 180) / 576;
  const sh = (window.innerHeight - 230) / 384;
  const scale = Math.max(0.6, Math.min(2.2, sw, sh));
  document.documentElement.style.setProperty('--scale', scale);
}
window.addEventListener('resize', fit);
fit();
show(0);
</script>
</body>
</html>
"""


def js_string(s):
    """Embed a Python string as a JS string literal safely inside <script>."""
    return (
        '"' +
        s.replace("\\", "\\\\")
         .replace('"', '\\"')
         .replace("\n", "\\n")
         .replace("\r", "")
         .replace("</", '<\\/')   # never close the <script> early
        + '"'
    )


def build(paths, out):
    recipes = []
    for p in paths:
        with open(p) as f:
            md = f.read()
        meta, _, _ = recipe_card.parse(md)
        recipes.append({
            "title": meta.get("title", os.path.basename(p)),
            "author": os.path.basename(os.path.dirname(os.path.abspath(p))).title(),
            "html": recipe_card.render_html(md),
        })

    items = ",\n".join(
        "{{title: {t}, author: {a}, html: {h}}}".format(
            t=js_string(r["title"]),
            a=js_string(r["author"]),
            h=js_string(r["html"]),
        )
        for r in recipes
    )
    page = PAGE.replace("{data}", "[\n" + items + "\n]")
    with open(out, "w") as f:
        f.write(page)
    print(f"wrote {out} ({len(recipes)} recipes)")


def main():
    ap = argparse.ArgumentParser(description="Build a single-page recipe carousel.")
    ap.add_argument("recipes", nargs="*", help="recipe .md files (default: anthony/* and clare/*)")
    ap.add_argument("-o", "--out", default=os.path.join(REPO, "index.html"),
                    help="output HTML path (default: repo-root index.html)")
    args = ap.parse_args()

    paths = args.recipes
    if not paths:
        paths = sorted(glob.glob(os.path.join(REPO, "anthony", "*.md"))) + \
                sorted(glob.glob(os.path.join(REPO, "clare", "*.md")))
    build(paths, args.out)


if __name__ == "__main__":
    main()
