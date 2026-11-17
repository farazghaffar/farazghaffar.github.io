# prohall.us — Prohall landing pages

A/B landing pages for shop.prohall.ai, served by GitHub Pages on the custom domain **prohall.us** (see `CNAME`).

**Test: layout.** A = classic layout, B = editorial layout, both in the white theme that matches Shopify checkout. Headline, copy, photos, price and buttons are identical on A and B.

| Product | A | B |
|---|---|---|
| Prohall Select One | https://prohall.us/select-one/a/ | https://prohall.us/select-one/b/ |
| Prohall Miracle Therapy Kit | https://prohall.us/miracle-therapy/a/ | https://prohall.us/miracle-therapy/b/ |
| Prohall Equalize Mask | https://prohall.us/equalize/a/ | https://prohall.us/equalize/b/ |
| Prohall Burix One | https://prohall.us/burix-one/a/ | https://prohall.us/burix-one/b/ |
| Prohall Absolut One Spray Mask | https://prohall.us/absolut-one/a/ | https://prohall.us/absolut-one/b/ |

Each product folder holds `a/`, `b/` and `assets/` (styles.css for both, styles-b.css for B).
Every page loads the Meta Pixel (1762938528379464); a product's Split tag is added once Split issues it.

## GitHub Pages
Settings → Pages → Source: **Deploy from a branch**, `main`, `/ (root)`. Custom domain: `prohall.us`. Then tick **Enforce HTTPS**.

## DNS for prohall.us
| Type | Name | Value |
|---|---|---|
| A | @ | 185.199.108.153 |
| A | @ | 185.199.109.153 |
| A | @ | 185.199.110.153 |
| A | @ | 185.199.111.153 |
| CNAME | www | farazghaffar.github.io |

For a redesign, publish new folders (e.g. `/select-one/a2/`) and start a new Split run; keep existing pages unchanged.

## Create a tracked landing page

New A/B pairs are built with `tools/landing/build.py`; the five pairs above were published by hand and the builder never writes into them. Each pair gets its own config, `pages/<slug>.json`, holding the Split experiment id, so a later experiment cannot change an earlier pair.

1. **Create the experiment in Split** (dashboard → new experiment) and give Claude its name. Claude looks up the exact id with the Split MCP tool `list_experiments` (read-only; nothing secret goes into the repo or the pages).
2. **Generate Page A and Page B** from a product in `tools/landing/products/` (`select-one`, `miracle-therapy`, `equalize`, `burix-one`, `absolut-one`), using a new slug:
   ```bash
   python3 tools/landing/build.py new select-one-2 --product select-one --experiment <experiment-id>
   ```
   Edit `pages/select-one-2.json` for copy, `handle` (Shopify product page), `variants[].id` (numeric variant ids for `/cart/<id>:1`) and `shopify_product_id`. Sections (`data-split-section`) and buttons (`data-split-cta`) are labelled by the templates in `tools/landing/render.py`; a new button must be added with `cta(href, "<placement-label>", text)`.
3. **Build, test and publish:**
   ```bash
   python3 tools/landing/build.py build select-one-2
   python3 -m unittest discover -s tools/landing
   git add pages/select-one-2.json select-one-2 && git commit -m "Add select-one-2 landing pages" && git push
   ```
   GitHub Pages publishes `https://prohall.us/select-one-2/a/` and `https://prohall.us/select-one-2/b/`. A blank `experiment_id` renders no Split tag; Shopify links still work.
4. **In Split (manual; the MCP connector is read-only):** New run → paste both URLs (keep the trailing `/`) → enter the promoted Shopify product ID printed by `build` → confirm the snippet → start the run.
5. **QA:** open each run-specific QA link (Claude can fetch them with `list_runs`), scroll through the page, click a few buttons and continue to Shopify. In Split → Results choose **QA links only** and check section views, button clicks and the Shopify handoff. Claude can read the same numbers with `get_results` (`source: direct`).
