# Repo Structure for Non-Technical Editors

**Date:** 2026-06-01
**Status:** Approved

## Goal

Reorganize the repository so that non-technical editors — who use GitHub's web file editor and local clones — can immediately identify what they need to touch and feel confident ignoring everything else.

## Target Editors

Editors who:
- Clone locally and edit via GitHub's web file editor
- Primarily edit existing pages and add new pages
- Occasionally add images
- Rarely update navigation

## Directory Structure (after)

```
pages/               ← edit pages here
images/              ← add images here
documents/           ← add PDFs/downloadable files here
  charts/
    ydw-2022-charts-and-graphs.pdf
    ydw-2024-charts-and-graphs.pdf
  hulbert-facility-map.pdf
  hulbert-main-house.pdf
navigation.yml       ← rarely: update site navigation (commented)
README.md            ← root orientation for editors
framework/           ← site framework, do not touch
  assets/            ← CSS, JS, fonts, favicon, robots.txt, sitemap.xml
  includes/          ← template partials
  layouts/           ← page templates
  sass/              ← stylesheets
_config.yml          ← site config (do not touch)
Gemfile              ← Ruby dependencies (do not touch)
old_site/            ← historical reference
old_site_extractor/  ← historical reference
search_ydw_emails.py ← utility script
```

## Changes Required

### 1. Move directories into `framework/`

| From | To |
|------|----|
| `assets/` | `framework/assets/` |
| `_layouts/` | `framework/layouts/` |
| `_includes/` | `framework/includes/` |
| `_sass/` | `framework/sass/` |

### 2. Create `documents/` and move PDFs

| From | To |
|------|----|
| `assets/charts/ydw-2022-charts-and-graphs.pdf` | `documents/charts/ydw-2022-charts-and-graphs.pdf` |
| `assets/charts/ydw-2024-charts-and-graphs.pdf` | `documents/charts/ydw-2024-charts-and-graphs.pdf` |
| `assets/hulbert-facility-map.pdf` | `documents/hulbert-facility-map.pdf` |
| `assets/hulbert-main-house.pdf` | `documents/hulbert-main-house.pdf` |

### 3. Update `_config.yml`

Add/update these settings:

```yaml
layouts_dir:  framework/layouts
includes_dir: framework/includes
sass:
  sass_dir: framework/sass
  style:    :compressed
```

### 4. Update asset URL references

Seven references in `framework/includes/` (formerly `_includes/`) must change from `/assets/...` to `/framework/assets/...`:

| File | Reference |
|------|-----------|
| `_head.html:25` | `/assets/css/styles_feeling_responsive.css` |
| `_head.html:29` | `/assets/js/modernizr.min.js` |
| `_head.html:84` | `/assets/img/favicon-16x16.png` |
| `_head.html:85` | `/assets/img/favicon-32x32.png` |
| `_head.html:86` | `/assets/img/apple-touch-icon.png` |
| `_head.html:87` | `/assets/img/apple-touch-icon.png` |
| `_footer_scripts.html:1` | `/assets/js/javascript.min.js` |

### 5. Update PDF links in pages

| File | Old path | New path |
|------|----------|----------|
| `pages/events/ydw2024.md:137` | `/assets/charts/ydw-2024-charts-and-graphs.pdf` | `/documents/charts/ydw-2024-charts-and-graphs.pdf` |
| `pages/events/ydw2022.md:76` | `/assets/charts/ydw-2022-charts-and-graphs.pdf` | `/documents/charts/ydw-2022-charts-and-graphs.pdf` |
| `pages/index.md:11` | `/assets/hulbert-facility-map.pdf` | `/documents/hulbert-facility-map.pdf` |
| `pages/index.md:13` | `/assets/hulbert-main-house.pdf` | `/documents/hulbert-main-house.pdf` |

### 6. Add README files

| File | Purpose |
|------|---------|
| `README.md` | Root overview: what's in each content folder, note on navigation.yml, note that framework/ and everything else is hands-off |
| `pages/README.md` | How to edit existing pages and add new ones; front matter basics |
| `images/README.md` | How to add images and reference them from a page |
| `documents/README.md` | How to add PDFs and link to them from a page |

### 7. Add comments to `navigation.yml`

Add inline YAML comments at the top of `navigation.yml` explaining its structure and how to add or reorder navigation entries.

## Verification

After implementation, run `bundle exec jekyll build` and confirm:
- Site builds without errors
- CSS loads correctly (check `/framework/assets/css/styles_feeling_responsive.css` is served)
- PDF links resolve
- Navigation renders correctly
