# Mohammad Kaif — Portfolio

Personal portfolio site for [@_mkahmad](https://x.com/_mkahmad) — Security Researcher & Bug Hunter.

Fully static (HTML/CSS/JS, no build step) and ready for GitHub Pages.

## Structure

```
portfolio/
├── index.html        # the whole site (single page)
├── css/style.css     # styles
├── js/main.js        # scroll reveal, mobile menu, nav highlight
├── manage.py         # CLI tool: writeups (Markdown + Medium), resume, preview
├── posts/            # your self-authored Markdown writeups (source)
│   └── <slug>.md
├── writeups/         # generated (from posts/ + Medium) — don't edit by hand
│   ├── index.html    # archive page ("View all writeups") — vertical list, paginated 6/page
│   └── <slug>/index.html
├── .medium-cache.json # cached Medium feed, refreshed by `sync-medium`
├── assets/
│   └── resume.pdf    # your resume (Download Resume button)
└── .nojekyll         # tells GitHub Pages to skip Jekyll processing
```

## Editing the site

### Writeups

Writeups come from **two sources**, merged into one section sorted newest-first:

1. **Self-authored Markdown** — files in `posts/*.md` that you write directly.
2. **Medium mirrors** — pulled from your RSS feed (`kaif0x01.medium.com/feed`).

Both render to self-hosted, styled pages under `writeups/<slug>/`, and both get
a card on the homepage. Three commands drive it:

```bash
cd portfolio

# --- write your own, hosted here ---
python3 manage.py new-writeup "Breaking XYZ's OAuth"   # scaffolds posts/<slug>.md
#   ...edit that Markdown file (frontmatter + body)...
python3 manage.py build                                # renders posts + merges Medium

# --- mirror your Medium posts ---
python3 manage.py sync-medium     # refresh Medium cache from RSS, then build

python3 manage.py serve           # preview, then commit + push
```

**Markdown format** — each file in `posts/` starts with frontmatter:

```markdown
---
title: Breaking XYZ's OAuth
date: 2026-07-08
tags: web, oauth, auth
description: One-line summary for the card and search results.
---

Body in **Markdown**: headings, lists, `code`, ```fenced``` blocks,
> blockquotes, [links](https://…) and ![images](https://…).
```

Optional frontmatter: `slug:` (custom URL) and `link:` (an "original" link; a
post with only `link:` and no body becomes a card that links straight out).

**How the two sources interact**

- `build` runs **offline** — it renders `posts/*.md` and merges the cached Medium
  posts. Run it after editing any Markdown.
- `sync-medium` re-fetches the feed into `.medium-cache.json`, then builds.
- Both regenerate the whole Writeups section, so ordering stays correct. A
  single-card `add-writeup` entry is replaced on the next build/sync.
- If a Markdown post and a Medium post share a slug, **your Markdown wins** — a
  clean way to "claim" and self-host a post you'd rather not depend on Medium for.
- The Medium feed only exposes the **10 most recent** posts; anything you want to
  keep permanently, author (or re-author) as Markdown in `posts/`.
- Mirrored images stay on Medium's CDN; Markdown images use whatever URL you give.

### With `manage.py` (manual writeups, resume, preview)

No dependencies — just Python 3, which macOS already has.

```bash
cd portfolio

# see current writeups (numbered)
python3 manage.py list-writeups

# add a new writeup — either answer prompts…
python3 manage.py add-writeup

# …or pass everything as flags
python3 manage.py add-writeup \
  --title "Breaking XYZ's OAuth flow" \
  --url "https://kaif0x01.medium.com/..." \
  --desc "How a redirect_uri bypass led to account takeover." \
  --tags web,oauth \
  --date 2026-07-08        # optional, defaults to today

# remove writeup #3 (numbers from list-writeups)
python3 manage.py remove-writeup 3

# replace the resume PDF
python3 manage.py set-resume ~/Downloads/MyResume.pdf

# preview locally at http://localhost:8000
python3 manage.py serve
```

New writeups are inserted at the top (newest first). Titles and descriptions
are HTML-escaped automatically, so any characters are safe.

> ⚠️ `manage.py` relies on the `<!-- WRITEUPS:START -->` / `<!-- WRITEUPS:END -->`
> comments in `index.html` — don't delete them.

### By hand (everything else)

| What | Where |
|---|---|
| Bio / About text & stats | `index.html` → `<!-- ABOUT -->` section |
| Experience / job history | `index.html` → `<!-- EXPERIENCE -->` section (copy a `<article class="tl-item">` block) |
| Highlight cards | `index.html` → `<!-- HIGHLIGHTS -->` section (copy a `<article class="card">` block) |
| Focus areas / skills | `index.html` → `<!-- FOCUS AREAS -->` section |
| Social links / email | `index.html` → hero `<ul class="socials">` and contact section |
| Colors, fonts, spacing | `css/style.css` → the `:root { … }` variables at the top |

### Publishing an update

After any edit, commit and push — GitHub Pages redeploys automatically in ~1 minute:

```bash
git add -A && git commit -m "Update portfolio" && git push
```

## Before deploying

1. **Replace `assets/resume.pdf`** with your actual resume.
2. Add/edit writeups in the *Writeups* section of `index.html` as you publish new ones.

## Deploy to GitHub Pages

### Option A — user site (recommended): `https://<username>.github.io`

```bash
cd portfolio
git init
git add .
git commit -m "Initial portfolio"
# create a repo named <username>.github.io on GitHub first, then:
git remote add origin git@github.com:<username>/<username>.github.io.git
git branch -M main
git push -u origin main
```

Then on GitHub: **Settings → Pages → Source: Deploy from a branch → main / (root)**.
The site goes live at `https://<username>.github.io` within a minute or two.

### Option B — project site: `https://<username>.github.io/portfolio`

Same steps, but name the repo anything (e.g. `portfolio`). All paths in the site
are relative, so it works from a subpath too.

## Local preview

```bash
cd portfolio
python3 -m http.server 8000
# open http://localhost:8000
```
