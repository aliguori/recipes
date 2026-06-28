#!/usr/bin/env python3
"""Render a recipe markdown file into a printable 4x6 recipe-card PDF.

Usage:
    recipe_card.py RECIPE.md [-o OUT.pdf] [--html-only]

The markdown format is a small superset of the recipes in this repo:

    ---
    title: Grandma Pizza
    servings: 1 Large Pizza
    prep: 20 Min
    cook: 12-15 Min
    ---

    ## Ingredients

    ### Crust            <- optional subsections; omit for a flat list
    - 2 cups flour
    - 2 tsp yeast

    ## Directions

    1. **Bold lead-in:** first step.
    2. second step.

Inline **bold** is supported in directions. Rendering uses headless Chrome
for faithful CSS; pass --html-only to stop at the .html (e.g. for other
renderers like weasyprint/wkhtmltopdf).
"""
import argparse
import html
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "template.html")

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    shutil.which("google-chrome"),
    shutil.which("chromium"),
    shutil.which("chrome"),
]

# Plate / fork-and-knife icon = servings; stopwatch = a time.
ICON_SERVINGS = '''<svg width="30" height="30" viewBox="0 0 64 64" fill="none" stroke="#2b2b2b" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="34" cy="32" r="15"/>
          <circle cx="34" cy="32" r="9"/>
          <line x1="5" y1="15" x2="5" y2="25"/>
          <line x1="9" y1="15" x2="9" y2="25"/>
          <line x1="13" y1="15" x2="13" y2="25"/>
          <path d="M5 25 H13 M9 25 V49"/>
          <path d="M57 15 V31 M57 15 C53 19 53 28 57 31"/>
          <line x1="57" y1="31" x2="57" y2="49"/>
        </svg>'''
ICON_CLOCK = '''<svg width="30" height="30" viewBox="0 0 64 64" fill="none" stroke="#2b2b2b" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="32" cy="36" r="19"/>
          <line x1="32" y1="36" x2="32" y2="25"/>
          <line x1="32" y1="36" x2="40" y2="36"/>
          <line x1="32" y1="10" x2="32" y2="17"/>
          <line x1="26" y1="10" x2="38" y2="10"/>
          <line x1="50" y1="20" x2="54" y2="16"/>
        </svg>'''


def parse(md):
    """Return (meta dict, ingredient groups, direction steps)."""
    meta = {}
    body = md
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", md, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip().lower()] = v.strip()
        body = md[m.end():]

    # Split into ## sections.
    sections = {}
    cur = None
    for line in body.splitlines():
        h = re.match(r"^##\s+(?!#)(.*)", line)
        if h:
            cur = h.group(1).strip().lower()
            sections[cur] = []
        elif cur is not None:
            sections[cur].append(line)

    ingredients = parse_ingredients(sections.get("ingredients", []))
    directions = parse_directions(sections.get("directions", []))
    return meta, ingredients, directions


def parse_ingredients(lines):
    """-> list of (subhead_or_None, [items])."""
    groups = []
    cur = None  # current (subhead, items)
    for line in lines:
        sub = re.match(r"^###\s+(.*)", line)
        item = re.match(r"^\s*[-*]\s+(.*)", line)
        if sub:
            cur = (sub.group(1).strip(), [])
            groups.append(cur)
        elif item:
            if cur is None:
                cur = (None, [])
                groups.append(cur)
            cur[1].append(item.group(1).strip())
    return groups


def parse_directions(lines):
    """Join wrapped numbered-list items into steps."""
    steps = []
    for line in lines:
        m = re.match(r"^\s*\d+\.\s+(.*)", line)
        if m:
            steps.append(m.group(1).strip())
        elif line.strip() and steps:
            steps[-1] += " " + line.strip()
    return steps


def inline(text):
    """Escape, then render **bold** -> <strong>."""
    text = html.escape(text)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)


def lead(text):
    """A leading **bold:** phrase becomes the card's .lead span."""
    text = html.escape(text)
    m = re.match(r"\*\*(.+?)\*\*\s*(.*)", text, re.S)
    if m:
        return f'<span class="lead">{m.group(1)}</span> {m.group(2)}'.strip()
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)


def stat(icon, label_html):
    return (f'<div class="stat">\n        {icon}\n'
            f'        <div class="label">{label_html}</div>\n      </div>')


def build_stats(meta):
    items = []
    if meta.get("servings"):
        items.append(stat(ICON_SERVINGS, f"<b>{html.escape(meta['servings'])}</b>"))
    if meta.get("prep"):
        items.append(stat(ICON_CLOCK, f"Prep Time:<br><b>{html.escape(meta['prep'])}</b>"))
    if meta.get("cook"):
        items.append(stat(ICON_CLOCK, f"Cook Time:<br><b>{html.escape(meta['cook'])}</b>"))
    if meta.get("total"):
        items.append(stat(ICON_CLOCK, f"Total Time:<br><b>{html.escape(meta['total'])}</b>"))
    return '\n      <div class="divider"></div>\n      '.join(items)


def build_ingredients(groups):
    out = []
    for sub, items in groups:
        if sub:
            out.append(f'<div class="subhead">{inline(sub)}:</div>')
        out.append("<ul>")
        out += [f"          <li>{inline(i)}</li>" for i in items]
        out.append("        </ul>")
    return "\n        ".join(out)


def build_directions(steps):
    lis = [f"<li>{lead(s)}</li>" for s in steps]
    return "\n          ".join(lis)


def render_html(md):
    meta, ingredients, directions = parse(md)
    with open(TEMPLATE) as f:
        tpl = f.read()

    # Replace the template's body between the markers we know are stable.
    title = html.escape(meta.get("title", "Recipe"))
    tpl = re.sub(r'<h1 class="title">.*?</h1>',
                 f'<h1 class="title">{title}</h1>', tpl, flags=re.S)
    tpl = re.sub(r'<div class="stats">.*?</div>\s*\n\s*<div class="rule thin">',
                 f'<div class="stats">\n      {build_stats(meta)}\n    </div>\n\n    <div class="rule thin">',
                 tpl, flags=re.S)
    tpl = re.sub(r'<h2>Ingredients</h2>.*?</div>\s*\n\s*<div class="col-directions">',
                 f'<h2>Ingredients</h2>\n\n        {build_ingredients(ingredients)}\n      </div>\n\n      <div class="col-directions">',
                 tpl, flags=re.S)
    tpl = re.sub(r'<h2>Directions</h2>\s*<ol>.*?</ol>',
                 f'<h2>Directions</h2>\n        <ol>\n          {build_directions(directions)}\n        </ol>',
                 tpl, flags=re.S)

    # Optional attribution footer (free-form `source:` frontmatter).
    if meta.get("source"):
        footer = f'<div class="source">{inline(meta["source"])}</div>'
    else:
        footer = ""
    tpl = tpl.replace("<!--SOURCE-->", footer)
    return tpl


def find_chrome():
    for c in CHROME_CANDIDATES:
        if c and os.path.exists(c):
            return c
    return None


def main():
    ap = argparse.ArgumentParser(description="Render a recipe markdown file to a 4x6 card PDF.")
    ap.add_argument("recipe", help="path to RECIPE.md")
    ap.add_argument("-o", "--out", help="output PDF path (default: alongside the .md)")
    ap.add_argument("--html-only", action="store_true", help="write the .html and stop")
    args = ap.parse_args()

    with open(args.recipe) as f:
        md = f.read()
    base = os.path.splitext(os.path.abspath(args.recipe))[0]
    html_path = base + ".html"
    with open(html_path, "w") as f:
        f.write(render_html(md))
    print(f"wrote {html_path}")
    if args.html_only:
        return

    pdf_path = args.out or (base + ".pdf")
    chrome = find_chrome()
    if not chrome:
        sys.exit("No Chrome/Chromium found; install one or use --html-only with another renderer.")
    subprocess.run([
        chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}", f"file://{html_path}",
    ], check=True, stderr=subprocess.DEVNULL)
    print(f"wrote {pdf_path}")


if __name__ == "__main__":
    main()
