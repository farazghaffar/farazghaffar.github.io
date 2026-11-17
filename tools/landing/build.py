#!/usr/bin/env python3
"""Create, build and check tracked Prohall A/B landing-page pairs.

  python3 tools/landing/build.py new <slug> --product <product> [--experiment <split-experiment-id>]
  python3 tools/landing/build.py build <slug>
  python3 tools/landing/build.py check [<slug> ...]

A pair is configured by pages/<slug>.json (a frozen copy of the product content
plus its own experiment_id) and published at /<slug>/a/ and /<slug>/b/.
`build` writes <slug>/landing.lock.json and refuses to:
  * write into a folder it did not create (the hand-published pairs stay untouched),
  * change the experiment id of an already-built pair (a new experiment = a new slug).
--root lets tests build into a temporary folder instead of the published site.
"""
import argparse
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import render  # noqa: E402

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LOCK = "landing.lock.json"
SITE = "https://prohall.us"


class BuildError(Exception):
    pass


def paths(root, pages_dir):
    root = os.path.abspath(root or REPO)
    pages_dir = os.path.abspath(pages_dir or os.path.join(root, "pages"))
    return root, pages_dir


def load_config(pages_dir, slug):
    path = os.path.join(pages_dir, slug + ".json")
    if not os.path.exists(path):
        raise BuildError(f"no config {path}; create it with: build.py new {slug} --product <product>")
    with open(path) as f:
        cfg = json.load(f)
    validate_config(cfg, slug)
    return cfg, path


def validate_config(cfg, slug):
    if cfg.get("slug") != slug:
        raise BuildError(f"config slug {cfg.get('slug')!r} does not match {slug!r}")
    try:
        cfg["experiment_id"] = render.validate_experiment_id(cfg.get("experiment_id", ""))
    except ValueError as err:
        raise BuildError(str(err))
    # Shopify destinations: product page handle and cart permalinks /cart/<variant>:1 (Split guide formats)
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", cfg.get("handle", "")):
        raise BuildError("handle must be a Shopify product handle, e.g. prohall-select-one")
    if not re.fullmatch(r"\d+", str(cfg.get("shopify_product_id", ""))):
        raise BuildError("shopify_product_id must be the numeric Shopify product id (Split run sales breakdown)")
    variants = cfg.get("variants") or []
    if not variants:
        raise BuildError("at least one Shopify variant is required")
    for v in variants:
        if not re.fullmatch(r"\d+", str(v.get("id", ""))):
            raise BuildError(f"variant id {v.get('id')!r} must be the numeric Shopify variant id")
        if not re.fullmatch(r"\d+(\.\d{2})?", str(v.get("price", ""))):
            raise BuildError(f"variant price {v.get('price')!r} must look like 69.99")


def cmd_new(args):
    root, pages_dir = paths(args.root, args.pages_dir)
    slug = args.slug
    if not SLUG_RE.match(slug):
        raise BuildError("slug must be lowercase letters, digits and hyphens, e.g. select-one-2")
    cfg_path = os.path.join(pages_dir, slug + ".json")
    if os.path.exists(cfg_path) or os.path.exists(os.path.join(root, slug)):
        raise BuildError(f"{slug!r} is already used (config or published folder); pick a new slug")
    product_path = os.path.join(HERE, "products", args.product + ".json")
    if not os.path.exists(product_path):
        choices = sorted(f[:-5] for f in os.listdir(os.path.join(HERE, "products")))
        raise BuildError(f"unknown product {args.product!r}; choose one of {choices}")
    with open(product_path) as f:
        content = json.load(f)
    cfg = {"slug": slug, "experiment_id": args.experiment or "", **content}
    validate_config(cfg, slug)
    os.makedirs(pages_dir, exist_ok=True)
    with open(cfg_path, "w") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"created {os.path.relpath(cfg_path, root)}  (experiment_id: {cfg['experiment_id'] or 'blank'})")
    print(f"next: edit it if needed, then  python3 tools/landing/build.py build {slug}")


def config_hash(cfg):
    return hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:16]


def build_one(root, pages_dir, slug):
    cfg, _ = load_config(pages_dir, slug)
    out = os.path.join(root, slug)
    lock_path = os.path.join(out, LOCK)
    if os.path.exists(out):
        if not os.path.exists(lock_path):
            raise BuildError(f"{slug}/ exists but was not created by this builder; it is left unchanged. Use a new slug.")
        with open(lock_path) as f:
            lock = json.load(f)
        if lock.get("experiment_id") and lock["experiment_id"] != cfg["experiment_id"]:
            raise BuildError(f"{slug}/ is already built for experiment {lock['experiment_id']!r}; "
                             f"a different experiment needs a new slug (build.py new <new-slug> ...)")
    files = render.render_pair(cfg)
    for rel, text in files.items():
        path = os.path.join(out, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(text)
    with open(lock_path, "w") as f:
        json.dump({"slug": slug, "experiment_id": cfg["experiment_id"], "config_sha256": config_hash(cfg)}, f, indent=2)
        f.write("\n")
    return cfg


def cmd_build(args):
    root, pages_dir = paths(args.root, args.pages_dir)
    for slug in args.slugs:
        cfg = build_one(root, pages_dir, slug)
        exp = cfg["experiment_id"] or "blank (no Split tag)"
        print(f"built {slug}: experiment {exp}")
        print(f"  A  {SITE}/{slug}/a/")
        print(f"  B  {SITE}/{slug}/b/")
        print(f"  Split run: promoted Shopify product ID {cfg['shopify_product_id']}")
    problems = check(root, args.slugs)
    for p in problems:
        print("CHECK FAILED:", p)
    if problems:
        sys.exit(1)


TAG_RE = re.compile(r'<script[^>]*src="' + re.escape(render.SPLIT_SCRIPT_SRC) + r'"[^>]*>', re.S)
EXPECTED_SECTIONS = {"hero", "benefits", "details", "ingredients", "how-to-use", "pricing", "faq", "final-cta"}
EXPECTED_CTAS = {"header-buy", "hero-buy", "hero-how-to", "mid-page-buy", "final-buy", "browse-all", "sticky-buy"}


def check(root, slugs=None):
    """Verify built pairs: one Split tag per page (zero when blank), same id on A and B,
    labels present and matching across A/B, Shopify links in supported formats."""
    problems = []
    if not slugs:
        slugs = sorted(d for d in os.listdir(root) if os.path.exists(os.path.join(root, d, LOCK)))
    for slug in slugs:
        with open(os.path.join(root, slug, LOCK)) as f:
            lock = json.load(f)
        labels = {}
        for v in ("a", "b"):
            page = open(os.path.join(root, slug, v, "index.html")).read()
            tags = TAG_RE.findall(page)
            ids = re.findall(r'data-split-experiment="([^"]*)"', page)
            if lock["experiment_id"]:
                if len(tags) != 1 or ids != [lock["experiment_id"]]:
                    problems.append(f"{slug}/{v}: expected 1 Split tag for {lock['experiment_id']}, found {len(tags)} {ids}")
            elif tags or ids or "external-landing.js" in page:
                problems.append(f"{slug}/{v}: blank experiment must render no Split tag")
            sections = set(re.findall(r'<section [^>]*data-split-section="([a-z0-9-]+)"', page))
            ctas = re.findall(r'<a [^>]*data-split-cta="([a-z0-9-]+)"', page)
            if not EXPECTED_SECTIONS <= sections:
                problems.append(f"{slug}/{v}: missing sections {sorted(EXPECTED_SECTIONS - sections)}")
            if not EXPECTED_CTAS <= set(ctas):
                problems.append(f"{slug}/{v}: missing buttons {sorted(EXPECTED_CTAS - set(ctas))}")
            if len(ctas) != len(set(ctas)):
                problems.append(f"{slug}/{v}: duplicate button labels {sorted(c for c in set(ctas) if ctas.count(c) > 1)}")
            for href in re.findall(r'href="(https://shop\.prohall\.ai[^"]*)"', page):
                path = href[len("https://shop.prohall.ai"):]
                if not re.fullmatch(r"/|/products/[a-z0-9-]+|/collections/[a-z0-9-]+|/cart|/cart/\d+:(10|[1-9])|/policies/[a-z-]+", path):
                    problems.append(f"{slug}/{v}: unsupported Shopify link {href}")
            labels[v] = (sections, sorted(ctas))
        if labels["a"] != labels["b"]:
            problems.append(f"{slug}: A and B labels differ: {labels['a']} vs {labels['b']}")
    return problems


def cmd_check(args):
    root, _ = paths(args.root, None)
    problems = check(root, args.slugs)
    for p in problems:
        print("CHECK FAILED:", p)
    if problems:
        sys.exit(1)
    print("check passed")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", help="site folder to build into (default: this repository)")
    ap.add_argument("--pages-dir", help="folder of pair configs (default: <root>/pages)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new", help="create pages/<slug>.json from a product in tools/landing/products")
    n.add_argument("slug")
    n.add_argument("--product", required=True)
    n.add_argument("--experiment", default="", help="Split experiment id from list_experiments (blank = no tag)")
    b = sub.add_parser("build", help="render <slug>/a/ and <slug>/b/ from pages/<slug>.json")
    b.add_argument("slugs", nargs="+")
    c = sub.add_parser("check", help="verify built pairs")
    c.add_argument("slugs", nargs="*")
    args = ap.parse_args(argv)
    try:
        {"new": cmd_new, "build": cmd_build, "check": cmd_check}[args.cmd](args)
    except BuildError as err:
        print("error:", err, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
