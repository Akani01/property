"""Server-rendered article metadata. Merge this module into the existing education app."""

from urllib.parse import urlsplit
from django import template
from django.urls import reverse, NoReverseMatch
from django.utils.html import format_html, format_html_join, strip_tags

register = template.Library()


def _absolute_http(request, value):
    if not value:
        return ""
    try:
        if hasattr(value, "url"):
            value = value.url
        if isinstance(value, dict):
            value = value.get("url") or value.get("src") or ""
        value = str(value).strip()
        if not value:
            return ""
        if urlsplit(value).scheme and urlsplit(value).scheme not in ("http", "https"):
            return ""
        if not value.startswith(("http://", "https://", "/")):
            value = "/media/" + value.removeprefix("media/")
        url = request.build_absolute_uri(value)
        return url if urlsplit(url).scheme in ("http", "https") else ""
    except (ValueError, AttributeError):
        return ""


@register.simple_tag(takes_context=True)
def news_share_meta(context, news):
    """Usage inside the article's head: {% load news_sharing %}{% news_share_meta news %}."""
    request = context.get("request")
    if not request or not news or getattr(news, "is_published", True) is False:
        return ""
    news_id = getattr(news, "pk", None) or getattr(news, "id", None)
    if not news_id:
        return ""
    try:
        path = reverse("education_news_detail", kwargs={"pk": news_id})
    except NoReverseMatch:
        from urllib.parse import quote

        path = "/education/news/" + quote(str(news_id), safe="") + "/"
    url = request.build_absolute_uri(path)
    title = strip_tags(str(getattr(news, "title", None) or "OppoGlobe News"))[:200]
    text = (
        getattr(news, "summary", None)
        or getattr(news, "description", None)
        or getattr(news, "content", None)
        or "Read the latest education news on OppoGlobe."
    )
    description = " ".join(strip_tags(str(text)).split())[:220]
    image = ""
    for name in ("image_url", "featured_image_url", "featured_image", "image"):
        image = _absolute_http(request, getattr(news, name, None))
        if image:
            break
    properties = [
        ("og:type", "article"),
        ("og:site_name", "OppoGlobe"),
        ("og:title", title),
        ("og:description", description),
        ("og:url", url),
    ]
    if image:
        properties += [("og:image", image), ("og:image:alt", title)]
    tags = format_html_join("\n", '<meta property="{}" content="{}">', properties)
    names = [
        ("description", description),
        ("twitter:card", "summary_large_image" if image else "summary"),
        ("twitter:title", title),
        ("twitter:description", description),
    ]
    if image:
        names.append(("twitter:image", image))
    social = format_html_join("\n", '<meta name="{}" content="{}">', names)
    return format_html('<link rel="canonical" href="{}">\n{}\n{}', url, tags, social)
