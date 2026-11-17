# Notes for Claude — Prohall landing pages (prohall.us)

Static A/B landing pages served by GitHub Pages from this repo. Builder: `tools/landing/build.py` (see README → "Create a tracked landing page").

## Split experiment id — rules when creating pages for a real experiment
- If the user has not given the Split experiment **name**, ask for it.
- Call the Split MCP tool `list_experiments` (check `nextPage` and fetch further pages) and pick the **non-archived** experiment whose name matches.
- Use that experiment's exact `id`. Never derive it from the name, and never use a run id, Shopify product id or variant id (`build.py` rejects all-digit and 20-hex ids).
- Several matches → ask which one. No match → ask the user to create it in Split or paste its installation snippet. MCP unavailable → use the `data-split-experiment` value from the snippet the user provides.
- A and B of a pair share the id; each pair has its own `pages/<slug>.json`. A new experiment always gets a new slug — `build.py` refuses to change the id of a built pair.
- Use MCP only while developing. Never put connector keys or dashboard credentials in pages, requests or this repo.

## Don't
- Don't edit the hand-published pairs (`select-one/`, `miracle-therapy/`, `equalize/`, `burix-one/`, `absolut-one/`) unless the user asks; the builder will not write into folders without `landing.lock.json`.
- Don't add a second Split loader: `render.split_tag()` is the only place the hosted tag is rendered.
- Don't claim live tracking works without seeing events from an active run's QA links (`list_runs` → `qaA`/`qaB`, then `get_results` with `source: "direct"`).
