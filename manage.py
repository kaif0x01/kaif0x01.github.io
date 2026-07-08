#!/usr/bin/env python3
"""
manage.py — tiny content manager for the portfolio site.

No dependencies, pure Python 3 stdlib. Run from anywhere; it always
operates on the files next to this script.

Writeups come from two sources, merged into one section (newest first):
  • self-authored Markdown files in posts/*.md
  • posts mirrored from your Medium RSS feed

Commands:
  python3 manage.py new-writeup "Title"        # scaffold posts/<slug>.md
  python3 manage.py build                      # render Markdown + merge Medium (no network)
  python3 manage.py sync-medium                # refresh Medium cache, then build
  python3 manage.py list-writeups
  python3 manage.py add-writeup                # add a single external-link card
  python3 manage.py remove-writeup 2           # number from list-writeups
  python3 manage.py set-resume ~/Downloads/MyResume.pdf
  python3 manage.py serve                      # preview at http://localhost:8000
"""

import argparse
import html
import json
import re
import shutil
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
RESUME = ROOT / "assets" / "resume.pdf"
WRITEUPS_DIR = ROOT / "writeups"       # generated article pages
POSTS_DIR = ROOT / "posts"             # self-authored Markdown sources
MEDIUM_CACHE = ROOT / ".medium-cache.json"

FEED_URL = "https://kaif0x01.medium.com/feed"
CONTENT_NS = {"content": "http://purl.org/rss/1.0/modules/content/"}

START = "<!-- WRITEUPS:START (managed by manage.py — keep newest first) -->"
END = "<!-- WRITEUPS:END -->"

CARD_TEMPLATE = """\
        <a class="writeup reveal" href="{url}" target="_blank" rel="noopener">
          <div class="writeup-meta mono">
            {tags}
            <time datetime="{iso_date}">{display_date}</time>
          </div>
          <h4>{title}</h4>
          <p>{desc}</p>
          <span class="card-link mono">read more →</span>
        </a>"""

# Card that links to a self-hosted mirror page (relative, same tab).
LOCAL_CARD_TEMPLATE = """\
        <a class="writeup reveal" href="{url}">
          <div class="writeup-meta mono">
            {tags}
            <time datetime="{iso_date}">{display_date}</time>
          </div>
          <h4>{title}</h4>
          <p>{desc}</p>
          <span class="card-link mono">read writeup →</span>
        </a>"""

# Standalone mirror page. Uses relative ../../ paths so it works whether the
# site is hosted at the domain root or from a project subpath.
ARTICLE_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title} — Mohammad Kaif</title>
  <meta name="description" content="{desc}" />
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E%F0%9F%9B%A1%EF%B8%8F%3C/text%3E%3C/svg%3E" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="../../css/style.css" />
</head>
<body>
  <div class="bg-grid" aria-hidden="true"></div>
  <div class="bg-glow" aria-hidden="true"></div>

  <header class="nav-wrap">
    <nav class="nav container">
      <a href="../../index.html" class="logo mono"><span class="accent">~/</span>kaif0x01</a>
      <ul class="nav-links">
        <li><a href="../../index.html#writeups">← All writeups</a></li>
      </ul>
    </nav>
  </header>

  <main class="article container">
    <p class="mono kicker"><a href="../../index.html#writeups">$ cd ../writeups</a></p>
    <h1>{title}</h1>
    <div class="writeup-meta mono article-meta">
      {tags}
      <time datetime="{iso_date}">{display_date}</time>
    </div>
    <div class="article-body">
{body}
    </div>
    {source_html}
  </main>

  <footer class="footer">
    <p class="mono">
      <span class="dim">built with</span> ❤️ <span class="dim">·</span>
      <a href="https://x.com/_mkahmad" target="_blank" rel="noopener">@_mkahmad</a>
      <span class="dim">· © {year} Mohammad Kaif</span>
    </p>
  </footer>
</body>
</html>
"""

# Archive page listing every writeup. Lives at writeups/index.html, so it is
# one level deep: paths use ../ and card links use plain "<slug>/".
ARCHIVE_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Writeups — Mohammad Kaif</title>
  <meta name="description" content="Security research writeups by Mohammad Kaif — web, API and Android vulnerabilities." />
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E%F0%9F%9B%A1%EF%B8%8F%3C/text%3E%3C/svg%3E" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="../css/style.css" />
</head>
<body>
  <div class="bg-grid" aria-hidden="true"></div>
  <div class="bg-glow" aria-hidden="true"></div>

  <header class="nav-wrap">
    <nav class="nav container">
      <a href="../index.html" class="logo mono"><span class="accent">~/</span>kaif0x01</a>
      <ul class="nav-links">
        <li><a href="../index.html">← Home</a></li>
      </ul>
    </nav>
  </header>

  <main class="section container archive-main">
    <p class="mono kicker"><a href="../index.html">$ cd ~</a></p>
    <h1 class="archive-title">Writeups <span class="dim">/</span> <span class="accent">{count}</span></h1>
    <p class="archive-sub">Security research — web, API and Android vulnerabilities.</p>
    <div class="writeups-archive">
{cards}
    </div>
    <nav class="pager" aria-label="Writeups pagination" hidden></nav>
  </main>

  <footer class="footer">
    <p class="mono">
      <span class="dim">built with</span> ❤️ <span class="dim">·</span>
      <a href="https://x.com/_mkahmad" target="_blank" rel="noopener">@_mkahmad</a>
      <span class="dim">· © {year} Mohammad Kaif</span>
    </p>
  </footer>

  <script>
  (function () {
    var PAGE_SIZE = 6;
    var list = document.querySelector('.writeups-archive');
    var pager = document.querySelector('.pager');
    var cards = Array.prototype.slice.call(list.querySelectorAll('.writeup'));
    if (!pager || cards.length <= PAGE_SIZE) return;
    var pages = Math.ceil(cards.length / PAGE_SIZE);
    var current = 1;

    function button(label, page, opts) {
      opts = opts || {};
      var b = document.createElement('button');
      b.className = 'pager-btn' + (opts.active ? ' active' : '');
      b.textContent = label;
      if (opts.disabled) b.disabled = true;
      if (opts.active) b.setAttribute('aria-current', 'page');
      b.addEventListener('click', function () {
        current = page;
        render();
        list.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
      return b;
    }

    function render() {
      cards.forEach(function (card, i) {
        card.style.display = (Math.floor(i / PAGE_SIZE) + 1 === current) ? '' : 'none';
      });
      pager.innerHTML = '';
      pager.appendChild(button('‹ Prev', current - 1, { disabled: current === 1 }));
      for (var p = 1; p <= pages; p++) {
        pager.appendChild(button(String(p), p, { active: p === current }));
      }
      pager.appendChild(button('Next ›', current + 1, { disabled: current === pages }));
    }

    pager.hidden = false;
    render();
  })();
  </script>
</body>
</html>
"""

POST_SCAFFOLD = """\
---
title: {title}
date: {date}
tags: web, writeup
description: One-line summary shown on the card and in search results.
---

Write your writeup in **Markdown**. The first paragraphs become the excerpt.

## A heading

Some prose with a [link](https://example.com), **bold**, *italic* and
`inline code`.

- a bullet
- another bullet

```bash
# fenced code blocks are supported
curl https://example.com
```

![screenshot caption](https://your-image-host/path.png)

> Blockquotes work too.
"""


def die(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def read_index() -> str:
    if not INDEX.exists():
        die(f"{INDEX} not found")
    return INDEX.read_text(encoding="utf-8")


def split_sections(doc: str):
    """Return (before, managed_block, after) around the writeup markers."""
    try:
        before, rest = doc.split(START, 1)
        block, after = rest.split(END, 1)
    except ValueError:
        die("writeup markers not found in index.html — don't remove the "
            "WRITEUPS:START/END comments")
    return before, block, after


def parse_cards(block: str):
    return re.findall(r'^[ \t]*<a class="writeup reveal".*?</a>', block, re.S | re.M)


def card_summary(card_html: str):
    title = re.search(r"<h4>(.*?)</h4>", card_html, re.S)
    when = re.search(r"<time[^>]*>(.*?)</time>", card_html)
    url = re.search(r'href="([^"]+)"', card_html)
    return (
        html.unescape(title.group(1).strip()) if title else "(untitled)",
        when.group(1) if when else "?",
        url.group(1) if url else "?",
    )


def write_index(before: str, cards: list, after: str) -> None:
    block = "\n" + "\n".join(cards) + "\n        "
    INDEX.write_text(before + START + block + END + after, encoding="utf-8")


# ---------------- medium sync helpers ----------------

def slugify(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower())
    return text.strip("-")[:80] or "writeup"


def strip_tags(html_text: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", html_text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def excerpt(html_text: str, limit: int = 155) -> str:
    text = strip_tags(html_text)
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (portfolio manage.py)"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def parse_feed(raw: bytes) -> list:
    root = ET.fromstring(raw)
    channel = root.find("channel")
    if channel is None:
        die("not an RSS feed (no <channel> element)")
    entries = []
    for item in channel.findall("item"):
        title = html.unescape((item.findtext("title") or "Untitled").strip())
        link = (item.findtext("link") or "").split("?")[0]
        content_el = item.find("content:encoded", CONTENT_NS)
        body = content_el.text if content_el is not None and content_el.text else ""
        try:
            dt = parsedate_to_datetime(item.findtext("pubDate"))
        except (TypeError, ValueError):
            dt = datetime.now()
        tags = [c.text.strip() for c in item.findall("category")
                if c.text and c.text.strip()][:3]
        entries.append({
            "title": title, "link": link, "body": body, "dt": dt,
            "tags": tags, "slug": slugify(title),
        })
    return entries


def tag_html(tags: list) -> str:
    if not tags:
        tags = ["writeup"]
    return "".join(f'<span class="tag">{html.escape(t.lower())}</span>' for t in tags)


def render_article(rec: dict) -> None:
    page_dir = WRITEUPS_DIR / rec["slug"]
    page_dir.mkdir(parents=True, exist_ok=True)
    link = rec.get("link")
    if rec["source"] == "medium" and link:
        source_html = ('<p class="article-source mono">Originally published on '
                       f'<a href="{html.escape(link, quote=True)}" target="_blank" '
                       'rel="noopener">Medium →</a></p>')
    elif link:
        source_html = ('<p class="article-source mono">'
                       f'<a href="{html.escape(link, quote=True)}" target="_blank" '
                       'rel="noopener">Original link →</a></p>')
    else:
        source_html = ""
    desc = rec.get("desc") or excerpt(rec["body"])
    html_doc = ARTICLE_TEMPLATE.format(
        title=html.escape(rec["title"]),
        desc=html.escape(desc),
        tags=tag_html(rec["tags"]),
        iso_date=rec["dt"].date().isoformat(),
        display_date=rec["dt"].strftime("%b %d, %Y"),
        body=rec["body"],
        source_html=source_html,
        year=date.today().year,
    )
    (page_dir / "index.html").write_text(html_doc, encoding="utf-8")


def make_card(rec: dict, base: str = "writeups/") -> str:
    """Render one card. `base` is the path prefix to the self-hosted pages
    ("writeups/" from the homepage, "" from the archive which is already inside
    writeups/)."""
    common = dict(
        tags=tag_html(rec["tags"]),
        iso_date=rec["dt"].date().isoformat(),
        display_date=rec["dt"].strftime("%b %Y"),
        title=html.escape(rec["title"]),
        desc=html.escape(rec.get("desc") or excerpt(rec["body"])),
    )
    if rec["body"]:  # self-hosted page → same-tab link
        return LOCAL_CARD_TEMPLATE.format(url=f"{base}{rec['slug']}/", **common)
    # external-only card → new tab
    return CARD_TEMPLATE.format(url=html.escape(rec["link"], quote=True), **common)


def render_archive(records: list) -> None:
    WRITEUPS_DIR.mkdir(parents=True, exist_ok=True)
    cards = "\n".join(make_card(r, base="") for r in records)
    # .replace (not .format) because the template embeds JS with { } braces;
    # substitute count/year first so card content is never rescanned for tokens.
    html_doc = (ARCHIVE_TEMPLATE
                .replace("{count}", str(len(records)))
                .replace("{year}", str(date.today().year))
                .replace("{cards}", cards))
    (WRITEUPS_DIR / "index.html").write_text(html_doc, encoding="utf-8")


# ---------------- minimal Markdown -> HTML (stdlib only) ----------------

def md_inline(text: str) -> str:
    stash = []

    def _stash(m):
        stash.append(m.group(1))
        return f"\x00{len(stash) - 1}\x00"

    text = re.sub(r"`([^`]+)`", _stash, text)          # protect inline code
    text = html.escape(text)
    text = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", r'<img src="\2" alt="\1" />', text)
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)",
                  r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__([^_]+)__", r"<strong>\1</strong>", text)
    text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
    text = re.sub(r"(?<!\w)_([^_]+)_(?!\w)", r"<em>\1</em>", text)
    text = re.sub(r"\x00(\d+)\x00",
                  lambda m: f"<code>{html.escape(stash[int(m.group(1))])}</code>", text)
    return text


_BLOCK_START = re.compile(r"^(#{1,6}\s|```|>\s?|\s*[-*+]\s+|\s*\d+\.\s+)")
_HR = re.compile(r"^(\*{3,}|-{3,}|_{3,})$")


def md_to_html(md: str) -> str:
    lines = md.replace("\r\n", "\n").split("\n")
    out, i, n = [], 0, len(lines)
    while i < n:
        line = lines[i]
        if line.strip().startswith("```"):                       # fenced code
            buf, i = [], i + 1
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i]); i += 1
            i += 1
            out.append(f"<pre><code>{html.escape(chr(10).join(buf))}</code></pre>")
            continue
        if not line.strip():
            i += 1; continue
        m = re.match(r"(#{1,6})\s+(.*)", line)                   # heading
        if m:
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{md_inline(m.group(2).strip())}</h{lvl}>")
            i += 1; continue
        if _HR.match(line.strip()):                              # horizontal rule
            out.append("<hr />"); i += 1; continue
        if line.lstrip().startswith(">"):                        # blockquote
            buf = []
            while i < n and lines[i].lstrip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i])); i += 1
            out.append(f"<blockquote>{md_inline(' '.join(buf))}</blockquote>")
            continue
        if re.match(r"^\s*[-*+]\s+", line):                      # unordered list
            items = []
            while i < n and re.match(r"^\s*[-*+]\s+", lines[i]):
                items.append(re.sub(r"^\s*[-*+]\s+", "", lines[i])); i += 1
            out.append("<ul>" + "".join(f"<li>{md_inline(x)}</li>" for x in items) + "</ul>")
            continue
        if re.match(r"^\s*\d+\.\s+", line):                      # ordered list
            items = []
            while i < n and re.match(r"^\s*\d+\.\s+", lines[i]):
                items.append(re.sub(r"^\s*\d+\.\s+", "", lines[i])); i += 1
            out.append("<ol>" + "".join(f"<li>{md_inline(x)}</li>" for x in items) + "</ol>")
            continue
        buf = []                                                 # paragraph
        while i < n and lines[i].strip() and not _BLOCK_START.match(lines[i]) \
                and not _HR.match(lines[i].strip()):
            buf.append(lines[i].strip()); i += 1
        out.append(f"<p>{md_inline(' '.join(buf))}</p>")
    return "\n".join(out)


# ---------------- collect writeups from both sources ----------------

def split_frontmatter(raw: str):
    if raw.lstrip().startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) == 3:
            meta = {}
            for line in parts[1].strip().splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip().lower()] = v.strip()
            return meta, parts[2].lstrip("\n")
    return {}, raw


def parse_post(path: Path):
    meta, body_md = split_frontmatter(path.read_text(encoding="utf-8"))
    title = meta.get("title") or path.stem.replace("-", " ").title()
    slug = meta.get("slug") or slugify(title)
    dstr = meta.get("date", "")
    try:
        dt = datetime.fromisoformat(dstr)
    except ValueError:
        try:
            dt = datetime.strptime(dstr, "%Y-%m-%d")
        except ValueError:
            dt = datetime.fromtimestamp(path.stat().st_mtime)
    tags = [t.strip() for t in meta.get("tags", "").split(",") if t.strip()]
    link = meta.get("link") or meta.get("external")
    body = md_to_html(body_md) if body_md.strip() else ""
    if not body and not link:
        print(f"  ! skipping {path.name}: no content and no 'link:'")
        return None
    return {"title": title, "slug": slug, "dt": dt, "tags": tags,
            "desc": meta.get("description", ""), "body": body,
            "source": "local", "link": link}


def collect_local():
    if not POSTS_DIR.exists():
        return []
    return [r for r in (parse_post(p) for p in sorted(POSTS_DIR.glob("*.md"))) if r]


def collect_medium():
    if not MEDIUM_CACHE.exists():
        return []
    out = []
    for e in json.loads(MEDIUM_CACHE.read_text(encoding="utf-8")):
        out.append({"title": e["title"], "slug": e["slug"],
                    "dt": datetime.fromisoformat(e["dt"]), "tags": e["tags"],
                    "desc": e.get("desc", ""), "body": e["body"],
                    "source": "medium", "link": e["link"]})
    return out


def rebuild():
    """Regenerate every writeup page + the homepage cards from all sources."""
    records, seen = [], set()
    for rec in collect_local() + collect_medium():   # local wins on slug clash
        if rec["slug"] in seen:
            continue
        seen.add(rec["slug"])
        records.append(rec)
    records.sort(key=lambda r: r["dt"].replace(tzinfo=None), reverse=True)

    cards = []
    for rec in records:
        if rec["body"]:
            render_article(rec)
        cards.append(make_card(rec))
        tag = "medium" if rec["source"] == "medium" else "local "
        print(f"  ✓ [{tag}] {rec['title']}")

    before, _, after = split_sections(read_index())
    write_index(before, cards, after)
    render_archive(records)
    return records


# ---------------- commands ----------------

def cmd_build(_args) -> None:
    records = rebuild()
    if not records:
        die("no writeups found — add Markdown to posts/ or run: "
            "python3 manage.py sync-medium")
    print(f"\nbuilt {len(records)} writeup(s). Preview with: python3 manage.py serve")


def cmd_new_writeup(args) -> None:
    POSTS_DIR.mkdir(exist_ok=True)
    title = args.title or input("Title: ").strip()
    if not title:
        die("title is required")
    slug = slugify(title)
    path = POSTS_DIR / f"{slug}.md"
    if path.exists():
        die(f"{path} already exists")
    path.write_text(POST_SCAFFOLD.format(title=title, date=date.today().isoformat()),
                    encoding="utf-8")
    print(f"created {path}")
    print("Edit it, then run: python3 manage.py build")


def cmd_sync_medium(args) -> None:
    url = args.feed or FEED_URL
    print(f"fetching {url} …")
    try:
        raw = fetch(url)
    except Exception as exc:  # noqa: BLE001 - surface any network error plainly
        die(f"could not fetch feed: {exc}")
    entries = parse_feed(raw)
    if not entries:
        die("feed contained no posts")
    cache = [{"title": e["title"], "slug": e["slug"], "link": e["link"],
              "body": e["body"], "dt": e["dt"].isoformat(), "tags": e["tags"],
              "desc": excerpt(e["body"])} for e in entries]
    MEDIUM_CACHE.write_text(json.dumps(cache, indent=2, ensure_ascii=False),
                            encoding="utf-8")
    print(f"  cached {len(entries)} Medium post(s)")
    records = rebuild()
    print(f"\nsynced. {len(records)} writeup(s) total. Preview: python3 manage.py serve")

def cmd_list(_args) -> None:
    _, block, _ = split_sections(read_index())
    cards = parse_cards(block)
    if not cards:
        print("no writeups yet")
        return
    for i, card in enumerate(cards, 1):
        title, when, url = card_summary(card)
        print(f"{i}. [{when}] {title}\n   {url}")


def prompt_if_missing(value, label):
    if value:
        return value
    value = input(f"{label}: ").strip()
    if not value:
        die(f"{label} is required")
    return value


def cmd_add(args) -> None:
    title = prompt_if_missing(args.title, "Title")
    url = prompt_if_missing(args.url, "URL")
    desc = prompt_if_missing(args.desc, "One-line description")
    tags = args.tags or input("Tags (comma-separated, e.g. web,csrf): ").strip()

    if not re.match(r"^https?://", url):
        die("URL must start with http:// or https://")

    iso = args.date or date.today().isoformat()
    try:
        display = datetime.strptime(iso, "%Y-%m-%d").strftime("%b %Y")
    except ValueError:
        die("--date must be YYYY-MM-DD")

    tag_html = "".join(
        f'<span class="tag">{html.escape(t.strip().lower())}</span>'
        for t in tags.split(",") if t.strip()
    ) or '<span class="tag">writeup</span>'

    card = CARD_TEMPLATE.format(
        url=html.escape(url, quote=True),
        tags=tag_html,
        iso_date=iso,
        display_date=display,
        title=html.escape(title),
        desc=html.escape(desc),
    )

    before, block, after = split_sections(read_index())
    cards = parse_cards(block)
    cards.insert(0, card)  # newest first
    write_index(before, cards, after)
    print(f"added: {title}\n{len(cards)} writeup(s) total. Preview with: python3 manage.py serve")


def cmd_remove(args) -> None:
    before, block, after = split_sections(read_index())
    cards = parse_cards(block)
    if not 1 <= args.number <= len(cards):
        die(f"pick a number between 1 and {len(cards)} (see list-writeups)")
    title, _, _ = card_summary(cards[args.number - 1])
    confirm = input(f'remove "{title}"? [y/N] ').strip().lower()
    if confirm != "y":
        print("aborted")
        return
    cards.pop(args.number - 1)
    write_index(before, cards, after)
    print(f"removed: {title}")


def cmd_set_resume(args) -> None:
    src = Path(args.pdf).expanduser()
    if not src.exists():
        die(f"{src} not found")
    if src.suffix.lower() != ".pdf":
        die("resume must be a PDF")
    RESUME.parent.mkdir(exist_ok=True)
    shutil.copyfile(src, RESUME)
    print(f"resume updated: {src} -> {RESUME}")


def cmd_serve(args) -> None:
    import http.server
    import functools
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    print(f"serving at http://localhost:{args.port}  (Ctrl+C to stop)")
    http.server.ThreadingHTTPServer(("", args.port), handler).serve_forever()


def main() -> None:
    p = argparse.ArgumentParser(description="Edit the portfolio site.")
    sub = p.add_subparsers(dest="command", required=True)

    new = sub.add_parser("new-writeup", help="scaffold a Markdown writeup in posts/")
    new.add_argument("title", nargs="?", help="writeup title")
    new.set_defaults(fn=cmd_new_writeup)

    sub.add_parser("build",
                   help="render Markdown posts + merge Medium cache (no network)"
                   ).set_defaults(fn=cmd_build)

    syn = sub.add_parser("sync-medium",
                         help="refresh Medium cache from RSS, then build")
    syn.add_argument("--feed", help=f"RSS feed URL (default: {FEED_URL})")
    syn.set_defaults(fn=cmd_sync_medium)

    sub.add_parser("list-writeups", help="list writeup cards").set_defaults(fn=cmd_list)

    add = sub.add_parser("add-writeup", help="add a writeup card (newest first)")
    add.add_argument("--title")
    add.add_argument("--url")
    add.add_argument("--desc")
    add.add_argument("--tags", help="comma-separated, e.g. web,csrf")
    add.add_argument("--date", help="YYYY-MM-DD (default: today)")
    add.set_defaults(fn=cmd_add)

    rm = sub.add_parser("remove-writeup", help="remove a writeup by number")
    rm.add_argument("number", type=int)
    rm.set_defaults(fn=cmd_remove)

    res = sub.add_parser("set-resume", help="replace assets/resume.pdf")
    res.add_argument("pdf")
    res.set_defaults(fn=cmd_set_resume)

    srv = sub.add_parser("serve", help="local preview server")
    srv.add_argument("--port", type=int, default=8000)
    srv.set_defaults(fn=cmd_serve)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
