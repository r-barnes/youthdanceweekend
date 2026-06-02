# Repo Structure for Non-Technical Editors — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize the repository so non-technical editors can immediately identify what to touch (pages, images, documents) and feel safe ignoring everything else (framework/).

**Architecture:** Move Jekyll framework directories (_layouts, _includes, _sass, assets) into a single `framework/` folder; extract user-facing PDFs into a new `documents/` folder; update the three config settings Jekyll needs to find the moved dirs; update seven URL references in template files and four PDF links in pages; add orientation READMEs.

**Tech Stack:** Jekyll 4.3.3, Bundler, git

---

## File Map

**Created:**
- `documents/` — top-level folder for user-facing PDFs
- `documents/charts/` — survey charts by year
- `framework/` — all site infrastructure (moved into here)
- `README.md` — root editor orientation (replaces existing)
- `pages/README.md` — how to edit and add pages
- `images/README.md` — how to add and use images
- `documents/README.md` — how to add and link documents

**Moved:**
- `assets/charts/*.pdf` → `documents/charts/`
- `assets/hulbert-*.pdf` → `documents/`
- `_layouts/` → `framework/layouts/`
- `_includes/` → `framework/includes/`
- `_sass/` → `framework/sass/`
- `assets/` → `framework/assets/`

**Modified:**
- `_config.yml` — add `layouts_dir`, `includes_dir`, update `sass.sass_dir`
- `framework/includes/_head.html` — six `/assets/...` URLs → `/framework/assets/...`
- `framework/includes/_footer_scripts.html` — one `/assets/...` URL → `/framework/assets/...`
- `pages/index.md` — two PDF links
- `pages/events/ydw2022.md` — one PDF link
- `pages/events/ydw2024.md` — one PDF link
- `navigation.yml` — add explanatory comments

---

## Task 0: Commit the plan

- [ ] **Step 1: Commit this plan file**

```bash
git add docs/superpowers/plans/2026-06-01-repo-structure-for-editors.md
git commit -m "Add implementation plan for repo structure reorganization"
```

---

## Task 1: Create `documents/` and move PDFs

**Files:**
- Create: `documents/charts/`
- Move: `assets/charts/ydw-2022-charts-and-graphs.pdf` → `documents/charts/`
- Move: `assets/charts/ydw-2024-charts-and-graphs.pdf` → `documents/charts/`
- Move: `assets/hulbert-facility-map.pdf` → `documents/`
- Move: `assets/hulbert-main-house.pdf` → `documents/`
- Modify: `pages/index.md` lines 11, 13
- Modify: `pages/events/ydw2022.md` line 76
- Modify: `pages/events/ydw2024.md` line 137

- [ ] **Step 1: Create documents/ and move PDFs**

```bash
mkdir -p documents/charts
git mv assets/charts/ydw-2022-charts-and-graphs.pdf documents/charts/
git mv assets/charts/ydw-2024-charts-and-graphs.pdf documents/charts/
git mv assets/hulbert-facility-map.pdf documents/
git mv assets/hulbert-main-house.pdf documents/
rmdir assets/charts
```

- [ ] **Step 2: Update PDF links in `pages/index.md`**

Change lines 11 and 13 from:
```markdown
Here is a map of the facilities: [Hulbert Map](/assets/hulbert-facility-map.pdf)

And here is a map of the main building that we will be using: [Hulbert Main House](/assets/hulbert-main-house.pdf)
```
To:
```markdown
Here is a map of the facilities: [Hulbert Map](/documents/hulbert-facility-map.pdf)

And here is a map of the main building that we will be using: [Hulbert Main House](/documents/hulbert-main-house.pdf)
```

- [ ] **Step 3: Update PDF link in `pages/events/ydw2022.md`**

Find line 76 (search for `ydw-2022-charts`) and change:
```markdown
[Download the 2022 YDW Charts & Graphs (PDF)](/assets/charts/ydw-2022-charts-and-graphs.pdf)
```
To:
```markdown
[Download the 2022 YDW Charts & Graphs (PDF)](/documents/charts/ydw-2022-charts-and-graphs.pdf)
```

- [ ] **Step 4: Update PDF link in `pages/events/ydw2024.md`**

Find line 137 (search for `ydw-2024-charts`) and change:
```markdown
[Download the 2024 YDW Charts & Graphs (PDF)](/assets/charts/ydw-2024-charts-and-graphs.pdf)
```
To:
```markdown
[Download the 2024 YDW Charts & Graphs (PDF)](/documents/charts/ydw-2024-charts-and-graphs.pdf)
```

- [ ] **Step 5: Verify build**

```bash
bundle exec jekyll build
```

Expected: exits with code 0 and no errors. If it errors, check the PDF link changes for typos.

- [ ] **Step 6: Commit**

```bash
git add documents/ assets/ pages/index.md pages/events/ydw2022.md pages/events/ydw2024.md
git commit -m "Move user-facing PDFs from assets/ to documents/"
```

---

## Task 2: Move `_layouts/` into `framework/`

**Files:**
- Create: `framework/`
- Move: `_layouts/` → `framework/layouts/`
- Modify: `_config.yml`

- [ ] **Step 1: Create `framework/` and move layouts**

```bash
mkdir framework
git mv _layouts framework/layouts
```

- [ ] **Step 2: Add `layouts_dir` to `_config.yml`**

Add this line after the `data_dir: .` line (around line 2):
```yaml
layouts_dir:  framework/layouts
```

- [ ] **Step 3: Verify build**

```bash
bundle exec jekyll build
```

Expected: exits with code 0. If it errors with "layout not found", check that `layouts_dir` is correctly set.

- [ ] **Step 4: Commit**

```bash
git add framework/ _layouts _config.yml
git commit -m "Move _layouts/ into framework/layouts/"
```

---

## Task 3: Move `_includes/` into `framework/`

**Files:**
- Move: `_includes/` → `framework/includes/`
- Modify: `_config.yml`

- [ ] **Step 1: Move includes**

```bash
git mv _includes framework/includes
```

- [ ] **Step 2: Add `includes_dir` to `_config.yml`**

Add this line immediately after the `layouts_dir` line you added in Task 2:
```yaml
includes_dir: framework/includes
```

- [ ] **Step 3: Verify build**

```bash
bundle exec jekyll build
```

Expected: exits with code 0. If it errors with "could not locate the included file", check that `includes_dir` is correctly set.

- [ ] **Step 4: Commit**

```bash
git add framework/includes/ _includes _config.yml
git commit -m "Move _includes/ into framework/includes/"
```

---

## Task 4: Move `_sass/` into `framework/`

**Files:**
- Move: `_sass/` → `framework/sass/`
- Modify: `_config.yml`

- [ ] **Step 1: Move sass directory**

```bash
git mv _sass framework/sass
```

- [ ] **Step 2: Update `sass_dir` in `_config.yml`**

Find the existing sass block:
```yaml
sass:
    sass_dir : _sass
    style    : :compressed
```

Change it to:
```yaml
sass:
    sass_dir : framework/sass
    style    : :compressed
```

- [ ] **Step 3: Verify build**

```bash
bundle exec jekyll build
```

Expected: exits with code 0 and CSS is generated at `_site/assets/css/styles_feeling_responsive.css`. If it errors with import or sass issues, check that `sass_dir` path is correct.

- [ ] **Step 4: Commit**

```bash
git add framework/sass/ _sass _config.yml
git commit -m "Move _sass/ into framework/sass/"
```

---

## Task 5: Move `assets/` into `framework/` and update URL references

**Files:**
- Move: `assets/` → `framework/assets/`
- Modify: `framework/includes/_head.html`
- Modify: `framework/includes/_footer_scripts.html`

- [ ] **Step 1: Move assets**

```bash
git mv assets framework/assets
```

- [ ] **Step 2: Update six references in `framework/includes/_head.html`**

Make these six replacements (each is a separate line in the file):

| Find | Replace |
|------|---------|
| `{{ url }}/assets/css/styles_feeling_responsive.css` | `{{ url }}/framework/assets/css/styles_feeling_responsive.css` |
| `{{ url }}/assets/js/modernizr.min.js` | `{{ url }}/framework/assets/js/modernizr.min.js` |
| `"/assets/img/favicon-16x16.png"` | `"/framework/assets/img/favicon-16x16.png"` |
| `"/assets/img/favicon-32x32.png"` | `"/framework/assets/img/favicon-32x32.png"` |
| `"/assets/img/apple-touch-icon.png"` | `"/framework/assets/img/apple-touch-icon.png"` |

Note: `apple-touch-icon.png` appears twice on adjacent lines (84 and 87) — replace both.

- [ ] **Step 3: Update one reference in `framework/includes/_footer_scripts.html`**

Change line 1 from:
```html
<script src="{{ site.url }}{{ site.baseurl }}/assets/js/javascript.min.js"></script>
```
To:
```html
<script src="{{ site.url }}{{ site.baseurl }}/framework/assets/js/javascript.min.js"></script>
```

- [ ] **Step 4: Verify build**

```bash
bundle exec jekyll build
```

Expected: exits with code 0. Spot-check that `_site/framework/assets/css/styles_feeling_responsive.css` exists.

```bash
ls _site/framework/assets/css/
```

Expected: `styles_feeling_responsive.css` is present.

- [ ] **Step 5: Commit**

```bash
git add framework/assets/ assets/ framework/includes/_head.html framework/includes/_footer_scripts.html
git commit -m "Move assets/ into framework/assets/ and update URL references"
```

---

## Task 6: Add README files

**Files:**
- Modify: `README.md`
- Create: `pages/README.md`
- Create: `images/README.md`
- Create: `documents/README.md`

- [ ] **Step 1: Replace root `README.md`**

Replace the full contents of `README.md` with:

```markdown
# Youth Dance Weekend Website

## For editors

These are the three folders you'll work with:

- **`pages/`** — the site's pages (About, Events, FAQ, etc.). Edit existing ones or add new ones here.
- **`images/`** — photos and images used across the site.
- **`documents/`** — PDFs and other downloadable files linked from pages.

To update the site navigation, edit **`navigation.yml`** in this folder. Comments inside that file explain how.

Everything else — `framework/`, `_config.yml`, `Gemfile`, and so on — is the site's technical infrastructure. You shouldn't need to touch it for everyday content updates.
```

- [ ] **Step 2: Create `pages/README.md`**

```markdown
# Pages

This folder contains all of the site's pages.

## Editing an existing page

Open the `.md` file and edit the content below the second `---` line. The block between the two `---` lines at the top is "front matter" — it sets the page title, URL, and other settings. Avoid changing it unless you know what you're doing.

## Adding a new page

Copy an existing page as a starting point. Update the front matter:

- `title:` — the page title shown in the browser tab and at the top of the page
- `permalink:` — the URL for the page, e.g. `/new-page/`

Then replace the content below the front matter with your new content, written in Markdown.

Pages for individual events live in the `events/` subfolder.
```

- [ ] **Step 3: Create `images/README.md`**

````markdown
# Images

This folder contains photos and images used across the site.

- `ydw/` — general YDW photos: headshots, event photos, decorative images
- `ydw-history/` — historical photos and charts organized by year

## Adding an image

Drop the image file into the appropriate subfolder.

## Using an image in a page

In any `.md` page file, add an image like this:

```markdown
![Description of image](/images/ydw/your-image-filename.jpg)
```

Use a path starting with `/images/` followed by the subfolder and filename.
````

- [ ] **Step 4: Create `documents/README.md`**

````markdown
# Documents

This folder contains PDFs and other downloadable files linked from the site.

- `charts/` — survey results and data charts by year

## Adding a document

Drop the file into this folder (or `charts/` if it's a survey chart).

## Linking to a document from a page

In any `.md` page file, add a link like this:

```markdown
[Link text](/documents/your-file.pdf)
```

Use a path starting with `/documents/` followed by the filename.
````

- [ ] **Step 5: Verify build**

```bash
bundle exec jekyll build
```

Expected: exits with code 0. README files are not pages (no front matter), so Jekyll will ignore them — this is intentional.

- [ ] **Step 6: Commit**

```bash
git add README.md pages/README.md images/README.md documents/README.md
git commit -m "Add editor-oriented README files"
```

---

## Task 7: Add explanatory comments to `navigation.yml`

**Files:**
- Modify: `navigation.yml`

- [ ] **Step 1: Add comments to `navigation.yml`**

Replace the full contents of `navigation.yml` with:

```yaml
# navigation.yml — Site navigation
#
# Each entry below appears as a link in the site header.
# Entries with side: left appear on the left; side: right on the right.
#
# To add a new link, copy an existing entry and update title and url.
# To reorder links, move entries up or down (keep the leading dash).
# To remove a link, delete its entry (the "- title:" line and the two lines after it).
#
# The url must match the permalink in the corresponding page file.

- title: Home
  url: "/"
  side: left
- title: About
  url: "/about/"
  side: left
- title: Policies
  url: "/policies/"
  side: left
- title: FAQ
  url: "/faq/"
  side: left
- title: Donate
  url: "/donate/"
  side: left
- title: Contact
  url: "/contact/"
  side: right
```

- [ ] **Step 2: Verify build**

```bash
bundle exec jekyll build
```

Expected: exits with code 0 and navigation renders correctly.

- [ ] **Step 3: Commit**

```bash
git add navigation.yml
git commit -m "Add explanatory comments to navigation.yml"
```
