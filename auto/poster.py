#!/usr/bin/env python3
"""
流量卡 - 每日自动发布文章
用法: 
  python auto/poster.py              # 发1篇
  python auto/poster.py --count 2     # 发2篇
  python auto/poster.py --delay       # 随机延时0-30分（用于定时任务）
"""

import argparse
import json
import os
import random
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
from auto.topics import TOPICS, ARTICLE_TEMPLATES

ARTICLES_DIR = BASE_DIR / "source" / "articles"
IMAGES_DIR = BASE_DIR / "source" / "images"
GENERATOR = BASE_DIR / "generate.py"

CATEGORY_NAMES = {
    "tuijian": "流量卡推荐", "duibi": "套餐对比",
    "jiqiao": "使用技巧", "zixun": "行业资讯", "huodong": "优惠活动",
}
COLORS = [
    (30, 64, 175), (5, 150, 105), (180, 83, 9),
    (147, 51, 234), (220, 38, 38), (234, 88, 12),
    (13, 148, 136), (79, 70, 229),
]


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    slug = text.strip("-")
    if not slug:
        slug = "auto-" + datetime.now().strftime("%Y%m%d%H%M%S")
    return slug


def pick_topic():
    topic = random.choice(TOPICS)
    tpl = topic["title_tpl"]
    fill_opts = topic.get("fill_opts", {})
    args = []
    for key in sorted(fill_opts.keys()):
        opts = fill_opts[key]
        args.append(random.choice(opts))
    title = tpl % tuple(args) if args else tpl
    return topic, title


def load_existing_titles():
    titles = set()
    if ARTICLES_DIR.exists():
        for md_file in ARTICLES_DIR.glob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    for line in parts[1].strip().split("\n"):
                        if ":" in line:
                            k, v = line.split(":", 1)
                            if k.strip() == "title":
                                titles.add(v.strip().strip("\""))
    return titles


def generate_article(topic, title):
    today = datetime.now().strftime("%Y-%m-%d")
    slug = slugify(title)
    template_id = topic["template"]
    category = topic["category"]
    tags = topic.get("tags", category)
    body_tpl = ARTICLE_TEMPLATES.get(template_id, "# {title}\n\n正文内容\n")
    body = body_tpl.format(title=title)
    first_line = body.strip().split("\n")[0]
    excerpt = first_line.replace("# ", "")[:100] if first_line.startswith("#") else title[:100]
    image_path = "/source/images/auto-{}.jpg".format(slug)
    md = (
        "---\n"
        'title: "{}"\n'
        "slug: {}\n"
        "date: {}\n"
        "category: {}\n"
        "tags: {}\n"
        "priority: 0\n"
        "image: {}\n"
        'excerpt: "{}"\n'
        "---\n\n"
        "{}"
    ).format(title, slug, today, category, tags, image_path, excerpt, body)
    return md, slug, category


def generate_image(slug, title, category):
    try:
        from PIL import Image, ImageDraw, ImageFont
        color = random.choice(COLORS)
        width, height = 800, 450
        img = Image.new("RGB", (width, height), color)
        draw = ImageDraw.Draw(img)
        for y in range(height):
            r = int(color[0] * (1 - y / height * 0.3))
            g = int(color[1] * (1 - y / height * 0.3))
            b = int(color[2] * (1 - y / height * 0.3))
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        for i in range(5):
            cx = width * 0.2 + i * width * 0.15
            cy = height * 0.3
            r_size = 60 + i * 15
            draw.ellipse([cx - r_size, cy - r_size, cx + r_size, cy + r_size],
                         fill=(color[0], color[1], color[2]))
        try:
            font_large = ImageFont.truetype("arial.ttf", 42)
            font_small = ImageFont.truetype("arial.ttf", 18)
        except Exception:
            font_large = ImageFont.load_default()
            font_small = font_large
        display_title = title if len(title) < 20 else title[:18] + ".."
        draw.text((width // 2, height // 2 - 30), display_title, fill="white",
                  font=font_large, anchor="mm")
        cat_name = CATEGORY_NAMES.get(category, category)
        draw.text((width // 2, height // 2 + 30), cat_name,
                  fill=(255, 255, 255, 160), font=font_small, anchor="mm")
        draw.line([(width // 2 - 80, height // 2 + 55),
                   (width // 2 + 80, height // 2 + 55)],
                  fill=(255, 255, 255, 80), width=2)
        today = datetime.now().strftime("%Y-%m-%d")
        draw.text((width // 2, height // 2 + 75), today,
                  fill=(255, 255, 255, 100), font=font_small, anchor="mm")
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        img_path = IMAGES_DIR / "auto-{}.jpg".format(slug)
        img.save(str(img_path), quality=85)
        return True
    except ImportError:
        print("Pillow not installed, skipping image")
        return False
    except Exception as e:
        print("Image error: {}".format(e))
        return False


def run_generator():
    print("Regenerating site...")
    try:
        result = subprocess.run(
            [sys.executable, str(GENERATOR)],
            capture_output=True, text=True, timeout=60,
            cwd=str(BASE_DIR),
        )
        if result.returncode == 0:
            print("Site regenerated successfully!")
        else:
            print("Generator error: {}".format(result.stderr))
    except Exception as e:
        print("Generator failed: {}".format(e))


def main():
    parser = argparse.ArgumentParser(description="自动发布文章")
    parser.add_argument("--count", type=int, default=1, help="本次发布的文章数")
    parser.add_argument("--delay", action="store_true", help="随机延时0-30分")
    args = parser.parse_args()

    if args.delay:
        delay_sec = random.randint(0, 1800)
        print("随机延时 {} 秒 ({} 分钟)...".format(delay_sec, delay_sec // 60))
        time.sleep(delay_sec)

    print("=" * 50)
    print("  流量卡 - 自动文章发布")
    print("  时间: {}".format(datetime.now().strftime("%Y-%m-%d %H:%M")))
    print("  本次: {} 篇".format(args.count))
    print("=" * 50)

    existing = load_existing_titles()
    print("已有文章: {} 篇".format(len(existing)))

    posted = 0
    for i in range(args.count):
        title = None
        topic = None
        for attempt in range(50):
            t, ttl = pick_topic()
            if ttl not in existing:
                title = ttl
                topic = t
                break

        if title is None:
            print("话题池已用完！")
            break

        existing.add(title)
        print("\n[{}/{}] 选题: {}".format(i+1, args.count, title))
        print("  分类: {}".format(CATEGORY_NAMES.get(topic["category"], topic["category"])))

        md_content, slug, category = generate_article(topic, title)
        filename = "{}-{}.md".format(datetime.now().strftime("%Y-%m-%d"), slug)
        ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
        (ARTICLES_DIR / filename).write_text(md_content, encoding="utf-8")
        print("  文章已保存: {}".format(filename))

        print("  生成配图...")
        generate_image(slug, title, category)
        posted += 1

    if posted > 0:
        run_generator()
    else:
        print("没有新文章需要生成")

    print("\n" + "=" * 50)
    print("  完成！本次发布 {} 篇".format(posted))
    print("=" * 50)


if __name__ == "__main__":
    main()
