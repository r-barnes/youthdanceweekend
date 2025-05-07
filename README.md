# Getting started

Linux:
```
sudo apt install ruby # Get ruby installed
# Install bundle somehow
bundle config path ~/.bundle-stuff
```

Local development:
```
bundle exec jekyll serve --config _config.yml,_config_dev.yml
```

Structure:
- `pages` has the templates that determine the actual structure of the site
- `_posts` directory has date-specified site content, the newest appears on the front page
- most actual content is in `_layouts`
- css stuff is in `_sass`
- old_site_extractor has the original site data
- `_data/navigation.yml` holds the structure of the site
- `index.md` holds front matter that will be displayed before the latest even from `_posts`
