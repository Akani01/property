import json
from urllib.parse import urlsplit
from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_safe
from xml.etree.ElementTree import Element, SubElement, tostring
from .content import GUIDES, GUIDE_BY_SLUG


def origin():
    value = getattr(settings, "OPPO_SEO_ORIGIN", "https://oppoglobe.co.za").rstrip("/")
    parsed = urlsplit(value)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc or parsed.path or parsed.query or parsed.fragment:
        raise ValueError("OPPO_SEO_ORIGIN must be an origin such as https://oppoglobe.co.za")
    return value


def context(title, description, path):
    return {"title": title, "description": description, "canonical": origin() + path,
            "contact_url": getattr(settings, "OPPO_SEO_CONTACT_URL", "/contact/"),
            "privacy_url": getattr(settings, "OPPO_SEO_PRIVACY_URL", "/privacy/")}


@require_safe
def robots(request):
    # robots.txt is crawl guidance, never access control. Do not block assets or API resources used to render pages.
    return HttpResponse("User-agent: *\nAllow: /\n\nSitemap: " + origin() + reverse("oppo_seo:sitemap") + "\n", content_type="text/plain; charset=utf-8")


@require_safe
def ads(request):
    # Publisher ID is copied from the supplied template. Verify ownership in AdSense before deployment.
    return HttpResponse("google.com, pub-5924073395226525, DIRECT, f08c47fec0942fa0\n", content_type="text/plain; charset=utf-8")


@require_safe
def sitemap(request):
    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    root = Element("urlset", xmlns=namespace)
    paths = ["/", reverse("oppo_seo:guides"), reverse("oppo_seo:editorial"), reverse("oppo_seo:cookies")]
    paths += [reverse("oppo_seo:guide", args=[g["slug"]]) for g in GUIDES]
    # Only include working canonical public HTML pages; never list API endpoints or invented news URLs.
    for path in paths:
        node = SubElement(root, "url")
        SubElement(node, "loc").text = origin() + path
    return HttpResponse(tostring(root, encoding="utf-8", xml_declaration=True), content_type="application/xml; charset=utf-8")


@require_safe
def guides(request):
    data = context("Education guides for South African learners | OppoGlobe", "Practical guides to bursary applications, NSFAS safety, course choices, admission points and exam revision.", reverse("oppo_seo:guides"))
    data["guides"] = GUIDES
    return render(request, "oppo_seo/guides.html", data)


@require_safe
def guide(request, slug):
    article = GUIDE_BY_SLUG.get(slug)
    if article is None:
        raise Http404("Guide not found")
    data = context(article["title"] + " | OppoGlobe", article["summary"], reverse("oppo_seo:guide", args=[slug]))
    data["guide"] = article
    data["related"] = [g for g in GUIDES if g["slug"] != slug][:3]
    schema = {"@context": "https://schema.org", "@type": "Article", "headline": article["title"],
              "description": article["summary"], "mainEntityOfPage": data["canonical"],
              "datePublished": article["date"], "inLanguage": "en-ZA",
              "publisher": {"@type": "Organization", "name": "OppoGlobe", "url": origin()}}
    data["schema"] = json.dumps(schema, ensure_ascii=False).replace("<", "\\u003c")
    return render(request, "oppo_seo/guide.html", data)


@require_safe
def editorial(request):
    return render(request, "oppo_seo/editorial.html", context("About these education guides | OppoGlobe", "Scope, sources and corrections for the practical education guides on OppoGlobe.", reverse("oppo_seo:editorial")))


@require_safe
def cookies(request):
    return render(request, "oppo_seo/cookies.html", context("Cookie preferences | OppoGlobe", "Manage the optional cookie preference stored by this site template and read about third-party services.", reverse("oppo_seo:cookies")))
