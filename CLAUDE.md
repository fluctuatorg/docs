# Xendit Documentation — Mintlify Site

## Project Overview

Xendit documentation site built on [Mintlify](https://mintlify.com/). Migrated from Document360 in March 2026.

## Key Files

- `docs.json` — Mintlify site configuration (navigation, theme, metadata)
- `scripts/convert_doc360.py` — Conversion script: Doc360 JSON export → Mintlify MDX
- `scripts/redirect-rules.csv` — Doc360 redirect rules (used for slug alias resolution during conversion)
- `scripts/navigation.json` — Generated navigation structure reference

## Document360 Export

Located at `export-from-doc360/Xendit-Documentations-2026-Mar-26-06-31-10/v1/`:

- `articles/` — 471 JSON files, each containing an array of language variants (en, id, th, es-mx). Each variant has `Code`, `Title`, `Slug`, `Content` (HTML), `SeoTitle`, `Description`.
- `categories/` — 9 category JSON files with `Languages`, `SubCategories`, `Articles` arrays.
- `v1_categories_articles.json` — Master category/article hierarchy index.
- `../Media/Images/` — 1340 exported image files.

## Conversion Script (`scripts/convert_doc360.py`)

Re-runnable. Reads the Doc360 export and overwrites all MDX files + `scripts/navigation.json`.

### What it does:
1. Reads category hierarchy from `v1_categories_articles.json`
2. Converts each article's HTML content to MDX using `markdownify` + BeautifulSoup
3. Maps Doc360 admonition boxes (infoBox, warningBox, etc.) to Mintlify components (`<Info>`, `<Warning>`, `<Tip>`)
4. Preserves iframes (Airtable embeds, YouTube, Vercel apps) as `<iframe>` tags
5. Resolves CDN image URLs to local files via case-insensitive filename index → `images/doc360/`
6. Escapes MDX-breaking characters (`{}`, `<>`, invalid JSX tags) outside code blocks
7. Filters out content using multiple criteria:
   - `[Internal]` title prefix
   - `internal-notes` HTML sections
   - Draft categories
   - Doc360 API statuses (`scripts/doc360-article-statuses.json`): hidden articles, private/restricted articles (security_visibility > 0), and never-published drafts (status=0 + public_version=0)
8. Rewrites internal links from Doc360 format (`/docs/slug`, `/v1/docs/slug`) to Mintlify paths using slug-to-path mapping + redirect CSV aliases
9. Generates navigation structure for `docs.json`

### To re-run:
```bash
python3 scripts/convert_doc360.py
```
Then manually update `docs.json` navigation from `scripts/navigation.json` if the category structure changed.

## Content Structure

- 273 converted MDX articles (180 excluded as internal/hidden/private/never-published)
- Embedded iframes preserved (Airtable tables, YouTube, Vercel apps)
- 283 local images in `images/doc360/`
- 243 internal links rewritten; 9 unresolved (point to excluded or empty articles)

## Development

```bash
npx mintlify dev          # Start dev server (default port 3000)
npx mintlify dev --port N # Use custom port
```

## Multi-language

The Doc360 export contains content in en, id, th, es-mx. Currently only English (`en`) content is converted. The conversion script can be extended to handle other languages.
