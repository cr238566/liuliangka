#!/usr/bin/env python3
"""
流量卡推广网站静态站点生成器
用法: python generate.py
"""

import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

import markdown
from jinja2 import Environment, FileSystemLoader

BASE_DIR = Path(__file__).parent
SOURCE_DIR = BASE_DIR / "source"
TEMPLATES_DIR = BASE_DIR / "templates"
OUTPUT_DIR = BASE_DIR / "output"

# Load config
with open(SOURCE_DIR / "config.json", "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

# Category lookup
CAT_MAP = {c["slug"]: c["name"] for c in CONFIG["categories"]}

# Setup Jinja2
env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def parse_markdown_article(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    frontmatter = {}
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1].strip()
            body = parts[2].strip()
            for line in fm_text.split("\n"):
                if ":" in line:
                    key, val = line.split(":", 1)
                    frontmatter[key.strip()] = val.strip()
    title = frontmatter.get("title", os.path.basename(filepath).replace(".md", ""))
    slug = frontmatter.get("slug", slugify(title))
    date = frontmatter.get("date", datetime.now().strftime("%Y-%m-%d"))
    update_date = frontmatter.get("update_date", "")
    category = frontmatter.get("category", "tuijian")
    tags_raw = frontmatter.get("tags", "")
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
    image = frontmatter.get("image", "")
    excerpt = frontmatter.get("excerpt", "")
    priority = int(frontmatter.get("priority", "0"))
    html_content = markdown.markdown(body, extensions=["extra", "codehilite", "toc", "nl2br"])
    if not excerpt:
        first_p = re.search(r"<p>(.*?)</p>", html_content, re.DOTALL)
        if first_p:
            excerpt = re.sub(r"<[^>]+>", "", first_p.group(1)).strip()
            excerpt = excerpt[:120] + "..." if len(excerpt) > 120 else excerpt
    if not image and os.path.exists(SOURCE_DIR / "images" / f"{slug}.jpg"):
        image = f"source/images/{slug}.jpg"
    category_name = CAT_MAP.get(category, category)
    return {
        "title": title, "slug": slug, "date": date, "update_date": update_date,
        "category": category, "category_name": category_name, "tags": tags,
        "image": image, "excerpt": excerpt, "content": html_content, "priority": priority,
    }


def load_articles():
    articles_dir = SOURCE_DIR / "articles"
    articles = []
    if not articles_dir.exists():
        return articles
    for md_file in sorted(articles_dir.glob("*.md"), reverse=True):
        try:
            articles.append(parse_markdown_article(md_file))
        except Exception as e:
            print(f"  Error loading {md_file.name}: {e}")
    articles.sort(key=lambda a: a["date"], reverse=True)
    return articles


def group_by_category(articles):
    groups = {}
    for cat in CONFIG["categories"]:
        groups[cat["slug"]] = []
    for a in articles:
        if a["category"] in groups:
            groups[a["category"]].append(a)
    return groups


def group_by_tag(articles):
    groups = {}
    for a in articles:
        for tag in a["tags"]:
            groups.setdefault(tag, []).append(a)
    return groups


def get_related(article, all_articles, max_n=4):
    related = [a for a in all_articles if a["slug"] != article["slug"] and a["category"] == article["category"]]
    return related[:max_n]


def render(template_name, **kwargs):
    """Render a template with config always available."""
    tpl = env.get_template(template_name)
    ctx = dict(config=CONFIG, **kwargs)
    return tpl.render(**ctx)


def build_static_pages():
    pages = [
        ("about.html", "about.html"),
        ("privacy.html", "privacy.html"),
    ]
    for template_name, out_name in pages:
        html = render(template_name, root_path=".")
        with open(OUTPUT_DIR / out_name, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  Page: {out_name}")
    # search.html
    html = render("search.html", root_path=".", articles=[], query="")
    with open(OUTPUT_DIR / "search.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("  Page: search.html")


def build_sitemap(articles):
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    lines.append(f"  <url>\n    <loc>{CONFIG['site_url']}/index.html</loc>\n    <changefreq>daily</changefreq>\n    <priority>1.0</priority>\n  </url>")
    for cat in CONFIG["categories"]:
        lines.append(f"  <url>\n    <loc>{CONFIG['site_url']}/category/{cat['slug']}/index.html</loc>\n    <changefreq>weekly</changefreq>\n    <priority>0.8</priority>\n  </url>")
    for a in articles:
        lines.append(f"  <url>\n    <loc>{CONFIG['site_url']}/article/{a['slug']}/index.html</loc>\n    <lastmod>{a['update_date'] or a['date']}</lastmod>\n    <changefreq>monthly</changefreq>\n    <priority>0.6</priority>\n  </url>")
    for page in ["about.html", "privacy.html", "search.html"]:
        lines.append(f"  <url>\n    <loc>{CONFIG['site_url']}/{page}</loc>\n    <priority>0.4</priority>\n  </url>")
    lines.append("</urlset>")
    with open(OUTPUT_DIR / "sitemap.xml", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("  Sitemap: sitemap.xml")


def generate_site():
    print("=" * 50)
    print("  流量卡优选 - 静态站点生成")
    print("=" * 50)
    assets_dir = OUTPUT_DIR / "assets"
    for item in OUTPUT_DIR.iterdir():
        if item.name != "assets":
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()

    print("\n[1/5] Loading articles...")
    articles = load_articles()
    print(f"  Total: {len(articles)} articles")

    print("\n[2/5] Copying assets...")
    source_images = SOURCE_DIR / "images"
    output_images = OUTPUT_DIR / "source" / "images"
    if source_images.exists():
        output_images.mkdir(parents=True, exist_ok=True)
        for img in source_images.glob("*"):
            if img.suffix.lower() in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
                shutil.copy2(img, output_images / img.name)

    print("\n[3/5] Building pages...")
    build_static_pages()

    print("  Building: index.html")
    html = render("index.html", root_path=".", articles=articles)
    with open(OUTPUT_DIR / "index.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("\n[4/5] Building articles...")
    for i, article in enumerate(articles):
        prev_article = articles[i - 1] if i > 0 else None
        next_article = articles[i + 1] if i < len(articles) - 1 else None
        related = get_related(article, articles)
        html = render("article.html", root_path="../..", article=article,
                      prev_article=prev_article, next_article=next_article, related_articles=related)
        article_dir = OUTPUT_DIR / "article" / article["slug"]
        article_dir.mkdir(parents=True, exist_ok=True)
        with open(article_dir / "index.html", "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  Article: {article['title']}")

    print("  Building categories...")
    for cat_slug, cat_articles in group_by_category(articles).items():
        cat_info = next((c for c in CONFIG["categories"] if c["slug"] == cat_slug), None)
        if cat_info and cat_articles:
            html = render("category.html", root_path="../..", cat=cat_info, articles=cat_articles)
            cat_dir = OUTPUT_DIR / "category" / cat_slug
            cat_dir.mkdir(parents=True, exist_ok=True)
            with open(cat_dir / "index.html", "w", encoding="utf-8") as f:
                f.write(html)
            print(f"  Category: {cat_info['name']} ({len(cat_articles)} articles)")

    print("  Building tags...")
    for tag, tag_articles in group_by_tag(articles).items():
        html = render("tag.html", root_path="../..", tag=tag, articles=tag_articles)
        tag_dir = OUTPUT_DIR / "tag" / tag
        tag_dir.mkdir(parents=True, exist_ok=True)
        with open(tag_dir / "index.html", "w", encoding="utf-8") as f:
            f.write(html)

    print("\n[5/5] Generating sitemap...")
    build_sitemap(articles)

    print("\n" + "=" * 50)
    print("  Done! Site generated in output/")
    print("=" * 50)


if __name__ == "__main__":
    generate_site()
