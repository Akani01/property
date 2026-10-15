import gzip
import json
from xml.etree import ElementTree
from django.http import HttpResponse
from django.test import SimpleTestCase, override_settings
from django.urls import include, path
from .content import GUIDES

urlpatterns = [path('', include('oppo_seo.urls')), path('', lambda request: HttpResponse('Home'))]

@override_settings(ROOT_URLCONF=__name__, ALLOWED_HOSTS=['testserver'], OPPO_SEO_ORIGIN='https://oppoglobe.co.za')
class PublicSeoTests(SimpleTestCase):
    def test_public_guides_contain_full_text_and_metadata(self):
        for guide in GUIDES:
            response = self.client.get('/education/guides/' + guide['slug'] + '/')
            self.assertEqual(response.status_code, 200)
            html = response.content.decode()
            self.assertEqual(html.count('<h1>'), 1)
            self.assertIn('<meta name="description"', html)
            self.assertIn('<link rel="canonical"', html)
            for section in guide['sections']:
                self.assertIn(section['title'], html)
            start = html.index('<script type="application/ld+json">') + len('<script type="application/ld+json">')
            schema = json.loads(html[start:html.index('</script>', start)])
            self.assertEqual(schema['@type'], 'Article')
            self.assertEqual(schema['headline'], guide['title'])
            self.assertNotIn('pagead2.googlesyndication.com', html)

    def test_unknown_guide_is_404(self):
        self.assertEqual(self.client.get('/education/guides/no-such-guide/').status_code, 404)

    def test_sitemap_urls_exist_and_are_https(self):
        response = self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/xml', response['Content-Type'])
        tree = ElementTree.fromstring(response.content)
        urls = [node.text for node in tree.findall('.//{*}loc')]
        self.assertEqual(len(urls), 10)
        self.assertEqual(len(urls), len(set(urls)))
        for url in urls:
            self.assertTrue(url.startswith('https://oppoglobe.co.za/'))
            self.assertEqual(self.client.get(url.removeprefix('https://oppoglobe.co.za')).status_code, 200)

    def test_robots_allows_public_content(self):
        response = self.client.get('/robots.txt')
        self.assertContains(response, 'Allow: /')
        self.assertContains(response, 'Sitemap: https://oppoglobe.co.za/sitemap.xml')
        self.assertNotContains(response, 'Disallow: /')
        self.assertIn('text/plain', response['Content-Type'])

    def test_ads_txt_matches_supplied_account(self):
        response = self.client.get('/ads.txt')
        self.assertContains(response, 'pub-5924073395226525, DIRECT, f08c47fec0942fa0')
        self.assertIn('text/plain', response['Content-Type'])

    def test_post_is_not_allowed_on_crawl_endpoints(self):
        for url in ['/robots.txt', '/sitemap.xml', '/ads.txt']:
            self.assertEqual(self.client.post(url).status_code, 405)

    @override_settings(MIDDLEWARE=['django.middleware.gzip.GZipMiddleware', 'oppo_seo.middleware.BaselineCSPMiddleware'])
    def test_html_compression_and_baseline_csp(self):
        response = self.client.get('/education/guides/', HTTP_ACCEPT_ENCODING='gzip')
        self.assertEqual(response['Content-Encoding'], 'gzip')
        self.assertIn('frame-ancestors', response['Content-Security-Policy'])
        self.assertIn(b'<h1>', gzip.decompress(response.content))
        self.assertIn('Accept-Encoding', response['Vary'])

    def test_csp_preserves_existing_policy(self):
        from .middleware import BaselineCSPMiddleware
        response = HttpResponse('<h1>Example</h1>')
        response['Content-Security-Policy'] = "default-src 'self'"
        middleware = BaselineCSPMiddleware(lambda request: response)
        self.assertEqual(middleware(None)['Content-Security-Policy'], "default-src 'self'")
