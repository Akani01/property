class BaselineCSPMiddleware:
    """Compatible baseline for the supplied inline-script template; not a strict script policy.

    If an upstream policy exists, preserve it. Test a stricter policy separately against
    Google sign-in, payments, media, advertising and the service worker before enforcing it.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.get("Content-Type", "").startswith("text/html"):
            response.setdefault("Content-Security-Policy", "object-src 'none'; base-uri 'self'; frame-ancestors 'self'")
        return response
