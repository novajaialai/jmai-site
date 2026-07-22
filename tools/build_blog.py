#!/usr/bin/env python3
"""
build_blog.py — static blog generator for jacobdart.com

Source of truth:  content/posts/*.md   (Markdown + YAML frontmatter)
Generated output: blog/index.html, blog/<slug>/index.html, feed.xml, sitemap.xml

This file is PRIVATE (lives under tools/, excluded from the public deploy like
pricing.py). Only the generated artifacts get mirrored to the public repo.

Usage:
  python3 tools/build_blog.py            # build the blog from content/posts/
  python3 tools/build_blog.py --drafts   # also include posts with draft: true
  python3 tools/build_blog.py --new "My Post Title"   # scaffold a new draft post

Dependencies (system python is fine):  pip install markdown pyyaml
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import re
import sys
from pathlib import Path

try:
    import markdown
    import yaml
except ImportError as e:  # pragma: no cover
    sys.exit(f"Missing dependency ({e.name}). Run:  pip install markdown pyyaml")

# ---- config ----------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = ROOT / "content" / "posts"
OUT_DIR = ROOT / "blog"
BASE_URL = "https://jacobdart.com"
OG_IMAGE = f"{BASE_URL}/assets/img/og-image.png"
AUTHOR = "Jacob Dart"
BRAND = "J&M AI Services"
BLOG_TITLE = "Writing"
BLOG_TAGLINE = ("Field notes on turning owner-operator businesses into calm, "
                "compounding systems — automation, AI, and the operating-system mindset.")

MD_EXTENSIONS = ["extra", "sane_lists", "smarty", "toc"]

# ---- shared chrome (nav links root-relative so they work from /blog/...) ----
HEADER = """<header class="site-header">
  <div class="wrap nav">
    <a class="brand" href="/" aria-label="Jacob Dart — J&amp;M AI Services, home">
      <img class="mark" src="/assets/img/mark.svg" alt="" width="30" height="30">
      Jacob Dart
      <span class="sub">J&amp;M AI Services</span>
    </a>
    <nav class="nav-links" aria-label="Primary">
      <a href="/#problem">The problem</a>
      <a href="/#how">How it works</a>
      <a href="/#pricing">Pricing</a>
      <a href="/about/">About</a>
      <a href="/blog/" aria-current="page">Writing</a>
      <a href="/#faq">FAQ</a>
    </nav>
    <div class="nav-cta">
      <a class="btn btn-primary" href="https://calendly.com/jacobdart" target="_blank" rel="noopener">Book a call <span class="arr">&rarr;</span></a>
    </div>
  </div>
</header>"""

FOOTER = """<footer class="site-footer">
  <div class="wrap">
    <div class="foot-grid">
      <div>
        <a class="brand" href="/"><img class="mark" src="/assets/img/mark-light.svg" alt="" width="30" height="30"> Jacob Dart <span class="sub">J&amp;M AI Services</span></a>
        <p>I turn owner-operators' repetitive work into calm, compounding systems they own — built for you, until it runs without you.</p>
      </div>
      <div class="foot-col">
        <h4>Work with me</h4>
        <a href="/#pricing">The Assessment — $999</a>
        <a href="/#pricing">Custom builds</a>
        <a href="/#pricing">The Concierge</a>
        <a href="https://calendly.com/jacobdart" target="_blank" rel="noopener">Book a call</a>
      </div>
      <div class="foot-col">
        <h4>Company</h4>
        <a href="/about/">About Jacob</a>
        <a href="/#how">How it works</a>
        <a href="/blog/">Writing</a>
        <a href="mailto:yakobdart@gmail.com">yakobdart@gmail.com</a>
      </div>
    </div>
    <div class="foot-bot">
      <span>&copy; <span id="yr">2026</span> J&amp;M AI Services LLC</span>
      <span class="tag">Calm systems, compounding.</span>
    </div>
  </div>
</footer>
<script>document.getElementById('yr').textContent = new Date().getFullYear();</script>"""

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{TITLE}}</title>
<meta name="description" content="{{DESC}}">
<link rel="canonical" href="{{CANON}}">
<meta name="theme-color" content="#1c3c74">
{{OG}}
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="alternate" type="application/rss+xml" title="Jacob Dart — Writing" href="/feed.xml">
<link rel="preload" href="/assets/fonts/SourceSerif4-Semibold.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/assets/fonts/RedHatText-Regular.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/assets/site.css">
<link rel="stylesheet" href="/assets/blog.css">
{{JSONLD}}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
{{HEADER}}
<main id="main">
{{CONTENT}}
</main>
{{FOOTER}}
</body>
</html>
"""


# ---- helpers ---------------------------------------------------------------
def render(template: str, **kw: str) -> str:
    out = template
    for k, v in kw.items():
        out = out.replace("{{" + k + "}}", v)
    return out


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def to_date(v) -> dt.date:
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    return dt.date.fromisoformat(str(v).strip())


def human_date(d: dt.date) -> str:
    return d.strftime("%B %-d, %Y")


def rfc822(d: dt.date) -> str:
    return dt.datetime(d.year, d.month, d.day).strftime("%a, %d %b %Y %H:%M:%S +0000")


def reading_time(text: str) -> int:
    words = len(re.sub(r"<[^>]+>", " ", text).split())
    return max(1, round(words / 200))


def slugify(s: str) -> str:
    s = re.sub(r"[^\w\s-]", "", s.lower()).strip()
    return re.sub(r"[\s_]+", "-", s) or "post"


# ---- parsing ---------------------------------------------------------------
FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.S)


def parse_post(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    m = FM_RE.match(raw)
    if not m:
        raise ValueError(f"{path.name}: missing YAML frontmatter (--- ... ---)")
    meta = yaml.safe_load(m.group(1)) or {}
    body_md = m.group(2).strip()

    md = markdown.Markdown(extensions=MD_EXTENSIONS, output_format="html5")
    body_html = md.convert(body_md)

    title = str(meta.get("title") or path.stem).strip()
    date = to_date(meta.get("date") or dt.date.today())
    slug = str(meta.get("slug") or path.stem).strip()
    desc = str(meta.get("description") or "").strip()
    if not desc:  # derive from first paragraph
        p = re.search(r"<p>(.*?)</p>", body_html, re.S)
        desc = re.sub(r"<[^>]+>", "", p.group(1)).strip() if p else title
        desc = re.sub(r"\s+", " ", desc)[:180]
    tags = meta.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    return {
        "title": title,
        "date": date,
        "slug": slug,
        "desc": desc,
        "tags": tags,
        "draft": bool(meta.get("draft", False)),
        "body": body_html,
        "url": f"/blog/{slug}/",
        "reading_time": reading_time(body_html),
        "source": path.name,
    }


# ---- rendering -------------------------------------------------------------
def og_block(kind: str, title: str, desc: str, url: str, image: str = OG_IMAGE,
             published: str = "") -> str:
    bits = [
        f'<meta property="og:type" content="{kind}">',
        f'<meta property="og:url" content="{url}">',
        f'<meta property="og:title" content="{esc(title)}">',
        f'<meta property="og:description" content="{esc(desc)}">',
        f'<meta property="og:image" content="{image}">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        f'<meta property="og:site_name" content="{BRAND}">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{esc(title)}">',
        f'<meta name="twitter:description" content="{esc(desc)}">',
        f'<meta name="twitter:image" content="{image}">',
    ]
    if kind == "article" and published:
        bits.append(f'<meta property="article:published_time" content="{published}">')
        bits.append(f'<meta property="article:author" content="{AUTHOR}">')
    return "\n".join(bits)


def post_jsonld(post: dict) -> str:
    iso = post["date"].isoformat()
    url = f"{BASE_URL}{post['url']}"
    data = (
        '<script type="application/ld+json">\n'
        "{\n"
        '  "@context":"https://schema.org",\n'
        '  "@type":"BlogPosting",\n'
        f'  "headline":{yaml_json(post["title"])},\n'
        f'  "description":{yaml_json(post["desc"])},\n'
        f'  "datePublished":"{iso}",\n'
        f'  "dateModified":"{iso}",\n'
        f'  "author":{{"@type":"Person","name":"{AUTHOR}","url":"{BASE_URL}/about/"}},\n'
        f'  "publisher":{{"@type":"Organization","name":"{BRAND}","url":"{BASE_URL}/"}},\n'
        f'  "mainEntityOfPage":{{"@type":"WebPage","@id":"{url}"}},\n'
        f'  "image":"{OG_IMAGE}",\n'
        f'  "url":"{url}"\n'
        "}\n"
        "</script>"
    )
    return data


def yaml_json(s: str) -> str:
    """JSON-string-encode a value (handles quotes/unicode safely)."""
    import json
    return json.dumps(s, ensure_ascii=False)


def render_post(post: dict) -> str:
    tags_html = ""
    if post["tags"]:
        chips = "".join(f'<span class="tag-chip">{esc(t)}</span>' for t in post["tags"])
        tags_html = f'<div class="tags" style="margin-top:18px">{chips}</div>'

    dek = f'<p class="dek">{esc(post["desc"])}</p>' if post["desc"] else ""

    content = f"""  <article class="article">
    <div class="wrap">
      <div class="article-head">
        <a class="back-link" href="/blog/"><span class="arr">&larr;</span> All writing</a>
        <div class="post-meta">
          <time datetime="{post['date'].isoformat()}">{human_date(post['date'])}</time>
          <span class="sep">&middot;</span><span>{post['reading_time']} min read</span>
        </div>
        <h1>{esc(post['title'])}</h1>
        {dek}
      </div>
      <div class="prose">
{indent(post['body'], 8)}
      </div>
      {tags_html}
      <aside class="post-cta">
        <p class="eyebrow">Work with me</p>
        <h3>Want this running in your business?</h3>
        <p class="muted">Every engagement starts with a $999 assessment — we find your highest-leverage automations and a plan to start.</p>
        <a class="btn btn-primary" href="https://calendly.com/jacobdart" target="_blank" rel="noopener">Book the assessment <span class="arr">&rarr;</span></a>
      </aside>
    </div>
  </article>"""

    return render(
        PAGE,
        TITLE=f"{esc(post['title'])} — {AUTHOR}",
        DESC=esc(post["desc"]),
        CANON=f"{BASE_URL}{post['url']}",
        OG=og_block("article", post["title"], post["desc"], f"{BASE_URL}{post['url']}",
                    published=post["date"].isoformat()),
        JSONLD=post_jsonld(post),
        HEADER=HEADER,
        FOOTER=FOOTER,
        CONTENT=content,
    )


def render_index(posts: list[dict]) -> str:
    items = []
    for p in posts:
        chips = ""
        if p["tags"]:
            chips = '<div class="tags">' + "".join(
                f'<span class="tag-chip">{esc(t)}</span>' for t in p["tags"]) + "</div>"
        items.append(f"""        <a class="post-item" href="{p['url']}">
          <div class="post-meta">
            <time datetime="{p['date'].isoformat()}">{human_date(p['date'])}</time>
            <span class="sep">&middot;</span><span>{p['reading_time']} min read</span>
          </div>
          <h2 class="post-title">{esc(p['title'])}</h2>
          <p class="post-dek">{esc(p['desc'])}</p>
          {chips}
          <span class="post-more">Read <span class="arr">&rarr;</span></span>
        </a>""")
    listing = "\n".join(items) if items else (
        '<p class="muted" style="padding:32px 0">No posts yet — check back soon.</p>')

    content = f"""  <section class="blog-head">
    <div class="wrap">
      <p class="eyebrow">{BLOG_TITLE}</p>
      <h1>Notes from node zero.</h1>
      <p class="lead">{BLOG_TAGLINE}</p>
    </div>
  </section>
  <section class="section plain" style="padding-top:0">
    <div class="wrap">
      <div class="post-list">
{listing}
      </div>
    </div>
  </section>"""

    jsonld = (
        '<script type="application/ld+json">\n'
        "{\n"
        '  "@context":"https://schema.org",\n'
        '  "@type":"Blog",\n'
        f'  "name":"{AUTHOR} — Writing",\n'
        f'  "url":"{BASE_URL}/blog/",\n'
        f'  "description":{yaml_json(BLOG_TAGLINE)},\n'
        f'  "publisher":{{"@type":"Organization","name":"{BRAND}"}}\n'
        "}\n"
        "</script>"
    )

    return render(
        PAGE,
        TITLE=f"Writing — {AUTHOR} | {BRAND}",
        DESC=esc(BLOG_TAGLINE),
        CANON=f"{BASE_URL}/blog/",
        OG=og_block("website", f"Writing — {AUTHOR}", BLOG_TAGLINE, f"{BASE_URL}/blog/"),
        JSONLD=jsonld,
        HEADER=HEADER,
        FOOTER=FOOTER,
        CONTENT=content,
    )


def indent(text: str, n: int) -> str:
    pad = " " * n
    return "\n".join(pad + line if line else line for line in text.splitlines())


# ---- feed + sitemap --------------------------------------------------------
def render_feed(posts: list[dict]) -> str:
    items = []
    for p in posts:
        link = f"{BASE_URL}{p['url']}"
        items.append(f"""    <item>
      <title>{esc(p['title'])}</title>
      <link>{link}</link>
      <guid isPermaLink="true">{link}</guid>
      <pubDate>{rfc822(p['date'])}</pubDate>
      <description>{esc(p['desc'])}</description>
    </item>""")
    built = rfc822(dt.date.today())
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{AUTHOR} — Writing</title>
    <link>{BASE_URL}/blog/</link>
    <atom:link href="{BASE_URL}/feed.xml" rel="self" type="application/rss+xml"/>
    <description>{esc(BLOG_TAGLINE)}</description>
    <language>en-us</language>
    <lastBuildDate>{built}</lastBuildDate>
{chr(10).join(items)}
  </channel>
</rss>
"""


def update_sitemap(posts: list[dict]) -> None:
    """Idempotently refresh the blog block in sitemap.xml between markers."""
    sm = ROOT / "sitemap.xml"
    text = sm.read_text(encoding="utf-8")
    today = dt.date.today().isoformat()

    urls = [f"""  <url>
    <loc>{BASE_URL}/blog/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.7</priority>
  </url>"""]
    for p in posts:
        urls.append(f"""  <url>
    <loc>{BASE_URL}{p['url']}</loc>
    <lastmod>{p['date'].isoformat()}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.6</priority>
  </url>""")
    block = "  <!-- BLOG:START (generated by tools/build_blog.py — do not edit) -->\n" \
            + "\n".join(urls) + "\n  <!-- BLOG:END -->"

    text = re.sub(r"  <!-- BLOG:START.*?<!-- BLOG:END -->\n?", "", text, flags=re.S)
    text = text.replace("</urlset>", block + "\n</urlset>")
    sm.write_text(text, encoding="utf-8")


# ---- scaffolder ------------------------------------------------------------
def scaffold(title: str) -> None:
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    slug = slugify(title)
    path = POSTS_DIR / f"{slug}.md"
    if path.exists():
        sys.exit(f"Refusing to overwrite existing {path.relative_to(ROOT)}")
    today = dt.date.today().isoformat()
    path.write_text(
        f'---\ntitle: "{title}"\ndate: {today}\ndescription: ""\ntags: []\ndraft: true\n---\n\n'
        "Write your post here in Markdown.\n",
        encoding="utf-8",
    )
    print(f"Created {path.relative_to(ROOT)}  (draft). Edit it, set draft: false, then rebuild.")


# ---- main ------------------------------------------------------------------
def build(include_drafts: bool) -> None:
    if not POSTS_DIR.exists():
        sys.exit(f"No posts dir at {POSTS_DIR.relative_to(ROOT)} — create it and add *.md")
    posts = [parse_post(p) for p in sorted(POSTS_DIR.glob("*.md"))]
    if not include_drafts:
        posts = [p for p in posts if not p["draft"]]
    posts.sort(key=lambda p: p["date"], reverse=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "index.html").write_text(render_index(posts), encoding="utf-8")
    for p in posts:
        d = OUT_DIR / p["slug"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(render_post(p), encoding="utf-8")

    (ROOT / "feed.xml").write_text(render_feed(posts), encoding="utf-8")
    update_sitemap(posts)
    # keep GitHub Pages from running Jekyll over generated output
    (ROOT / ".nojekyll").touch()

    print(f"Built {len(posts)} post(s) -> {OUT_DIR.relative_to(ROOT)}/")
    for p in posts:
        print(f"  - {p['date']}  {p['url']}  ({p['reading_time']} min)")
    print("Generated: blog/index.html, blog/<slug>/index.html, feed.xml, sitemap.xml, .nojekyll")


def main() -> None:
    ap = argparse.ArgumentParser(description="Build the jacobdart.com blog.")
    ap.add_argument("--drafts", action="store_true", help="include draft posts")
    ap.add_argument("--new", metavar="TITLE", help="scaffold a new draft post and exit")
    args = ap.parse_args()
    if args.new:
        scaffold(args.new)
        return
    build(include_drafts=args.drafts)


if __name__ == "__main__":
    main()
