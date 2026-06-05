---
layout: page
show_meta: false
title: "Past schedules"
# subheadline: "Layouts of Feeling Responsive"
header:
   image_fullwidth: ydw/2022-ydw-late-night-dance.webp
permalink: "/events/"
---
<ul>
    {% assign events = site.pages | where: "event", true | sort: "date" | reverse %}
    {% for event in events %}
    <li><a href="{{ site.url }}{{ site.baseurl }}{{ event.url }}">{{ event.title }}</a></li>
    {% endfor %}
</ul>
