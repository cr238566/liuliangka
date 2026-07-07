#!/usr/bin/env python3
"""
流量卡优选 - 后台管理系统
运行: python admin/app.py
然后浏览器访问 http://127.0.0.1:5000
"""


import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from functools import wraps

import markdown
from flask import Flask, render_template, request, redirect, session, url_for, jsonify

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
SOURCE_DIR = BASE_DIR / "source"
ARTICLES_DIR = SOURCE_DIR / "articles"
IMAGES_DIR = SOURCE_DIR / "images"
CONFIG_PATH = SOURCE_DIR / "config.json"
OUTPUT_DIR = BASE_DIR / "output"
GENERATOR = BASE_DIR / "generate.py"

# Default admin password
ADMIN_PASSWORD = "admin123"

app = Flask(__name__)
app.secret_key = "liuliangka-admin-secret-key-2026"


# ===== Auth decorator =====
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def load_articles_meta():
    """Load metadata from all markdown articles."""
    articles = []
    if not ARTICLES_DIR.exists():
        return articles
    for md_file in sorted(ARTICLES_DIR.glob("*.md"), reverse=True):
        content = md_file.read_text(encoding="utf-8")
        fm = {}
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                for line in parts[1].strip().split("\n"):
                    if ":" in line:
                        k, v = line.split(":", 1)
                        fm[k.strip()] = v.strip()
        articles.append({
            "filename": md_file.name,
            "title": fm.get("title", md_file.stem),
            "date": fm.get("date", ""),
            "category": fm.get("category", "tuijian"),
            "slug": fm.get("slug", ""),
            "tags": fm.get("tags", ""),
            "image": fm.get("image", ""),
        })
    return articles


# ===== Routes =====

@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        pw = request.form.get("password", "")
        if pw == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        else:
            error = "密码错误"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
    config = load_config()
    articles = load_articles_meta()
    cat_counts = {}
    for a in articles:
        cat = a["category"]
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    return render_template("dashboard.html",
                           config=config,
                           article_count=len(articles),
                           cat_counts=cat_counts,
                           categories=config["categories"])


@app.route("/articles")
@login_required
def article_list():
    articles = load_articles_meta()
    config = load_config()
    cat_map = {c["slug"]: c["name"] for c in config["categories"]}
    return render_template("articles.html", articles=articles, cat_map=cat_map)


@app.route("/articles/new", methods=["GET", "POST"])
@login_required
def article_new():
    config = load_config()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            return "标题不能为空", 400
        category = request.form.get("category", "tuijian")
        tags = request.form.get("tags", "").strip()
        excerpt = request.form.get("excerpt", "").strip()
        image = request.form.get("image", "").strip()
        priority = request.form.get("priority", "0")
        content = request.form.get("content", "")
        date = datetime.now().strftime("%Y-%m-%d")

        # Generate slug
        slug = request.form.get("slug", "").strip()
        if not slug:
            slug = re.sub(r"[^\w\s-]", "", title.lower())
            slug = re.sub(r"[\s_]+", "-", slug).strip("-")
            slug = re.sub(r"-+", "-", slug)

        md = (
            f"---\n"
            f'title: "{title}"\n'
            f"slug: {slug}\n"
            f"date: {date}\n"
            f"category: {category}\n"
            f"tags: {tags}\n"
            f"priority: {priority}\n"
        )
        if image:
            md += f"image: {image}\n"
        if excerpt:
            md += f'excerpt: "{excerpt}"\n'
        md += f"---\n\n{content}"

        filename = f"{date}-{slug}.md"
        (ARTICLES_DIR / filename).write_text(md, encoding="utf-8")
        return redirect(url_for("article_list"))

    return render_template("article_edit.html", config=config, article=None,
                           cats=config["categories"])


@app.route("/articles/edit/<filename>", methods=["GET", "POST"])
@login_required
def article_edit(filename):
    config = load_config()
    filepath = ARTICLES_DIR / filename
    if not filepath.exists():
        return "文章不存在", 404

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            return "标题不能为空", 400
        category = request.form.get("category", "tuijian")
        tags = request.form.get("tags", "").strip()
        excerpt = request.form.get("excerpt", "").strip()
        image = request.form.get("image", "").strip()
        priority = request.form.get("priority", "0")
        content = request.form.get("content", "")
        date = request.form.get("date", datetime.now().strftime("%Y-%m-%d"))
        slug = request.form.get("slug", "").strip()
        if not slug:
            slug = re.sub(r"[^\w\s-]", "", title.lower())
            slug = re.sub(r"[\s_]+", "-", slug).strip("-")
            slug = re.sub(r"-+", "-", slug)

        md = (
            f"---\n"
            f'title: "{title}"\n'
            f"slug: {slug}\n"
            f"date: {date}\n"
            f"category: {category}\n"
            f"tags: {tags}\n"
            f"priority: {priority}\n"
        )
        if image:
            md += f"image: {image}\n"
        if excerpt:
            md += f'excerpt: "{excerpt}"\n'
        md += f"---\n\n{content}"

        # If filename changed, rename file
        new_filename = f"{date}-{slug}.md"
        if new_filename != filename:
            old_path = filepath
            new_path = ARTICLES_DIR / new_filename
            # Remove old file
            old_path.unlink()
            new_path.write_text(md, encoding="utf-8")
        else:
            filepath.write_text(md, encoding="utf-8")

        return redirect(url_for("article_list"))

    # Load existing article
    raw = filepath.read_text(encoding="utf-8")
    fm = {}
    body = raw
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].strip().split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    fm[k.strip()] = v.strip()
            body = parts[2].strip()

    article = {
        "filename": filename,
        "title": fm.get("title", ""),
        "slug": fm.get("slug", ""),
        "date": fm.get("date", ""),
        "category": fm.get("category", "tuijian"),
        "tags": fm.get("tags", ""),
        "priority": fm.get("priority", "0"),
        "image": fm.get("image", ""),
        "excerpt": fm.get("excerpt", ""),
        "content": body,
    }
    return render_template("article_edit.html", config=config, article=article,
                           cats=config["categories"])


@app.route("/articles/delete/<filename>", methods=["POST"])
@login_required
def article_delete(filename):
    filepath = ARTICLES_DIR / filename
    if filepath.exists():
        filepath.unlink()
    return redirect(url_for("article_list"))


@app.route("/preview", methods=["POST"])
@login_required
def preview_markdown():
    content = request.form.get("content", "")
    html = markdown.markdown(content, extensions=["extra", "codehilite", "toc", "nl2br"])
    return html


@app.route("/images")
@login_required
def image_list():
    images = []
    if IMAGES_DIR.exists():
        for img in sorted(IMAGES_DIR.glob("*")):
            if img.suffix.lower() in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
                images.append(img.name)
    return render_template("images.html", images=images)


@app.route("/images/upload", methods=["POST"])
@login_required
def image_upload():
    if "file" not in request.files:
        return "没有选择文件", 400
    f = request.files["file"]
    if f.filename == "":
        return "文件名为空", 400
    if not IMAGES_DIR.exists():
        IMAGES_DIR.mkdir(parents=True)
    f.save(str(IMAGES_DIR / f.filename))
    return redirect(url_for("image_list"))


@app.route("/images/delete/<name>", methods=["POST"])
@login_required
def image_delete(name):
    img_path = IMAGES_DIR / name
    if img_path.exists():
        img_path.unlink()
    return redirect(url_for("image_list"))


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    config = load_config()
    if request.method == "POST":
        config["site_name"] = request.form.get("site_name", config["site_name"])
        config["site_url"] = request.form.get("site_url", config["site_url"])
        config["site_description"] = request.form.get("site_description", config["site_description"])
        config["site_keywords"] = request.form.get("site_keywords", config["site_keywords"])
        config["author"] = request.form.get("author", config["author"])
        config["beian"] = request.form.get("beian", config.get("beian", ""))
        config["ga_id"] = request.form.get("ga_id", config.get("ga_id", ""))
        save_config(config)
        return redirect(url_for("settings"))

    return render_template("settings.html", config=config)


@app.route("/generate", methods=["POST"])
@login_required
def generate_site():
    try:
        result = subprocess.run(
            [sys.executable, str(GENERATOR)],
            capture_output=True, text=True, timeout=30,
            cwd=str(BASE_DIR),
        )
        return jsonify({
            "success": result.returncode == 0,
            "output": result.stdout + result.stderr,
        })
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "output": "生成超时"})
    except Exception as e:
        return jsonify({"success": False, "output": str(e)})



@app.route("/source/images/<name>")
@login_required
def serve_image(name):
    from flask import send_from_directory
    return send_from_directory(str(IMAGES_DIR), name)

if __name__ == "__main__":
    print("=" * 50)
    print("  流量卡优选 - 后台管理系统")
    print("  URL: http://127.0.0.1:5000")
    print("  密码: admin123")
    print("=" * 50)
    app.run(host="127.0.0.1", port=5000, debug=True)



