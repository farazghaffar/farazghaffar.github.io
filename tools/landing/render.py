"""Render one Prohall A/B landing-page pair from its config (pages/<slug>.json).

Layout A = classic, layout B = editorial; both use the white theme. Every
clickable link is created by cta() with a placement label (data-split-cta) and
every section carries data-split-section, so the hosted Split tag can report
section views and button clicks. Labels default to DEFAULT_SECTION_LABELS /
DEFAULT_CTA_LABELS and can be renamed per pair with "split_labels" in the config. The Split tag itself is
rendered once, from the pair's own experiment_id, or not at all when it is blank.
"""
import html
import json
import re

STORE = "https://shop.prohall.ai"
SPLIT_SCRIPT_SRC = "https://split-ivory-one.vercel.app/external-landing.js"
SPLIT_STOREFRONT = "shop.prohall.ai"
e = html.escape

_LABEL_RE = re.compile(r"^[a-z][a-z0-9-]{0,47}$")   # Split label format

# Standard placements and their default Split labels. A pair can rename any of them
# in pages/<slug>.json -> "split_labels": {"sections": {...}, "ctas": {...}}.
DEFAULT_SECTION_LABELS = {
    "hero": "hero", "benefits": "benefits", "details": "details", "ingredients": "ingredients",
    "how-to-use": "how-to-use", "gallery": "gallery", "pricing": "pricing", "faq": "faq",
    "final-cta": "final-cta",
}
DEFAULT_CTA_LABELS = {
    "nav-benefits": "nav-benefits", "nav-how-to-use": "nav-how-to-use", "nav-faq": "nav-faq",
    "header-buy": "header-buy", "hero-buy": "hero-buy", "hero-how-to": "hero-how-to",
    "mid-page-buy": "mid-page-buy",
    "pricing-buy": "pricing-buy",   # one size: this label; several sizes: pricing-buy-<size>
    "final-buy": "final-buy", "browse-all": "browse-all", "sticky-buy": "sticky-buy",
}
_EXPERIMENT_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate_experiment_id(value):
    """Return the experiment id ('' allowed). Rejects things that are clearly not
    a Split experiment id: Shopify product/variant ids (all digits) and Split run
    ids (20 hex characters)."""
    value = (value or "").strip()
    if not value:
        return ""
    if len(value) > 120 or not _EXPERIMENT_RE.match(value):
        raise ValueError(f"experiment_id {value!r} is not a Split experiment id (lowercase letters, digits, hyphens)")
    if value.isdigit():
        raise ValueError(f"experiment_id {value!r} looks like a Shopify product/variant id, not a Split experiment id")
    if re.fullmatch(r"[0-9a-f]{20}", value):
        raise ValueError(f"experiment_id {value!r} looks like a Split run id; use the experiment id from list_experiments")
    return value


def split_tag(experiment_id):
    """The hosted Split tag, exactly once per page; nothing when the id is blank."""
    experiment_id = validate_experiment_id(experiment_id)
    if not experiment_id:
        return ""
    return (
        "  <!-- Split tracking: experiment id comes from this pair's config (pages/<slug>.json). -->\n"
        "  <script defer\n"
        f'    src="{SPLIT_SCRIPT_SRC}"\n'
        f'    data-split-experiment="{e(experiment_id)}"\n'
        f'    data-split-storefront="{SPLIT_STOREFRONT}"></script>\n'
    )


def split_labels(p):
    """Resolved {"sections": {slot: label}, "ctas": {slot: label}} for a pair config."""
    cfg = p.get("split_labels") or {}
    unknown = set(cfg) - {"sections", "ctas"}
    if unknown:
        raise ValueError(f"split_labels has unknown keys {sorted(unknown)}; use 'sections' and 'ctas'")
    out = {}
    for kind, defaults in (("sections", DEFAULT_SECTION_LABELS), ("ctas", DEFAULT_CTA_LABELS)):
        over = cfg.get(kind) or {}
        bad = set(over) - set(defaults)
        if bad:
            raise ValueError(f"split_labels.{kind} has unknown placements {sorted(bad)}; known: {sorted(defaults)}")
        merged = {**defaults, **over}
        for slot, label in merged.items():
            if not isinstance(label, str) or not _LABEL_RE.match(label):
                raise ValueError(f"split_labels.{kind}.{slot} = {label!r} must match ^[a-z][a-z0-9-]{{0,47}}$")
        if len(set(merged.values())) != len(merged):
            raise ValueError(f"split_labels.{kind}: each placement needs its own label")
        out[kind] = merged
    return out


def expected_labels(p):
    """(sections, ctas) the rendered pair must carry, for build.py check."""
    lab = split_labels(p)
    sections = {v for k, v in lab["sections"].items() if k != "gallery" or p.get("gallery")}
    ctas = {v for k, v in lab["ctas"].items() if k != "pricing-buy"}
    if len(p["variants"]) > 1:
        ctas |= {lab["ctas"]["pricing-buy"] + "-" + label_slug(v["title"]) for v in p["variants"]}
    else:
        ctas.add(lab["ctas"]["pricing-buy"])
    return sections, ctas


def label_slug(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")


def cta(href, label, content, cls="btn btn-primary"):
    """Shared button/link component. The placement passes its own Split label."""
    if not _LABEL_RE.match(label):
        raise ValueError(f"bad data-split-cta label {label!r}")
    return f'<a class="{cls}" href="{e(href, quote=True)}" data-split-cta="{label}">{content}</a>'


ICONS = {
    "frizz": '<path d="M4 7c4-3 12-3 16 0M4 12c4-3 12-3 16 0M4 17c4-3 12-3 16 0"/>',
    "drop": '<path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z"/>',
    "shine": '<path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1"/><circle cx="12" cy="12" r="3"/>',
    "heart": '<path d="M20 12c0 5-8 9-8 9s-8-4-8-9a5 5 0 0 1 8-4 5 5 0 0 1 8 4z"/>',
    "shield": '<path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z"/>',
    "volume": '<path d="M8 4v16M16 4v16M4 9l4-5 4 5M12 15l4 5 4-5"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    "flame": '<path d="M12 3c1 4 5 5 5 10a5 5 0 0 1-10 0c0-2 1-3.5 2-4.5.5 2 1.5 3 3 3-1-3 0-6 0-8.5z"/>',
    "balance": '<path d="M12 4v16M5 20h14M6 8h12M6 8l-3 6a3 3 0 0 0 6 0zM18 8l-3 6a3 3 0 0 0 6 0z"/>',
    "palette": '<path d="M12 3a9 9 0 1 0 0 18c1.5 0 2-1 2-2s-1-1.5-1-2.5 1-1.5 2-1.5h2a4 4 0 0 0 4-4c0-4.5-4-8-9-8z"/><circle cx="7.5" cy="11" r="1"/><circle cx="10" cy="7" r="1"/><circle cx="15" cy="7" r="1"/>',
    "curl": '<path d="M7 20c-2-3 0-6 3-6s4-3 2-5-5-1-5 2M14 20c3 0 5-2 5-5"/>',
    "straight": '<path d="M7 3v18M12 3v18M17 3v18"/>',
    "wave": '<path d="M3 8c3-3 6 3 9 0s6 3 9 0M3 16c3-3 6 3 9 0s6 3 9 0"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "scissors": '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M8.1 8.1 20 20M8.1 15.9 20 4"/>',
}
ARROW = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>'


def icon(name):
    return ('<div class="icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg></div>')


def img(url, width):
    return f"{url}&width={width}" if "?" in url else f"{url}?width={width}"


def money(v):
    return f"${v}"


def page_a(p):
    labels = split_labels(p)
    S, C = labels["sections"], labels["ctas"]   # Split section / button labels
    variant = "A"
    head = p["headline"]
    product_url = f"{STORE}/products/{p['handle']}"
    variants = p["variants"]
    multi = len(variants) > 1
    # Add-to-cart target: one-variant products add straight to cart (Shopify cart permalink ->
    # checkout); multi-size products jump to the size picker, whose cards add to cart directly.
    add_url = "#buy" if multi else f"{STORE}/cart/{variants[0]['id']}:1"
    add_short = "Choose size" if multi else "Add to cart"
    add_label = "Choose your size" if multi else f"Add to cart &mdash; {money(variants[0]['price'])}"
    price_label = (f"From {money(min(v['price'] for v in variants))}" if multi else money(variants[0]["price"]))
    hero_w, hero_h = p["hero"]["w"], p["hero"]["h"]

    chips = "".join(f"<li>{e(c)}</li>" for c in p["chips"])
    benefits = "".join(
        f'\n          <article class="benefit">\n            {icon(b[0])}\n            <h3>{e(b[1])}</h3>\n            <p>{e(b[2])}</p>\n          </article>'
        for b in p["benefits"])
    ticks = "".join(f"\n            <li>{e(t)}</li>" for t in p["who"]["items"])
    spec = "".join(f"\n            <dt>{e(k)}</dt><dd>{e(v)}</dd>" for k, v in p["spec"])
    n_ing = len(p["formula"]["items"])
    ing_cls = {2: " cols-2", 4: " cols-4"}.get(n_ing, "")
    ings = "".join(
        f'\n          <article class="ingredient">\n            <span class="num">{i:02d}</span>\n            <h3>{e(it[0])}</h3>\n            <p>{e(it[1])}</p>'
        + (f'\n            <span class="size">{e(it[2])}</span>' if len(it) > 2 else "")
        + "\n          </article>"
        for i, it in enumerate(p["formula"]["items"], 1))
    formula_foot = f'\n        <p class="lumini">{p["formula"]["foot"]}</p>' if p["formula"].get("foot") else ""
    n_steps = len(p["steps"]["items"])
    steps_cls = " cols-4" if n_steps in (4, 7, 8) else ""
    steps = "".join(f"\n          <li><h3>{e(s[0])}</h3><p>{e(s[1])}</p></li>" for s in p["steps"]["items"])
    faqs = "".join(
        f"\n          <details>\n            <summary>{e(q)}</summary>\n            <p>{e(a)}</p>\n          </details>"
        for q, a in p["faq"])

    gallery = ""
    if p.get("gallery"):
        figs = "".join(
            f'\n          <figure><img src="{img(g, 700)}" width="700" height="700" loading="lazy" alt="{e(p["gallery_alt"])}, photo {i}"></figure>'
            for i, g in enumerate(p["gallery"], 2))
        gallery = f'''
    <!-- ============ GALLERY ============ -->
    <section class="section section-alt" id="gallery" data-split-section="{S["gallery"]}" aria-labelledby="gallery-title">
      <div class="wrap">
        <div class="section-head center">
          <p class="eyebrow">A closer look</p>
          <h2 id="gallery-title">{e(p["gallery_title"])}</h2>
        </div>
        <div class="gallery">{figs}
        </div>
      </div>
    </section>
'''

    if multi:
        size_cards = "".join(
            "\n              " + cta(f"{STORE}/cart/{v['id']}:1", C["pricing-buy"] + "-" + label_slug(v["title"]),
                f'<span class="sz">{e(v["title"])}</span><span class="pr">{money(v["price"])}</span>'
                f'<span class="go">Add {e(v["title"])} to cart &rarr;</span>', "size-card")
            for v in variants)
        buy_block = f'''<p class="price-note" style="margin:6px 0 0">USD &middot; choose your size &middot; taxes and shipping shown at checkout</p>
            <div class="sizes">{size_cards}
            </div>'''
        buy_ctas = ''
    else:
        v = variants[0]
        buy_block = f'''<div class="price-row" style="margin:6px 0 4px">
              <span class="price">{money(v["price"])}</span>
              <span class="price-note">USD &middot; final price, taxes and shipping shown at checkout</span>
            </div>'''
        buy_ctas = cta(f"{STORE}/cart/{v['id']}:1", C["pricing-buy"], f"Add to cart &mdash; {money(v['price'])}")

    other = "B" if variant == "A" else "A"
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <!-- VERSION A — layout test. Same headline, copy, photos and offer as version B; only the layout differs. -->
  <title>{e(p["title"])}</title>
  <meta name="description" content="{e(p["meta"])}">
  <meta name="robots" content="noindex">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400..700;1,9..144,400..700&family=Questrial&display=swap">
  <link rel="preload" as="image" href="{img(p["hero"]["url"], 900)}">
  <link rel="stylesheet" href="../assets/styles.css">
</head>
<body>
  <a class="skip" href="#main">Skip to content</a>

  <div class="announce">{e(p["announce"])}</div>

  <header class="site-header">
    <div class="wrap">
      <span class="logo" aria-label="Prohall">PROHALL</span>
      <nav class="header-links" aria-label="Page">
        {cta("#benefits", C["nav-benefits"], "Benefits", "hide-sm")}
        {cta("#how-to-use", C["nav-how-to-use"], "How to use", "hide-sm")}
        {cta("#faq", C["nav-faq"], "FAQ", "hide-sm")}
        {cta(add_url, C["header-buy"], add_short)}
      </nav>
    </div>
  </header>

  <main id="main">

    <!-- ============ HERO ============ -->
    <section class="hero" data-split-section="{S["hero"]}" aria-labelledby="hero-title">
      <div class="wrap hero-grid">
        <div>
          <p class="eyebrow">{e(p["name"])}</p>
          <h1 id="hero-title">{e(head)}</h1>
          <p class="hero-lede">{e(p["lede"])}</p>

          <div class="price-row">
            <span class="price">{price_label}</span>
            <span class="price-note">USD &middot; {e(p["size_note"])}</span>
          </div>

          <div class="cta-row">
            {cta(add_url, C["hero-buy"], add_label + " " + ARROW)}
            {cta("#how-to-use", C["hero-how-to"], "See how to use it", "btn btn-ghost")}
          </div>

          <ul class="chips" aria-label="Product highlights">{chips}</ul>
        </div>

        <div class="hero-visual">
          <div class="halo" aria-hidden="true"></div>
          <img src="{img(p["hero"]["url"], 900)}"
               width="{hero_w}" height="{hero_h}"
               alt="{e(p["hero"]["alt"])}">
          <div class="float-tag t1" aria-hidden="true"><strong>{e(p["tags"][0][0])}</strong>{e(p["tags"][0][1])}</div>
          <div class="float-tag t2" aria-hidden="true"><strong>{e(p["tags"][1][0])}</strong>{e(p["tags"][1][1])}</div>
        </div>
      </div>
    </section>

    <!-- ============ BENEFITS ============ -->
    <section class="section" id="benefits" data-split-section="{S["benefits"]}" aria-labelledby="benefits-title">
      <div class="wrap">
        <div class="section-head center">
          <p class="eyebrow">Benefits</p>
          <h2 id="benefits-title">{e(p["benefits_title"])}</h2>
          <p>{e(p["benefits_intro"])}</p>
        </div>

        <div class="benefits">{benefits}
        </div>
      </div>
    </section>

    <!-- ============ WHO IT'S FOR + SPEC ============ -->
    <section class="section section-alt" id="details" data-split-section="{S["details"]}" aria-labelledby="details-title">
      <div class="wrap split">
        <div>
          <p class="eyebrow">{e(p["who"]["eyebrow"])}</p>
          <h2 id="details-title">{e(p["who"]["title"])}</h2>
          <ul class="ticks">{ticks}
          </ul>
          {cta(add_url, C["mid-page-buy"], add_short)}
        </div>

        <aside class="spec" aria-label="Product details">
          <h3>Product details</h3>
          <dl>{spec}
          </dl>
        </aside>
      </div>
    </section>

    <!-- ============ FORMULA / KIT ============ -->
    <section class="section section-dark" id="formula" data-split-section="{S["ingredients"]}" aria-labelledby="formula-title">
      <div class="wrap">
        <div class="section-head center">
          <p class="eyebrow">{e(p["formula"]["eyebrow"])}</p>
          <h2 id="formula-title">{e(p["formula"]["title"])}</h2>
          <p>{e(p["formula"]["intro"])}</p>
        </div>
        <div class="ingredients{ing_cls}">{ings}
        </div>{formula_foot}
      </div>
    </section>

    <!-- ============ HOW TO USE ============ -->
    <section class="section" id="how-to-use" data-split-section="{S["how-to-use"]}" aria-labelledby="howto-title">
      <div class="wrap">
        <div class="section-head center">
          <p class="eyebrow">How to use</p>
          <h2 id="howto-title">{e(p["steps"]["title"])}</h2>
          <p>{e(p["steps"]["intro"])}</p>
        </div>
        <ol class="steps{steps_cls}">{steps}
        </ol>
        <div class="note">
          {p["steps"]["note"]}
        </div>
      </div>
    </section>
{gallery}
    <!-- ============ BUYING INFORMATION ============ -->
    <section class="section{"" if p.get("gallery") else " section-alt"}" id="buy" data-split-section="{S["pricing"]}" aria-labelledby="buy-title">
      <div class="wrap">
        <div class="buy-card">
          <div class="pack">
            <img src="{img(p["hero"]["url"], 600)}"
                 width="{hero_w}" height="{hero_h}" loading="lazy"
                 alt="{e(p["hero"]["alt"])}">
          </div>
          <div>
            <p class="eyebrow">Buying information</p>
            <h2 id="buy-title">{e(p["buy_title"])}</h2>
            {buy_block}
            <ul class="info-list">
              <li>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 7h11v9H3zM14 10h4l3 3v3h-7"/><circle cx="7" cy="18" r="2"/><circle cx="17" cy="18" r="2"/></svg>
                <span>Shipping rates and delivery times: see our <a href="{STORE}/policies/shipping-policy">shipping policy</a>.</span>
              </li>
              <li>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5"/></svg>
                <span>Returns and refunds: see our <a href="{STORE}/policies/refund-policy">refund policy</a>.</span>
              </li>
              <li>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg>
                <span>Secure checkout handled by Shopify.</span>
              </li>
            </ul>
            <div class="cta-row">
              {buy_ctas}
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ============ FAQ ============ -->
    <section class="section{" section-alt" if p.get("gallery") else ""}" id="faq" data-split-section="{S["faq"]}" aria-labelledby="faq-title">
      <div class="wrap">
        <div class="section-head center">
          <p class="eyebrow">FAQ</p>
          <h2 id="faq-title">Questions, answered</h2>
        </div>
        <div class="faq">{faqs}
        </div>
      </div>
    </section>

    <!-- ============ FINAL ACTION ============ -->
    <section class="final" data-split-section="{S["final-cta"]}" aria-labelledby="final-title">
      <div class="wrap">
        <p class="eyebrow">Ready when you are</p>
        <h2 id="final-title">{e(p["final"]["title"])}</h2>
        <p>{e(p["final"]["text"])}</p>
        <div class="cta-row">
          {cta(add_url, C["final-buy"], add_short, "btn btn-gold")}
          {cta(STORE + "/collections/all", C["browse-all"], "All products", "btn btn-ghost")}
        </div>
      </div>
    </section>
  </main>

  <footer class="site-footer">
    <div class="wrap">
      <span>&copy; Prohall Professional</span>
      <nav aria-label="Store policies">
        <a href="{STORE}/policies/shipping-policy">Shipping</a>
        <a href="{STORE}/policies/refund-policy">Refunds</a>
        <a href="{STORE}/policies/privacy-policy">Privacy</a>
        <a href="{STORE}/policies/terms-of-service">Terms</a>
        <a href="{STORE}/">Store</a>
      </nav>
    </div>
  </footer>

  <div class="sticky-buy">
    <span class="s-name"><strong>{e(p["short"])}</strong>{price_label} &middot; {e(p["sticky_size"])}</span>
    {cta(add_url, C["sticky-buy"], add_short)}
  </div>

{split_tag(p.get("experiment_id", ""))}</body>
</html>
'''


def page_b(p):
    labels = split_labels(p)
    S, C = labels["sections"], labels["ctas"]   # Split section / button labels
    head = p["headline"]
    product_url = f"{STORE}/products/{p['handle']}"
    variants = p["variants"]
    multi = len(variants) > 1
    # Add-to-cart target: one-variant products add straight to cart (Shopify cart permalink ->
    # checkout); multi-size products jump to the size picker, whose cards add to cart directly.
    add_url = "#buy" if multi else f"{STORE}/cart/{variants[0]['id']}:1"
    add_short = "Choose size" if multi else "Add to cart"
    add_label = "Choose your size" if multi else f"Add to cart &mdash; {money(variants[0]['price'])}"
    price_label = (f"From {money(min(v['price'] for v in variants))}" if multi else money(variants[0]["price"]))
    hero_w, hero_h = p["hero"]["w"], p["hero"]["h"]
    strip = "".join(f"<li>{e(c)}</li>" for c in p["chips"])
    blist = "".join(f"\n            <li><h3>{e(b[1])}</h3><p>{e(b[2])}</p></li>" for b in p["benefits"])
    ticks = "".join(f"\n          <li>{e(t)}</li>" for t in p["who"]["items"])
    tiles = "".join(f'\n          <div class="b-tile"><span>{e(k)}</span><strong>{e(v)}</strong></div>' for k, v in p["spec"])
    menu = "".join(
        f'\n          <article><span class="num">{i:02d}</span><h3>{e(it[0])}</h3><p>{e(it[1])}'
        + (f'<span class="size">{e(it[2])}</span>' if len(it) > 2 else "") + "</p></article>"
        for i, it in enumerate(p["formula"]["items"], 1))
    foot = f'\n        <p class="b-foot">{p["formula"]["foot"]}</p>' if p["formula"].get("foot") else ""
    tl = "".join(f"\n          <li><h3>{e(st[0])}</h3><p>{e(st[1])}</p></li>" for st in p["steps"]["items"])
    faqs = "".join(
        f"\n            <details>\n              <summary>{e(q)}</summary>\n              <p>{e(a)}</p>\n            </details>"
        for q, a in p["faq"])
    gallery = ""
    if p.get("gallery"):
        figs = "".join(
            f'\n          <figure><img src="{img(g, 900 if i == 2 else 600)}" width="700" height="700" loading="lazy" alt="{e(p["gallery_alt"])}, photo {i}"></figure>'
            for i, g in enumerate(p["gallery"], 2))
        gallery = f"""
    <!-- ============ GALLERY ============ -->
    <section class="section" id="gallery" data-split-section="{S["gallery"]}" aria-labelledby="gallery-title">
      <div class="wrap">
        <div class="section-head center">
          <p class="eyebrow">A closer look</p>
          <h2 id="gallery-title">{e(p["gallery_title"])}</h2>
        </div>
        <div class="b-gallery">{figs}
        </div>
      </div>
    </section>
"""
    if multi:
        size_cards = "".join(
            "\n              " + cta(f"{STORE}/cart/{v['id']}:1", C["pricing-buy"] + "-" + label_slug(v["title"]),
                f'<span class="sz">{e(v["title"])}</span><span class="pr">{money(v["price"])}</span>'
                f'<span class="go">Add {e(v["title"])} to cart &rarr;</span>', "size-card")
            for v in variants)
        buy_block = f"""<p class="price-note" style="margin:6px 0 0">USD &middot; choose your size &middot; taxes and shipping shown at checkout</p>
            <div class="sizes">{size_cards}
            </div>"""
        buy_ctas = ''
    else:
        v = variants[0]
        buy_block = f"""<div class="price-row" style="margin:6px 0 4px">
              <span class="price">{money(v["price"])}</span>
              <span class="price-note">USD &middot; final price, taxes and shipping shown at checkout</span>
            </div>"""
        buy_ctas = cta(f"{STORE}/cart/{v['id']}:1", C["pricing-buy"], f"Add to cart &mdash; {money(v['price'])}")

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <!-- VERSION B — layout test. Same headline, copy, photos and offer as version A; only the layout differs. -->
  <title>{e(p["title"])}</title>
  <meta name="description" content="{e(p["meta"])}">
  <meta name="robots" content="noindex">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400..700;1,9..144,400..700&family=Questrial&display=swap">
  <link rel="preload" as="image" href="{img(p["hero"]["url"], 900)}">
  <link rel="stylesheet" href="../assets/styles.css">
  <link rel="stylesheet" href="../assets/styles-b.css">
</head>
<body class="b">
  <a class="skip" href="#main">Skip to content</a>

  <div class="announce b-announce">{e(p["announce"])}</div>

  <header class="site-header">
    <div class="wrap">
      <span class="logo" aria-label="Prohall">PROHALL</span>
      <nav class="header-links" aria-label="Page">
        {cta("#benefits", C["nav-benefits"], "Benefits", "hide-sm")}
        {cta("#how-to-use", C["nav-how-to-use"], "How to use", "hide-sm")}
        {cta("#faq", C["nav-faq"], "FAQ", "hide-sm")}
        {cta(add_url, C["header-buy"], add_short)}
      </nav>
    </div>
  </header>

  <main id="main">

    <!-- ============ HERO ============ -->
    <section class="b-hero" data-split-section="{S["hero"]}" aria-labelledby="hero-title">
      <div class="wrap">
        <p class="eyebrow">{e(p["name"])}</p>
        <h1 id="hero-title">{e(head)}</h1>
        <p class="hero-lede">{e(p["lede"])}</p>
        <div class="price-row">
          <span class="price">{price_label}</span>
          <span class="price-note">USD &middot; {e(p["size_note"])}</span>
        </div>
        <div class="cta-row">
          {cta(add_url, C["hero-buy"], add_label + " " + ARROW)}
          {cta("#how-to-use", C["hero-how-to"], "See how to use it", "btn btn-ghost")}
        </div>
        <div class="b-arch">
          <img src="{img(p["hero"]["url"], 900)}" width="{hero_w}" height="{hero_h}" alt="{e(p["hero"]["alt"])}">
          <div class="float-tag t1" aria-hidden="true"><strong>{e(p["tags"][0][0])}</strong>{e(p["tags"][0][1])}</div>
          <div class="float-tag t2" aria-hidden="true"><strong>{e(p["tags"][1][0])}</strong>{e(p["tags"][1][1])}</div>
        </div>
      </div>
    </section>
    <div class="b-strip"><ul aria-label="Product highlights">{strip}</ul></div>

    <!-- ============ BENEFITS ============ -->
    <section class="section" id="benefits" data-split-section="{S["benefits"]}" aria-labelledby="benefits-title">
      <div class="wrap b-benefits">
        <div class="intro">
          <p class="eyebrow">Benefits</p>
          <h2 id="benefits-title">{e(p["benefits_title"])}</h2>
          <p>{e(p["benefits_intro"])}</p>
          {cta(add_url, C["mid-page-buy"], add_short)}
        </div>
        <ol class="b-list">{blist}
        </ol>
      </div>
    </section>

    <!-- ============ WHO IT'S FOR + SPEC ============ -->
    <section class="section section-alt" id="details" data-split-section="{S["details"]}" aria-labelledby="details-title">
      <div class="wrap b-who">
        <div class="section-head center">
          <p class="eyebrow">{e(p["who"]["eyebrow"])}</p>
          <h2 id="details-title">{e(p["who"]["title"])}</h2>
        </div>
        <ul class="ticks">{ticks}
        </ul>
        <div class="b-tiles" aria-label="Product details">{tiles}
        </div>
      </div>
    </section>

    <!-- ============ FORMULA / KIT ============ -->
    <section class="section" id="formula" data-split-section="{S["ingredients"]}" aria-labelledby="formula-title">
      <div class="wrap">
        <div class="section-head center">
          <p class="eyebrow">{e(p["formula"]["eyebrow"])}</p>
          <h2 id="formula-title">{e(p["formula"]["title"])}</h2>
          <p>{e(p["formula"]["intro"])}</p>
        </div>
        <div class="b-menu">{menu}
        </div>{foot}
      </div>
    </section>

    <!-- ============ HOW TO USE ============ -->
    <section class="section section-alt" id="how-to-use" data-split-section="{S["how-to-use"]}" aria-labelledby="howto-title">
      <div class="wrap">
        <div class="section-head center">
          <p class="eyebrow">How to use</p>
          <h2 id="howto-title">{e(p["steps"]["title"])}</h2>
          <p>{e(p["steps"]["intro"])}</p>
        </div>
        <ol class="b-timeline">{tl}
        </ol>
        <div class="note">
          {p["steps"]["note"]}
        </div>
      </div>
    </section>
{gallery}
    <!-- ============ BUYING INFORMATION ============ -->
    <section class="b-buy" id="buy" data-split-section="{S["pricing"]}" aria-labelledby="buy-title">
      <div class="wrap">
        <div class="b-arch">
          <img src="{img(p["hero"]["url"], 600)}" width="{hero_w}" height="{hero_h}" loading="lazy" alt="{e(p["hero"]["alt"])}">
        </div>
        <div>
          <p class="eyebrow">Buying information</p>
          <h2 id="buy-title">{e(p["buy_title"])}</h2>
          {buy_block}
          <ul class="info-list">
            <li>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 7h11v9H3zM14 10h4l3 3v3h-7"/><circle cx="7" cy="18" r="2"/><circle cx="17" cy="18" r="2"/></svg>
              <span>Shipping rates and delivery times: see our <a href="{STORE}/policies/shipping-policy">shipping policy</a>.</span>
            </li>
            <li>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5"/></svg>
              <span>Returns and refunds: see our <a href="{STORE}/policies/refund-policy">refund policy</a>.</span>
            </li>
            <li>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg>
              <span>Secure checkout handled by Shopify.</span>
            </li>
          </ul>
          <div class="cta-row">
            {buy_ctas}
          </div>
        </div>
      </div>
    </section>

    <!-- ============ FAQ ============ -->
    <section class="section" id="faq" data-split-section="{S["faq"]}" aria-labelledby="faq-title">
      <div class="wrap b-faq">
        <div>
          <p class="eyebrow">FAQ</p>
          <h2 id="faq-title">Questions, answered</h2>
        </div>
        <div class="faq">{faqs}
        </div>
      </div>
    </section>

    <!-- ============ FINAL ACTION ============ -->
    <section class="b-final" data-split-section="{S["final-cta"]}" aria-labelledby="final-title">
      <div class="wrap">
        <p class="eyebrow">Ready when you are</p>
        <h2 id="final-title">{e(p["final"]["title"])}</h2>
        <p>{e(p["final"]["text"])}</p>
        <div class="cta-row">
          {cta(add_url, C["final-buy"], add_short)}
          {cta(STORE + "/collections/all", C["browse-all"], "All products", "btn btn-ghost")}
        </div>
      </div>
    </section>
  </main>

  <footer class="site-footer">
    <div class="wrap">
      <span>&copy; Prohall Professional</span>
      <nav aria-label="Store policies">
        <a href="{STORE}/policies/shipping-policy">Shipping</a>
        <a href="{STORE}/policies/refund-policy">Refunds</a>
        <a href="{STORE}/policies/privacy-policy">Privacy</a>
        <a href="{STORE}/policies/terms-of-service">Terms</a>
        <a href="{STORE}/">Store</a>
      </nav>
    </div>
  </footer>

  <div class="sticky-buy">
    <span class="s-name"><strong>{e(p["short"])}</strong>{price_label} &middot; {e(p["sticky_size"])}</span>
    {cta(add_url, C["sticky-buy"], add_short)}
  </div>

{split_tag(p.get("experiment_id", ""))}</body>
</html>
"""


META_PIXEL_ID = "1762938528379464"


def with_meta_pixel(p, variant, html_):
    """Add the Prohall Meta Pixel: PageView + ViewContent on load, AddToCart on add-to-cart
    clicks. Purchase is left to Shopify's Meta integration at checkout."""
    prices = {v["id"]: float(v["price"]) for v in p["variants"]}
    cfg = json.dumps({
        "ids": [v["id"] for v in p["variants"]],
        "prices": prices,
        "value": min(prices.values()),
        "name": p["name"],
        "page": f"{p['slug']}-{variant.lower()}",
        "variant": variant,
    })
    head = f"""  <!-- Meta Pixel {META_PIXEL_ID}: PageView + ViewContent on load, AddToCart on add-to-cart clicks.
       Purchase is sent by Shopify's Meta integration at checkout, never from this page. -->
  <script>
  !function(f,b,e,v,n,t,s){{if(f.fbq)return;n=f.fbq=function(){{n.callMethod?
  n.callMethod.apply(n,arguments):n.queue.push(arguments)}};if(!f._fbq)f._fbq=n;
  n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;
  t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}}(window,
  document,'script','https://connect.facebook.net/en_US/fbevents.js');
  fbq('init', '{META_PIXEL_ID}');
  fbq('track', 'PageView');
  (function () {{
    var P = {cfg};
    var base = {{ content_type: 'product', content_name: P.name, currency: 'USD', landing_page: P.page, landing_variant: P.variant }};
    fbq('track', 'ViewContent', Object.assign({{ content_ids: P.ids, value: P.value }}, base));
    document.addEventListener('click', function (e) {{
      var a = e.target && e.target.closest ? e.target.closest('a[href*="/cart/"]') : null;
      var m = a && a.getAttribute('href').match(/\\/cart\\/(\\d+):(\\d+)/);
      if (!m) return;
      var qty = Number(m[2]);
      fbq('track', 'AddToCart', Object.assign({{ content_ids: [m[1]], num_items: qty, value: (P.prices[m[1]] || P.value) * qty }}, base));
    }}, true);
  }})();
  </script>
</head>"""
    noscript = (f'\n  <noscript><img height="1" width="1" style="display:none" alt="" '
                f'src="https://www.facebook.com/tr?id={META_PIXEL_ID}&amp;ev=PageView&amp;noscript=1"></noscript>')
    assert html_.count("</head>") == 1
    html_ = html_.replace("</head>", head)
    html_, n = re.subn(r'(<body[^>]*>)', lambda m: m.group(1) + noscript, html_, count=1)
    assert n == 1
    return html_



def render_pair(p):
    """Return {relative path: text} for one pair: a/, b/ and assets/ (CSS)."""
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    styles = lambda name: open(os.path.join(here, "styles", name)).read()
    css_a = styles("base.css").replace(
        "/* Prohall Select One — shared layout for versions A and B.",
        f"/* {p['name']} — shared layout for versions A and B.", 1) + styles("white-base.css")
    css_b = styles("b.css") + styles("white-b.css")
    return {
        "a/index.html": with_meta_pixel(p, "A", page_a(p)),
        "b/index.html": with_meta_pixel(p, "B", page_b(p)),
        "assets/styles.css": css_a,
        "assets/styles-b.css": css_b,
    }
