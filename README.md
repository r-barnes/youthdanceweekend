# Youth Dance Weekend Website

## For editors

These are the three folders you'll work with:

- **`pages/`** — the site's pages (About, Events, FAQ, etc.). Edit existing ones or add new ones here.
- **`images/`** — photos and images used across the site.
- **`documents/`** — PDFs and other downloadable files linked from pages.

To update the site navigation, edit **`navigation.yml`** in this folder. Comments inside that file explain how.

## Technical infrastructure

Everything below is the site's technical infrastructure. You shouldn't need to touch it for everyday content updates.

- **`framework/`** — Jekyll layouts, includes, and Sass stylesheets.
- **`_config.yml`** — main Jekyll configuration (site URL, theme settings, build options).
- **`_config_dev.yml`** — overrides for local development (run with `jekyll serve --config _config.yml,_config_dev.yml`).
- **`_data/navigation.yml`** — site navigation menu structure.
- **`Gemfile`** / **`Gemfile.lock`** — Ruby gem dependencies for building the site.
- **`jekyll-theme-feeling-responsive.gemspec`** — gem specification for the theme.
- **`CNAME`** — custom domain (`youthdanceweekend.org`); tells GitHub Pages where to serve the site. Don't delete or rename it.
- **`LICENSE`** — open-source license for the theme.
- **`_generated_site/`** — local build output; ignored by git and safe to delete.
- **`.github/`** — GitHub Actions workflows for automated deployment.
- **`.bundle/`**, **`.jekyll-cache/`**, **`.gitignore`** — build tooling caches and git ignore rules.
