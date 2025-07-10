# Getting started

Linux:
```
sudo apt install ruby # Get ruby installed
# Install bundle somehow
bundle config path ~/.bundle-stuff
```

Local development:
```
bundle exec jekyll serve --config _config.yml,_config_dev.yml --port 4001
```

Structure:
- `_posts` directory has date-specified site content, the newest appears on the front page
- `pages` has the site content that is not contained in the `_posts` area: this is most of it because we're not actually running a blog.
- `_layouts` converts your pages to the actual site content using html templating. this is what the "framework" does for us.
- css stuff is in `_sass`
- old_site_extractor has the original site data
- `_data/navigation.yml` holds the structure of the site
- `index.md` holds front matter that will be displayed before the latest even from `_posts`
