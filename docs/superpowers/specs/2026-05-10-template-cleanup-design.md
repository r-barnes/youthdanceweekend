# Template Cleanup Design

**Date:** 2026-05-10
**Status:** Approved

## Overview

Remove leftover "Feeling Responsive" Jekyll theme files that were never replaced with YDW content. The site is a static page site — no blog, no media player, no theme demos. Everything being removed is either a theme showcase page, a blog feature, or a legacy media player asset.

## Files to Delete

### Pages
- `pages/changelog.md` — theme changelog
- `pages/documentation.md` — theme documentation
- `pages/headers.md` — theme header demo
- `pages/info.md` — theme author's "about" page
- `pages/roadmap.md` — theme roadmap
- `pages/redirected_page.md` — redirect layout demo

### Drafts
- All 9 files in `_drafts/` — theme example drafts (gallery, page variants, post variants, video)

### Blog Directory
- `blog/archive.html`
- `blog/index.html`

### Layouts
- `_layouts/redirect.html` — only used by `redirected_page.md`
- `_layouts/video.html` — unused
- `_layouts/blog.html` — blog is disabled in navigation

### Includes
- `_includes/list-posts/` — blog feature
- `_includes/list-collection/` — blog feature
- `_includes/next-previous-post-in-category/` — blog feature
- `_includes/_pagination.html` — blog feature
- `_includes/_comments.html` — Disqus comments, not configured or used
- `_includes/_improve_content.html` — "edit on GitHub" link, not used

### Assets
- `assets/mediaelement_js/` — Flash/Silverlight media player (~20 files including `.swf`), nothing on the site uses it

## Reference Audit (after deletion)

Search all remaining source files for any references to deleted items:
- Layout names: `blog`, `video`, `redirect`
- Deleted include filenames
- `mediaelement_js` path
- Any `paginate` config that depended on the blog

Fix any references found before committing. Run `jekyll build` to confirm no errors.

## Commit Strategy

Single commit containing all deletions plus any reference fixes found during audit.

## Out of Scope

- `images/` template images (deferred — touches masthead/footer rendering)
- `_data/` template files (deferred — referenced by active includes)
- `old_site/`, `old_site_extractor/`, `email_attachments/` (kept intentionally)
