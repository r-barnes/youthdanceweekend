---
layout: page
title: Header Image Preview
header: no
permalink: /header-preview/
noindex: true
style: |
  .header-preview-item { margin-bottom: 2rem; }
  .header-preview-item h3 { margin-bottom: 0.25rem; font-size: 0.9rem; font-family: monospace; color: #555; }
  .header-preview-banner {
    width: 100%;
    height: 280px;
    background-size: cover;
    background-repeat: no-repeat;
    border-radius: 4px;
  }
---

{% for img in site.data.header_images %}
<div class="header-preview-item">
  <h3>{{ img.file }} — {{ img.position }}</h3>
  <div class="header-preview-banner" style="background-image: url('/images/ydw/headers/{{ img.file }}'); background-position: {{ img.position }};"></div>
</div>
{% endfor %}
