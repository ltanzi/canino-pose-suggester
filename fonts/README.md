# Fonts

The page uses **Akzidenz-Grotesk**, a Berthold commercial typeface. It is not on Google Fonts and we don't bundle font files in this repo (no license to redistribute).

To use the real face, drop your licensed font files into this folder. The `@font-face` rules in `style.css` accept any of these formats — pick whichever you have:

```
fonts/
├── akzidenz-grotesk-regular.{woff2,woff,otf}   (weight 400)
└── akzidenz-grotesk-medium.{woff2,woff,otf}    (weight 500, optional)
```

`.woff2` is best (smallest, fastest). `.woff` is a slightly larger compressed variant. `.otf` works everywhere modern but is uncompressed — for an internal tool the size difference is negligible. To convert `.otf` → `.woff2` for the production deploy: `pyftsubset font.otf --flavor=woff2 --output-file=font.woff2` (needs `pip install fonttools brotli`), or use any online OTF→WOFF2 converter.

Until any of these files exist, the page silently falls back to the system sans-serif.

If you license the font with a different filename, either rename the files to match above or update the `src:` URLs at the top of `style.css`.

> If this repo is public, **do not commit the font files** — that violates Berthold's license. Keep the directory empty in version control and ship the font files separately to the deployment.
