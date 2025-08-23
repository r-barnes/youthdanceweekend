# Youth Dance Weekend Website

## Getting Started

Linux:
```
sudo apt install ruby # Get ruby installed
# Install bundle somehow
bundle config path ~/.bundle-stuff
```

On Mac, ruby versions were giving me pain. I installed ruby-env to disambiguate.
``` sh
brew install rbenv ruby-build

# Set up for shell, fish in my case
status is-interactive; and rbenv init - fish | source

# 3.3.5 stable with jekyll
rbenv install 3.3.5
rbenv global 3.3.5

```

Local development:
```
bundle exec jekyll serve --config _config.yml,_config_dev.yml --port 4001
```

Structure:
- `_posts` directory has date-specified site content, the newest appears on the front page
- `pages` has the site content that is not contained in the `_posts` area: this is most of it because we're not actually running a blog.
    - `pages-root-folder` contains the main index.md and other important pages
- `_layouts` converts your pages to the actual site content using html templating. this is what the "framework" does for us.
- css stuff is in `_sass`
- old_site_extractor has the original site data
- `_data/navigation.yml` holds the structure of the site
- `index.md` holds front matter that will be displayed before the latest even from `_posts`

## Photos

Photos:
- [2023 Google Photos](https://photos.google.com/share/AF1QipNmy4WBRK787Baz3nx7B7t4b7Y6ePLUmimxzk7NWOJFS__4ZEfUUSFTYbaCDt-nHA?key=dUhlZTNPSEdlQmR5aF85dGlJSDAxbUNBaWxhUGJn)
- [2022 Google Photos](https://photos.google.com/share/AF1QipPYWmSVcHdrvfnCqVJDaUGftiXgzBX4Pv5zcy5jFJTLI-scWlMtiR4N-QgE_26pnA?pli=1&key=b1JqaWdRNnhpZGpOOUNUOElPampzVnZyYzJPNVNR)
