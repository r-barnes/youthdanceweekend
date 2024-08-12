---
layout: page
show_meta: false
title: "Events"
# subheadline: "Layouts of Feeling Responsive"
header:
   image_fullwidth: "ydw/cropped-YDW2022DSC04384-scaled-1.jpg"
permalink: "/events/"
---
<ul>
    {% for post in site.categories.events %}
    <li><a href="{{ site.url }}{{ site.baseurl }}{{ post.url }}">{{ post.title }}</a></li>
    {% endfor %}
</ul>