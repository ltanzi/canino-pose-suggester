# Canino FM · Pose Suggester

Tiny single-page web tool for Canino FM. Pick a group size (1–5) and get a curated stick-figure pose suggestion drawn on an SVG canvas — used between takes in the elevator photo booth to give visiting artists a quick visual prompt. Poses are hand-authored and many of them assume the elevator's three walls (back wall against the head, side walls for a foot up, a hand against, peeking around a corner, etc.).

No framework, no build step. Vanilla HTML + CSS + JS. Served as static files.

## Run locally

JSON files are loaded via `fetch()`, so opening `index.html` directly with `file://` will fail in most browsers. Serve the folder:

```sh
cd canino-pose-suggester
python -m http.server 8000
```

Then open <http://localhost:8000/>.

Any other tiny static server works equivalently (`npx serve`, `php -S`, etc.).

## Deploy to GitHub Pages

1. Push this folder to a public repo (e.g. `canino-pose-suggester`).
2. Repo **Settings → Pages**.
3. **Source**: *Deploy from a branch*. **Branch**: `main`, folder `/ (root)`. Save.
4. After a minute, visit `https://<your-username>.github.io/canino-pose-suggester/`.

No build, no Actions, no extra config. All asset paths are relative so the project subpath works out of the box.

## Repo layout

```
canino-pose-suggester/
├── index.html
├── style.css
├── app.js
└── poses/
    ├── 1.json   16 solo poses
    ├── 2.json   14 duo poses
    ├── 3.json   14 trio poses
    ├── 4.json    8 quartet poses
    └── 5.json    8 quintet poses
```

Each `poses/N.json` is an array of pose objects. A pose looks like:

```jsonc
{
  "id": "2-back-to-back",
  "name": "Back to back",
  "tags": ["serious", "symmetric"],
  "figures": [
    { "head": { "cx": 370, "cy": 110, "r": 22 }, "lines": [ /* ... */ ] },
    { "head": { "cx": 430, "cy": 110, "r": 22 }, "lines": [ /* ... */ ] }
  ]
}
```

- `figures.length` must equal the group size; mismatches are surfaced as a console warning.
- `tags` carry mood (`serious`, `fun`, `energetic`, `chill`) and descriptors (`static`, `dynamic`, `symmetric`, `playful`, `casual`, `intimate`, `dreamy`, `neutral`). The selection function already supports tag-based filtering — a mood filter UI is intentionally not in v1.
- Coordinate space is a fixed `viewBox="0 0 800 500"` with the implied elevator walls at `x=50` (left), `x=750` (right), and `y=360` (floor). New poses can lean against, push off, or otherwise interact with these.

## Adding new poses

1. Open the appropriate `poses/N.json`.
2. Add a new object to the array. Pick an `id` of the form `N-short-name`.
3. Each figure has one `head` circle and an array of `lines`. Body part `id`s like `torso`, `leftArm` are just hints for the human author — the renderer draws every entry as a `<line>`.
4. Refresh the page. The next Generate / Regenerate on that group size may pick your new pose.

## Customizing the look

Palette lives in CSS custom properties at the top of `style.css` — `--bg`, `--accent`, `--wall`, `--text`, `--border`. Swap in Canino FM's actual brand color by changing `--accent` only; the rest of the design is built from neutral tones.
