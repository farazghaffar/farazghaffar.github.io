# prohall.us — Prohall landing pages

A/B landing pages for shop.prohall.ai, served by GitHub Pages on the custom domain **prohall.us** (see `CNAME`).

**Test: layout.** A = classic layout, B = editorial layout, both in the white theme that matches Shopify checkout. Headline, copy, photos, price and buttons are identical on A and B.

| Product | A | B | Split experiment id |
|---|---|---|---|
| Prohall Select One | https://prohall.us/select-one/a/ | https://prohall.us/select-one/b/ | `select-one-2148bc42` |
| Prohall Miracle Therapy Kit | https://prohall.us/miracle-therapy/a/ | https://prohall.us/miracle-therapy/b/ | `miracle-therapy-4df9437a` |
| Prohall Equalize Mask | https://prohall.us/equalize/a/ | https://prohall.us/equalize/b/ | `equalize-mask-15fbd2ec` |
| Prohall Burix One | https://prohall.us/burix-one/a/ | https://prohall.us/burix-one/b/ | `burix-one-67145c69` |
| Prohall Absolut One Spray Mask | https://prohall.us/absolut-one/a/ | https://prohall.us/absolut-one/b/ | `absolut-one-a568fdbb` |

These five pairs were published by hand (no `landing.lock.json`; the builder never writes into them). Builder pairs: `/select-one-2/` (experiment `select-one-ed4a1070`, deleted in Split) and `/select-one-3/` (built for `select-one-2148bc42`, but that experiment's run uses `/select-one/`).

Each product folder holds `a/`, `b/` and `assets/` (styles.css for both, styles-b.css for B).
Every page loads the Meta Pixel (1762938528379464) and the product's Split tag exactly once, before `</body>`.

### Split labels (all pairs)
Sections carry `data-split-section`, clickable links carry `data-split-cta` (on the `<a>` itself). Labels match `^[a-z][a-z0-9-]{0,47}$` and are the same on A and B:

| Placement | Label |
|---|---|
| Sections | `hero`, `benefits`, `details`, `ingredients`, `how-to-use`, `gallery` (Miracle Therapy, Equalize), `pricing`, `faq`, `final-cta` |
| Header | `nav-benefits`, `nav-how-to-use`, `nav-faq`, `header-buy` |
| Hero | `hero-buy`, `hero-how-to` |
| Mid page (details on A, benefits on B) | `mid-page-buy` |
| Pricing | `pricing-buy`, or `pricing-buy-<size>` per size card (Burix One: `pricing-buy-4-oz`, `pricing-buy-10-oz`) |
| Final call to action | `final-buy`, `browse-all` |
| Phone sticky bar | `sticky-buy` |

Policy and footer links are not labelled. `/` and `404.html` redirect to the store and pass the query string on (so `split_landing` survives).

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

New A/B pairs are built with `tools/landing/build.py`; the five hand-published pairs above are never written by it. Each pair gets its own config, `pages/<slug>.json`, holding its Split experiment id, so a later experiment cannot change an earlier pair.

Files: `tools/landing/build.py` (CLI: `new`, `build`, `check`), `tools/landing/render.py` (templates A and B, `cta()` button component, `split_tag()` — the only place the Split script is rendered — and the default labels), `tools/landing/products/*.json` (product content), `tools/landing/styles/` (CSS), `tools/landing/test_build.py` (tests).

1. **Get the experiment id.** Create the experiment in Split and give Claude its name; Claude reads the exact id with the Split MCP tool `list_experiments` (read-only). Without MCP, copy `data-split-experiment` from the experiment's installation snippet. Never guess or reuse another pair's id.
2. **Create the config** from a product (`select-one`, `miracle-therapy`, `equalize`, `burix-one`, `absolut-one`) with a new slug:
   ```bash
   python3 tools/landing/build.py new select-one-4 --product select-one --experiment <experiment-id>
   ```
   `experiment_id` is an explicit setting with no default: leave out `--experiment` and the pages render without a Split tag but still work as shopping pages. Ids that are all digits (Shopify ids) or 20 hex characters (Split run ids) are refused. Edit `pages/select-one-4.json` for copy, `handle`, `variants[].id` (numeric variant ids for `/cart/<id>:1`) and `shopify_product_id`.
3. **Labels (optional).** The standard sections and buttons get the labels in the table above. To rename one for this pair only, add to `pages/<slug>.json`:
   ```json
   "split_labels": {
     "sections": { "pricing": "offer" },
     "ctas": { "hero-buy": "hero-add-to-cart", "pricing-buy": "offer-buy" }
   }
   ```
   Keys are the placement names (`DEFAULT_SECTION_LABELS` / `DEFAULT_CTA_LABELS` in `render.py`); values must match `^[a-z][a-z0-9-]{0,47}$` and be unique. A new button in a template is added with `cta(href, C["<placement>"], text)` after adding the placement to `DEFAULT_CTA_LABELS`; a new section gets `data-split-section="{S["<placement>"]}"`.
4. **Build, check, test, publish:**
   ```bash
   python3 tools/landing/build.py build select-one-4
   python3 tools/landing/build.py check
   python3 -m unittest discover -s tools/landing
   git add pages/select-one-4.json select-one-4 && git commit -m "Add select-one-4 landing pages" && git push
   ```
   `check` (no slug = every pair in the repo, hand-published ones included) prints each page's experiment id and section/button counts and fails on: more than one Split tag, different ids on A and B, a built pair whose id differs from its lock, invalid/duplicate labels, a button label not on an `<a>`/`<button>`, A/B label mismatches, missing placements, unsupported Shopify links. GitHub Pages publishes `https://prohall.us/<slug>/a/` and `/b/` from `main` about a minute after the push.
5. **In Split (manual; the MCP connector is read-only):** New run → paste both URLs (keep the trailing `/`) → enter the promoted Shopify product ID printed by `build` → start the run.
6. **Verify live.** On each production URL, in the browser console:
   ```js
   console.log({ sections: document.querySelectorAll('[data-split-section]').length,
                 buttons: document.querySelectorAll('[data-split-cta]').length });
   ```
   The numbers must equal the counts printed by `build.py check`. Then open the run's QA links (Claude gets them from `list_runs`), check `SplitExternal.status === "ready"`, scroll the page (`split_section_view`, `split_cta_view`), click a button (`split_cta_click`) and continue to Shopify. In Split → Results choose **QA links only**; Claude reads the same data with `get_results` (`source: direct`) and `get_tracking_health`.
