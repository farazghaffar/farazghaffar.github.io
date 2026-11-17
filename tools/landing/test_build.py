"""Tests for the tracked landing-page builder. Run:  python3 -m unittest discover -s tools/landing -v

Everything is built into temporary folders; nothing touches the published site.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
BUILD = os.path.join(HERE, "build.py")
TAG_SRC = "https://split-ivory-one.vercel.app/external-landing.js"


def run(root, *args, ok=True):
    r = subprocess.run([sys.executable, BUILD, "--root", root, *args], capture_output=True, text=True)
    if ok and r.returncode != 0:
        raise AssertionError(f"build.py {' '.join(args)} failed:\n{r.stdout}\n{r.stderr}")
    return r


def read(root, *parts):
    with open(os.path.join(root, *parts)) as f:
        return f.read()


class TrackedLandingPages(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="landing-test-")

    def tearDown(self):
        shutil.rmtree(self.root)

    def make(self, slug, product, experiment=""):
        args = ["new", slug, "--product", product] + (["--experiment", experiment] if experiment else [])
        run(self.root, *args)
        run(self.root, "build", slug)

    def tags(self, slug, v):
        page = read(self.root, slug, v, "index.html")
        return page, re.findall(r"<script[^>]*" + re.escape(TAG_SRC) + r"[^>]*>", page, re.S)

    def test_pair_has_distinct_urls_and_same_experiment_id(self):
        self.make("exp-one", "select-one", "first-experiment-0001")
        a, tags_a = self.tags("exp-one", "a")
        b, tags_b = self.tags("exp-one", "b")
        self.assertNotEqual(os.path.join("exp-one", "a"), os.path.join("exp-one", "b"))
        self.assertEqual(len(tags_a), 1)
        self.assertEqual(len(tags_b), 1)
        self.assertEqual(re.findall(r'data-split-experiment="([^"]*)"', a), ["first-experiment-0001"])
        self.assertEqual(re.findall(r'data-split-experiment="([^"]*)"', b), ["first-experiment-0001"])
        self.assertIn('data-split-storefront="shop.prohall.ai"', tags_a[0])
        self.assertIn("<script defer\n", a)

    def test_second_experiment_does_not_change_first_pair(self):
        self.make("exp-one", "select-one", "first-experiment-0001")
        before = {v: read(self.root, "exp-one", v, "index.html") for v in "ab"}
        self.make("exp-two", "equalize", "second-experiment-0002")
        run(self.root, "build", "exp-one")  # rebuilding the first pair keeps its own id
        for v in "ab":
            self.assertEqual(read(self.root, "exp-one", v, "index.html"), before[v])
            self.assertIn('data-split-experiment="second-experiment-0002"', read(self.root, "exp-two", v, "index.html"))
        # changing the id of an already-built pair is refused
        cfg_path = os.path.join(self.root, "pages", "exp-one.json")
        with open(cfg_path) as f:
            cfg = json.load(f)
        cfg["experiment_id"] = "second-experiment-0002"
        with open(cfg_path, "w") as f:
            json.dump(cfg, f)
        r = run(self.root, "build", "exp-one", ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("new slug", r.stderr)
        self.assertEqual(read(self.root, "exp-one", "a", "index.html"), before["a"])

    def test_unconfigured_page_has_no_tag_and_working_shop_links(self):
        self.make("starter", "burix-one")
        for v in "ab":
            page, tags = self.tags("starter", v)
            self.assertEqual(tags, [])
            self.assertNotIn("external-landing.js", page)
            self.assertNotIn("data-split-experiment", page)
            links = re.findall(r'href="(https://shop\.prohall\.ai/[^"]*)"', page)
            self.assertIn("https://shop.prohall.ai/cart/48091127808177:1", links)
            self.assertIn("https://shop.prohall.ai/cart/48091127840945:1", links)
            self.assertIn("https://shop.prohall.ai/collections/all", links)

    def test_labels_on_sections_and_buttons_match_across_a_and_b(self):
        self.make("labels", "burix-one", "label-experiment-0003")
        found = {}
        for v in "ab":
            page = read(self.root, "labels", v, "index.html")
            sections = re.findall(r'<section [^>]*data-split-section="([a-z0-9-]+)"', page)
            ctas = re.findall(r'<a [^>]*data-split-cta="([a-z0-9-]+)"', page)
            self.assertEqual(len(ctas), len(set(ctas)), "each placement has its own label")
            # labels sit on the clickable element itself
            self.assertRegex(page, r'<a class="btn btn-primary" href="https://shop\.prohall\.ai/cart/48091127808177:1"|<a class="size-card" href="https://shop\.prohall\.ai/cart/48091127808177:1" data-split-cta="pricing-buy-4-oz">')
            found[v] = (sorted(sections), sorted(ctas))
        self.assertEqual(found["a"], found["b"])
        sections, ctas = found["a"]
        self.assertEqual(sections, sorted(["hero", "benefits", "details", "ingredients", "how-to-use", "pricing", "faq", "final-cta"]))
        self.assertEqual(ctas, sorted(["header-buy", "hero-buy", "hero-how-to", "mid-page-buy", "pricing-buy-4-oz",
                                       "pricing-buy-10-oz", "final-buy", "browse-all", "sticky-buy"]))

    def test_rejects_ids_that_are_not_experiment_ids(self):
        for bad in ["8069155422385", "b7f73a06d88a5a9c24df", "Select One"]:
            r = run(self.root, "new", "bad", "--product", "select-one", "--experiment", bad, ok=False)
            self.assertNotEqual(r.returncode, 0, bad)
            self.assertFalse(os.path.exists(os.path.join(self.root, "pages", "bad.json")))

    def test_never_writes_into_folders_it_did_not_create(self):
        os.makedirs(os.path.join(self.root, "select-one", "a"))
        with open(os.path.join(self.root, "select-one", "a", "index.html"), "w") as f:
            f.write("published page")
        r = run(self.root, "new", "select-one", "--product", "select-one", ok=False)
        self.assertNotEqual(r.returncode, 0)
        os.makedirs(os.path.join(self.root, "pages"), exist_ok=True)
        with open(os.path.join(HERE, "products", "select-one.json")) as f:
            cfg = json.load(f)
        with open(os.path.join(self.root, "pages", "select-one.json"), "w") as f:
            json.dump({"slug": "select-one", "experiment_id": "", **cfg}, f)
        r = run(self.root, "build", "select-one", ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(read(self.root, "select-one", "a", "index.html"), "published page")

    def test_published_pairs_have_no_builder_lock(self):
        """The hand-published pairs in this repository are outside the builder's reach."""
        for slug in ["select-one", "miracle-therapy", "equalize", "burix-one", "absolut-one"]:
            if os.path.isdir(os.path.join(REPO, slug)):
                self.assertFalse(os.path.exists(os.path.join(REPO, slug, "landing.lock.json")), slug)


if __name__ == "__main__":
    unittest.main()
