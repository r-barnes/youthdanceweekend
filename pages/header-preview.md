---
layout: page
title: Header Image Preview
header: no
permalink: /header-preview/
noindex: true
style: |
  .header-preview-item { margin-bottom: 2.5rem; }
  .header-preview-item h3 { margin-bottom: 0.25rem; font-size: 0.9rem; font-family: monospace; color: #555; }
  .header-preview-banner {
    display: block;
    width: 100vw;
    margin-left: calc(-50vw + 50%);
    background-size: cover;
    background-repeat: no-repeat;
    height: 200px;
  }
  @media (min-width: 641px)  { .header-preview-banner { height: 280px; } }
  @media (min-width: 1025px) { .header-preview-banner { height: 310px; } }
  @media (min-width: 1441px) { .header-preview-banner { height: 380px; } }
---

{% for img in site.data.header_images %}
<div class="header-preview-item">
  <h3>{{ img.file }} — {{ img.position }}</h3>
  <div class="header-preview-banner" style="background-image: url('/images/ydw/headers/{{ img.file }}'); background-position: {{ img.position }};"></div>
</div>
{% endfor %}
