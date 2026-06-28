---
name: recipe-card
description: Create a printable 4x6 recipe card (PDF) from a recipe. Use when asked to turn a recipe — a markdown file in this repo, a URL/MHTML page, or pasted text — into a recipe card or printable PDF.
---

# Recipe Card

Turns a recipe into a printable **4×6 inch landscape** recipe card rendered to PDF.
The card style: cream background, thin border, centered uppercase serif title, a
stats row (servings / prep / cook with line icons), and a two-column body —
**Ingredients** on the left, numbered **Directions** on the right, split by a
vertical rule. See `example.png` for the look.

You write the recipe as a small markdown file; `recipe_card.py` converts it to
styled HTML and renders the PDF. You normally don't touch HTML or CSS.

## Markdown format

Frontmatter holds the title and the stats row; `## Ingredients` and
`## Directions` hold the body. Ingredient subsections (`###`) are optional.

```markdown
---
title: Grandma Pizza
servings: 1 Large Pizza
prep: 20 Min
cook: 12–15 Min
---

## Ingredients

### Crust
- 2 cups (212g) Italian-Style Flour
- 2 tsp instant yeast

### Topping
- 3 cups (340g) shredded mozzarella

## Directions

1. **To make the crust:** Combine all crust ingredients and knead to a smooth dough.
2. Bake at 500°F for 12 to 15 minutes.
```

Format notes:
- Frontmatter keys: `title`, `servings`, `prep`, `cook`, and optionally `total`.
  Each present time/servings key becomes one stat in the row. Omit a key to drop
  its slot (the row stays balanced).
- Optional `source:` — free-form attribution rendered as a small italic footer
  at the bottom of the card (e.g. `source: Adapted from Erin McDowell's Drop
  Biscuits`). Omit it for no footer. It uses ~12pt of height, so re-check fit on
  near-full cards.
- Omit the `###` subsections for a single flat ingredient list.
- A leading `**bold:**` phrase on a direction step renders as the card's bold
  lead-in (e.g. "To make the crust:"). Inline `**bold**` also works mid-step.
- Type real Unicode for fractions/symbols — `¼ ½ ¾ ° × ″ –`. The script
  HTML-escapes everything, so paste characters directly rather than entities.
- This is a superset of the plain recipe `.md` files already in the repo; an
  existing recipe just needs frontmatter and the two `##` headings added.

## Fitting the card

The whole recipe must fit one 4×6 page. Hard-won guidance:

- **Title must be a single line.** A two-line title eats vertical space and looks
  worse. If a title wraps, shorten it — prefer renaming over shrinking type
  (e.g. "Strawberry Rhubarb Rock Cakes" → "Fruit Rock Cakes", "Butternut Squash
  Pasta Sauce" → "Butternut Squash Sauce", "Pineapple Jalapeño Jelly" → "Spicy
  Pineapple Jelly"). Roughly ≤ ~22 uppercase characters stays on one line.
- **Capacity is driven by the taller column.** As a rule of thumb a card holds
  about **15 ingredient lines** or **9–10 directions** with a one-line title.
  Each ingredient `### subhead` costs roughly one item's worth of height, and a
  `source:` footer or two-line title costs a bit more — so a card with subheads
  + footer fits fewer items. When near the limit, drop subheads (use a flat
  list), merge related ingredient lines ("1 cup each diced rhubarb and
  strawberries"), or tighten step wording.
- **Split recipes that won't fit into multiple cards.** A recipe with a long
  prep sub-recipe (stock, roux, clarified juice) plus a main assembly often
  exceeds one card. Make each part its own `.md`/card and reference the
  dependency in the dependent card's ingredient list, e.g.
  `1½ lb duck meat (see Duck Stock & Fat)`. This is cleaner than cramming.
- **Drop prose that isn't steps or ingredients** — headnotes, variations,
  equipment lists, storage essays, award backstories. The source recipe keeps
  them; the card is a working reference.

## Verifying fit

Render to PNG (step 4 below) and **look at the bottom of each column** — Chrome
silently clips overflow, so an over-long list just ends early with no error. The
last ingredient and last direction must both be visible with margin below. When
a card is near-full, crop the bottom corners at higher resolution to confirm
nothing is cut off, e.g.:

```bash
sips -s format png --out /tmp/big.png --resampleWidth 1600 <recipe>.pdf
# then crop the bottom-left (ingredients) / bottom-right (directions) and view
```

## Steps

1. **Get the recipe content** from wherever it lives — a `.md` in this repo, a
   URL, an `.mhtml` save, or pasted text. For MHTML, the print view holds the
   cleanest markup; `grep` for the `<h1>`, `Ingredients`, and `Instructions`.

2. **Write `<recipe_name>.md`** in the repo root using the format above.

3. **Render it:**

   ```bash
   python3 skills/recipe-card/recipe_card.py <recipe_name>.md
   ```

   This writes `<recipe_name>.html` and `<recipe_name>.pdf` next to the markdown.
   Use `-o OUT.pdf` to choose the PDF path, or `--html-only` to stop at the HTML
   (e.g. to render with another tool).

4. **Verify the layout** — everything must fit on the single 4×6 page with no
   overflow:

   ```bash
   sips -s format png --out /tmp/card.png <recipe_name>.pdf
   ```

   View `/tmp/card.png`. If content runs long, tighten wording or trim a
   low-value final step, then re-render.

## How it works / tweaking

- `recipe_card.py` — dependency-free (Python 3 stdlib only). Parses the markdown,
  fills `template.html`, and shells out to headless Chrome
  (`--headless --print-to-pdf`) for faithful CSS and exact page size.
- `template.html` — the card's HTML/CSS, with placeholder content. All styling
  (fonts, colors, the plate/stopwatch SVG icons, column split, 4×6 `@page`) lives
  here. Edit it to change the look for *every* card; the script copies its `<style>`
  verbatim and only swaps the title, stats, ingredients, and directions.
- Fonts are system fonts (Baskerville/Didot/Optima with fallbacks) — no assets.
- Renderer is headless Chrome because it reproduces the icons and layout most
  faithfully; `--html-only` + weasyprint/wkhtmltopdf is a fallback if needed.
