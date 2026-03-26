#!/usr/bin/env python3
"""
Convert Document360 JSON export to Mintlify MDX pages.

Usage:
    python3 scripts/convert_doc360.py

Reads from: export-from-doc360/Xendit-Documentations-2026-Mar-26-06-31-10/v1/
Writes to:  docs/ (organized by category slug)
"""

import json
import os
import re
import shutil
import sys
import urllib.parse
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString
from markdownify import MarkdownConverter

# Paths
ROOT = Path(__file__).resolve().parent.parent
EXPORT_BASE = ROOT / "export-from-doc360" / "Xendit-Documentations-2026-Mar-26-06-31-10"
EXPORT_DIR = EXPORT_BASE / "v1"
ARTICLES_DIR = EXPORT_DIR / "articles"
CATEGORIES_DIR = EXPORT_DIR / "categories"
INDEX_FILE = EXPORT_DIR / "v1_categories_articles.json"
MEDIA_DIR = EXPORT_BASE / "Media" / "Images"
OUTPUT_DIR = ROOT
IMAGES_OUTPUT_DIR = ROOT / "images" / "doc360"

# Build image lookup index: lowercase filename -> actual path
IMAGE_INDEX = {}
if MEDIA_DIR.exists():
    for img_file in MEDIA_DIR.iterdir():
        if img_file.is_file():
            IMAGE_INDEX[img_file.name.lower()] = img_file

# Stats
stats = {
    "converted": 0,
    "skipped_internal": 0,
    "skipped_draft": 0,
    "skipped_empty": 0,
    "internal_sections_stripped": 0,
    "images_resolved": 0,
    "images_unresolved": 0,
    "links_rewritten": 0,
    "links_unresolved": 0,
}

# Slug → Mintlify path mapping (populated during conversion)
SLUG_TO_PATH = {}

# Load slug aliases from Doc360 redirect rules CSV
SLUG_ALIASES = {}
REDIRECT_CSV = ROOT / "scripts" / "redirect-rules.csv"
if REDIRECT_CSV.exists():
    import csv
    with open(REDIRECT_CSV, "r", encoding="utf-8-sig") as _f:
        for _row in csv.DictReader(_f):
            _src = _row.get("Source", "").strip()
            _dst = _row.get("Destination", "").strip()
            if not _src or not _dst:
                continue
            _src_m = re.match(r"^/(?:v\d+/)?docs/(?:(?:en|id|th|es-mx)/)?([a-z0-9][a-z0-9_-]+)$", _src)
            if not _src_m:
                continue
            _dst_m = re.match(
                r"^(?:https?://[^/]+)?/?(?:v\d+/)?docs/(?:(?:en|id|th|es-mx)/)?([a-z0-9][a-z0-9_-]+)$", _dst
            )
            if _dst_m and _src_m.group(1) != _dst_m.group(1):
                SLUG_ALIASES[_src_m.group(1)] = _dst_m.group(1)

# Load article statuses from Doc360 API export
# Exclude: hidden, private (security_visibility > 0), or never-published drafts
EXCLUDE_SLUGS = set()
ARTICLE_STATUSES_FILE = ROOT / "scripts" / "doc360-article-statuses.json"
if ARTICLE_STATUSES_FILE.exists():
    with open(ARTICLE_STATUSES_FILE) as _f:
        _api_data = json.load(_f)
    for _a in _api_data.get("data", []):
        _slug = _a["slug"]
        _hidden = _a.get("hidden", False)
        _private = _a.get("security_visibility", 0) > 0
        _never_published = _a.get("status") == 0 and _a.get("public_version", 0) == 0
        if _hidden or _private or _never_published:
            EXCLUDE_SLUGS.add(_slug)
    print(f"Article status filter: {len(EXCLUDE_SLUGS)} slugs excluded (hidden/private/never-published)")


def resolve_image(cdn_url):
    """Resolve a CDN URL to a local image from the export Media directory."""
    # Extract filename from URL
    parsed = cdn_url.split("/")[-1]
    parsed = urllib.parse.unquote(parsed)

    # Try exact match first
    if parsed.lower() in IMAGE_INDEX:
        src_path = IMAGE_INDEX[parsed.lower()]
        safe_name = re.sub(r'[^\w\-.]', '_', parsed)
        dest = IMAGES_OUTPUT_DIR / safe_name
        if not dest.exists():
            IMAGES_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dest)
        stats["images_resolved"] += 1
        return "/" + str(dest.relative_to(ROOT))

    # Try partial match (filename without query params, etc.)
    base_name = parsed.split("?")[0]
    if base_name.lower() in IMAGE_INDEX:
        src_path = IMAGE_INDEX[base_name.lower()]
        safe_name = re.sub(r'[^\w\-.]', '_', base_name)
        dest = IMAGES_OUTPUT_DIR / safe_name
        if not dest.exists():
            IMAGES_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dest)
        stats["images_resolved"] += 1
        return "/" + str(dest.relative_to(ROOT))

    stats["images_unresolved"] += 1
    return cdn_url  # Keep original URL as fallback


class Doc360Converter(MarkdownConverter):
    """Custom markdownify converter for Document360 HTML."""

    def convert_section(self, el, text, **kwargs):
        if "internal-notes" in el.get("class", []):
            stats["internal_sections_stripped"] += 1
            return ""
        return text

    def convert_div(self, el, text, **kwargs):
        classes = el.get("class", [])
        if isinstance(classes, str):
            classes = classes.split()

        # Doc360 admonition boxes
        if "infoBox" in classes:
            return f"\n<Info>\n{text.strip()}\n</Info>\n\n"
        if "warningBox" in classes:
            return f"\n<Warning>\n{text.strip()}\n</Warning>\n\n"
        if "dangerBox" in classes:
            return f"\n<Warning>\n{text.strip()}\n</Warning>\n\n"
        if "successBox" in classes:
            return f"\n<Tip>\n{text.strip()}\n</Tip>\n\n"

        # Doc360 admonition_admonition class with inline style color hints
        if any("admonition" in c for c in classes):
            style = el.get("style", "")
            if "rgb(239, 68, 68)" in style or "red" in style.lower():
                return f"\n<Warning>\n{text.strip()}\n</Warning>\n\n"
            if "rgb(245, 158, 11)" in style or "orange" in style.lower() or "yellow" in style.lower():
                return f"\n<Warning>\n{text.strip()}\n</Warning>\n\n"
            if "rgb(16, 185, 129)" in style or "green" in style.lower():
                return f"\n<Tip>\n{text.strip()}\n</Tip>\n\n"
            return f"\n<Info>\n{text.strip()}\n</Info>\n\n"

        if el.get("data-type") == "table-content":
            return text

        return text

    def convert_img(self, el, text, **kwargs):
        src = el.get("src", "")
        alt = el.get("alt", "")
        if not src:
            return ""
        if "cdn.document360.io" in src:
            src = resolve_image(src)
        return f"![{alt}]({src})"

    def convert_pre(self, el, text, **kwargs):
        code_el = el.find("code")
        if code_el:
            classes = code_el.get("class", [])
            if isinstance(classes, str):
                classes = classes.split()
            lang = ""
            for c in classes:
                if c.startswith("language-"):
                    lang = c.replace("language-", "")
                    break
            code_text = code_el.get_text()
            return f"\n```{lang}\n{code_text}\n```\n\n"
        return f"\n```\n{text}\n```\n\n"

    def convert_iframe(self, el, text, **kwargs):
        src = el.get("src", "")
        if not src:
            return ""
        title = el.get("title", "Embedded content")
        # Preserve height from original; default based on content type
        height = el.get("height", "")
        if not height:
            if "airtable" in src:
                height = "533"
            elif "youtube" in src or "youtu.be" in src:
                height = "400"
            else:
                height = "500"
        # Use className for Mintlify MDX; must use opening+closing tags (not self-closing)
        return f'\n<iframe src="{src}" title="{title}" className="w-full rounded-xl" height="{height}"></iframe>\n\n'

    def convert_hr(self, el, text, **kwargs):
        return "\n---\n\n"


def html_to_mdx(html_content):
    """Convert Document360 HTML to clean MDX."""
    if not html_content:
        return ""

    soup = BeautifulSoup(html_content, "html.parser")

    # Remove internal-notes sections
    for section in soup.find_all("section", class_="internal-notes"):
        stats["internal_sections_stripped"] += 1
        section.decompose()

    # Remove <style> tags entirely
    for style in soup.find_all("style"):
        style.decompose()

    # Remove empty paragraphs (spacers) — but keep ones with embedded content
    for p in soup.find_all("p"):
        if not p.get_text(strip=True) and not p.find("img") and not p.find("iframe"):
            p.decompose()

    html_content = str(soup)

    result = Doc360Converter(
        heading_style="atx",
        bullets="-",
        strong_em_symbol="*",
        strip=["style", "span"],
    ).convert(html_content)

    # Clean up
    result = re.sub(r'\n{4,}', '\n\n\n', result)
    result = re.sub(r'\s*data-block-id="[^"]*"', '', result)
    result = re.sub(r'\s*style="[^"]*"', '', result)
    result = re.sub(r'\*\*\s*\*\*', '', result)
    result = re.sub(r'\*\s*\*', '', result)

    # Escape curly braces for MDX (JSX interprets {} as expressions)
    # But preserve braces inside code blocks
    result = escape_braces_outside_code(result)

    # Escape <> (empty JSX fragments) used as text like "Xendit <> Midtrans"
    result = result.replace('<>', '&lt;&gt;')

    # Escape </path...> patterns (broken link references, not closing tags)
    result = re.sub(r'</([^a-zA-Z>])', r'&lt;/\1', result)
    # Also </v1 etc — closing tag-like with path content
    result = re.sub(r'</v\d', r'&lt;/v', result)

    # Escape angle brackets that look like HTML but aren't valid JSX
    # e.g., <put>, <something>, <input ...> etc. — except our Mintlify components
    mintlify_tags = {'Info', 'Warning', 'Tip', 'Note', 'iframe'}
    result = escape_invalid_jsx_tags(result, mintlify_tags)

    # Remove leftover CSS blocks (/* ... */ patterns outside code blocks)
    result = re.sub(r'/\\\*.*?\\\*/', '', result, flags=re.DOTALL)
    # Clean up lines that are just CSS properties
    result = re.sub(r'^[a-z-]+\s*:\s*[^;]+;\s*$', '', result, flags=re.MULTILINE)

    # Clean excessive blank lines again after all processing
    result = re.sub(r'\n{4,}', '\n\n\n', result)

    return result.strip()


def escape_braces_outside_code(text):
    """Escape { and } outside of code blocks/spans for MDX compatibility."""
    parts = re.split(r'(```[\s\S]*?```|`[^`]+`)', text)
    for i, part in enumerate(parts):
        # Only escape in non-code parts
        if not part.startswith('`'):
            # Escape { and } but not inside our Mintlify JSX tags
            part = re.sub(r'(?<!\<)\{(?!/)', r'&#123;', part)
            part = re.sub(r'(?<!/)\}(?!\>)', r'&#125;', part)
            parts[i] = part
    return ''.join(parts)


def escape_invalid_jsx_tags(text, valid_tags):
    """Escape HTML-like tags that aren't valid Mintlify components."""
    def replace_tag(m):
        tag_name = m.group(1)
        if tag_name in valid_tags:
            return m.group(0)
        # Escape the angle bracket
        return m.group(0).replace('<', '&lt;').replace('>', '&gt;')

    # Match opening tags like <something> or <something attr="val">
    text = re.sub(r'<([a-zA-Z][a-zA-Z0-9]*)\b[^>]*/>', lambda m: m.group(0) if m.group(1) in valid_tags else m.group(0).replace('<', '&lt;').replace('>', '&gt;'), text)
    text = re.sub(r'<([a-zA-Z][a-zA-Z0-9]*)\b[^>]*>(?!</)', lambda m: m.group(0) if m.group(1) in valid_tags else replace_tag(m), text)
    text = re.sub(r'</([a-zA-Z][a-zA-Z0-9]*)>', lambda m: m.group(0) if m.group(1) in valid_tags else m.group(0).replace('<', '&lt;').replace('>', '&gt;'), text)

    return text


def make_frontmatter(title, description=None, seo_title=None):
    safe_title = title.replace('"', '\\"')
    lines = ['---', f'title: "{safe_title}"']
    if seo_title and seo_title != title:
        safe_seo = seo_title.replace('"', '\\"')
        lines.append(f'seoTitle: "{safe_seo}"')
    if description:
        safe_desc = description.replace('"', '\\"')
        lines.append(f'description: "{safe_desc}"')
    lines.append('---')
    return '\n'.join(lines)


def should_skip_article(article_data):
    """Check if article should be excluded: internal, hidden, private, or never-published draft."""
    en = next((a for a in article_data if a["Code"] == "en"), None)
    if not en:
        return True
    title = en.get("Title", "")
    slug = en.get("Slug", "")
    if "[Internal]" in title:
        return True
    if slug in EXCLUDE_SLUGS:
        return True
    return False


def convert_article(article_file, output_path):
    """Convert a single article JSON file to MDX."""
    with open(article_file) as f:
        data = json.load(f)

    en = next((a for a in data if a["Code"] == "en"), None)
    if not en:
        stats["skipped_empty"] += 1
        return None

    if should_skip_article(data):
        stats["skipped_internal"] += 1
        return None

    title = en["Title"]
    content = en.get("Content", "")
    if not content:
        stats["skipped_empty"] += 1
        return None

    mdx_content = html_to_mdx(content)
    frontmatter = make_frontmatter(
        title=title,
        description=en.get("Description"),
        seo_title=en.get("SeoTitle"),
    )
    full_content = f"{frontmatter}\n\n{mdx_content}\n"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(full_content)

    # Register slug → path mapping for internal link rewriting
    art_slug = en["Slug"]
    rel_path = str(output_path.relative_to(OUTPUT_DIR)).replace(".mdx", "")
    SLUG_TO_PATH[art_slug] = rel_path
    # Also register the filename stem (often used as link target in Doc360)
    file_stem = article_file.stem
    if file_stem != art_slug:
        SLUG_TO_PATH[file_stem] = rel_path

    stats["converted"] += 1
    return output_path


def get_category_slug(cat):
    for lang in cat.get("Languages", []):
        if lang["Code"] == "en":
            return lang["Slug"]
    return cat.get("Title", "unknown").lower().replace(" ", "-")


def get_category_title(cat):
    for lang in cat.get("Languages", []):
        if lang["Code"] == "en":
            return lang["Title"]
    return cat.get("Title", "Unknown")


def is_draft_category(cat):
    title = get_category_title(cat).lower()
    return "draft" in title


def process_category(cat, parent_path, nav_items):
    """Recursively process a category and its articles/subcategories.

    parent_path: relative path from OUTPUT_DIR (e.g. Path("get-started"))
    """
    slug = get_category_slug(cat)
    title = get_category_title(cat)

    if is_draft_category(cat):
        print(f"  SKIP draft category: {title}")
        return

    cat_path = parent_path / slug
    group = {"group": title, "pages": []}

    # Process articles (sorted by Order)
    articles = sorted(cat.get("Articles", []), key=lambda a: a.get("Order", 999))
    for article in articles:
        art_filename = article.get("Path")
        if not art_filename:
            continue

        art_file = ARTICLES_DIR / art_filename
        if not art_file.exists():
            print(f"  WARNING: Article file not found: {art_filename}")
            continue

        with open(art_file) as f:
            art_data = json.load(f)

        if should_skip_article(art_data):
            stats["skipped_internal"] += 1
            print(f"  SKIP internal: {art_data[0].get('Title', art_filename)}")
            continue

        en = next((a for a in art_data if a["Code"] == "en"), None)
        if not en:
            continue

        art_slug = en["Slug"]
        output_file = OUTPUT_DIR / cat_path / f"{art_slug}.mdx"
        result = convert_article(art_file, output_file)

        if result:
            nav_path = str(cat_path / art_slug)
            group["pages"].append(nav_path)

    # Process subcategories — each becomes a nested group directly
    subcats = sorted(cat.get("SubCategories", []), key=lambda c: c.get("Order", 999))
    for subcat in subcats:
        subcat_title = get_category_title(subcat)
        if is_draft_category(subcat):
            print(f"  SKIP draft category: {subcat_title}")
            continue
        subcat_slug = get_category_slug(subcat)
        subcat_path = cat_path / subcat_slug
        sub_pages = []

        # Process subcat articles
        sub_articles = sorted(subcat.get("Articles", []), key=lambda a: a.get("Order", 999))
        for article in sub_articles:
            art_filename = article.get("Path")
            if not art_filename:
                continue
            art_file = ARTICLES_DIR / art_filename
            if not art_file.exists():
                continue
            with open(art_file) as f:
                art_data = json.load(f)
            if should_skip_article(art_data):
                stats["skipped_internal"] += 1
                continue
            en = next((a for a in art_data if a["Code"] == "en"), None)
            if not en:
                continue
            art_slug = en["Slug"]
            output_file = OUTPUT_DIR / subcat_path / f"{art_slug}.mdx"
            result = convert_article(art_file, output_file)
            if result:
                sub_pages.append(str(subcat_path / art_slug))

        # Recurse deeper subcategories
        for deeper in sorted(subcat.get("SubCategories", []), key=lambda c: c.get("Order", 999)):
            deeper_group = {"group": get_category_title(deeper), "pages": []}
            process_category(deeper, subcat_path, deeper_group["pages"])
            if deeper_group["pages"]:
                sub_pages.append(deeper_group)

        if sub_pages:
            group["pages"].append({"group": subcat_title, "pages": sub_pages})

    if group["pages"]:
        nav_items.append(group)


def rewrite_internal_links():
    """Rewrite old Document360 internal links to new Mintlify paths."""
    # Pattern matches /docs/slug or /v1/docs/slug (with optional trailing slash or anchor)
    link_pattern = re.compile(r'(?:\(/v\d+)?/docs/([a-z0-9][a-z0-9_-]*?)([#)?])')

    unresolved_slugs = set()
    files_updated = 0

    for mdx_file in OUTPUT_DIR.rglob("*.mdx"):
        content = mdx_file.read_text()

        def replace_link(m):
            slug = m.group(1)
            suffix = m.group(2)

            # Try direct match, then alias
            resolved_slug = slug
            if slug not in SLUG_TO_PATH and slug in SLUG_ALIASES:
                resolved_slug = SLUG_ALIASES[slug]

            if resolved_slug in SLUG_TO_PATH:
                stats["links_rewritten"] += 1
                return f"(/{SLUG_TO_PATH[resolved_slug]}{suffix}"
            else:
                unresolved_slugs.add(slug)
                stats["links_unresolved"] += 1
                return m.group(0)

        # Replace /docs/slug and /v1/docs/slug patterns in markdown links
        new_content = re.sub(
            r'\(/(?:v\d+/)?docs/([a-z0-9][a-z0-9_-]*?)([#\)"])',
            replace_link,
            content,
        )

        # Also handle bare URLs (not in markdown link syntax) like [text](/docs/slug)
        # Already covered above since markdown links use (url) syntax

        if new_content != content:
            mdx_file.write_text(new_content)
            files_updated += 1

    if unresolved_slugs:
        print(f"\n  Unresolved link slugs ({len(unresolved_slugs)}):")
        for s in sorted(unresolved_slugs)[:20]:
            print(f"    - {s}")
        if len(unresolved_slugs) > 20:
            print(f"    ... and {len(unresolved_slugs) - 20} more")

    print(f"\n  Internal links rewritten: {stats['links_rewritten']} in {files_updated} files")
    print(f"  Unresolved link slugs:   {stats['links_unresolved']}")


def main():
    print("=" * 60)
    print("Document360 → Mintlify Conversion")
    print("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Build category tree
    with open(INDEX_FILE) as f:
        index = json.load(f)
    categories = index["Categories"]
    print(f"\nFound {len(categories)} root categories")
    print(f"Image index: {len(IMAGE_INDEX)} files from Media export")

    # Process each root category — parent_path starts empty (relative to OUTPUT_DIR)
    navigation_groups = []
    for cat in sorted(categories, key=lambda c: c.get("Order", 999)):
        title = get_category_title(cat)
        print(f"\nProcessing category: {title}")
        process_category(cat, Path(""), navigation_groups)

    # Find orphan articles (not in any category)
    categorized_paths = set()
    def collect_paths(cats):
        for c in cats:
            for a in c.get("Articles", []):
                if a.get("Path"):
                    categorized_paths.add(a["Path"])
            collect_paths(c.get("SubCategories", []))
    collect_paths(categories)

    orphan_count = 0
    orphan_group = {"group": "Other", "pages": []}
    for art_file in sorted(ARTICLES_DIR.iterdir()):
        if art_file.name not in categorized_paths:
            with open(art_file) as f:
                art_data = json.load(f)
            if should_skip_article(art_data):
                stats["skipped_internal"] += 1
                continue
            en = next((a for a in art_data if a["Code"] == "en"), None)
            if not en or not en.get("Content"):
                stats["skipped_empty"] += 1
                continue
            art_slug = en["Slug"]
            result = convert_article(art_file, OUTPUT_DIR / "other" / f"{art_slug}.mdx")
            if result:
                orphan_group["pages"].append(f"other/{art_slug}")
                orphan_count += 1

    if orphan_group["pages"]:
        navigation_groups.append(orphan_group)

    # Rewrite internal links in all converted MDX files
    rewrite_internal_links()

    # Write navigation JSON for reference
    nav_output = ROOT / "scripts" / "navigation.json"
    with open(nav_output, "w") as f:
        json.dump(navigation_groups, f, indent=2)
    print(f"\nNavigation structure written to: {nav_output}")

    # Print summary
    print("\n" + "=" * 60)
    print("Conversion Summary")
    print("=" * 60)
    print(f"  Articles converted:          {stats['converted']}")
    print(f"  Skipped (internal):          {stats['skipped_internal']}")
    print(f"  Skipped (draft):             {stats['skipped_draft']}")
    print(f"  Skipped (empty/no English):  {stats['skipped_empty']}")
    print(f"  Internal sections stripped:   {stats['internal_sections_stripped']}")
    print(f"  Images resolved (local):     {stats['images_resolved']}")
    print(f"  Images unresolved:           {stats['images_unresolved']}")
    if orphan_count:
        print(f"  Orphan articles (uncategorized): {orphan_count}")


if __name__ == "__main__":
    main()
