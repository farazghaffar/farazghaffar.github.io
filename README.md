# prohall.us — Prohall landing pages

A/B landing pages for shop.prohall.ai, served by GitHub Pages on the custom domain **prohall.us** (see `CNAME`).

**Test: layout.** A = classic layout, B = editorial layout. Headline, copy, photos, price and buttons are identical on A and B.

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
