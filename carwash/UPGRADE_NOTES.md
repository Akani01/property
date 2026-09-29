# OppoGlobe Car Wash live-map upgrade

This package keeps the existing 15% commission and upgrades the car-wash app around live state, public identity and safety.

## Database change

A new `CarWashSafetyReport` model was added. Run:

```bash
python manage.py makemigrations carwash
python manage.py migrate
```

## What changed

- Consistent public names: customer profile name -> account/Google username fallback; business name -> account/Google username fallback; worker display name -> profile name -> username.
- Fresh live provider discovery: mobile providers disappear from discovery if their GPS is older than two minutes.
- Worker GPS state now reports live/reconnecting/offline.
- Mobile jobs cannot be accepted unless the worker has fresh live GPS.
- Customer/provider status permissions are tightened so a customer cannot mark a wash accepted/washing/completed.
- Map markers are HTML overlays with clear labels, smooth movement, status styling, and washing bubbles.
- Customer marker clearly says "You are here".
- Active tracking redraws the driving route without hammering Google Directions on every GPS tick.
- Nearby providers, requests, workers, dashboard totals and payments refresh automatically without a full browser reload.
- GET API requests use cache-busting + `no-store` to reduce stale PWA/browser responses.
- Safety centre includes 10111, 112, nearest police, navigation, GPS copy and an internal OppoGlobe incident report.
- The map page polls OppoGlobe alerts every 15 seconds and plays `/static/hiring/audio/notification.mp3` for a new alert after the initial sync.

## Optional cross-page notification sound

`static/carwash/js/oppoglobe_live_alerts.js` is included as a reusable helper. Add it to your shared OppoGlobe base template if you want the same 15-second alert sound on every open page:

```django
{% load static %}
<script src="{% static 'carwash/js/oppoglobe_live_alerts.js' %}"></script>
```

A browser cannot reliably autoplay a custom MP3 after the PWA/browser has been completely closed. Closed-app alerts still require Web Push / service-worker OS notifications.

## Service worker

The uploaded ZIP did not contain the project's `sw.js`, so this package cannot change its caching rules. The car-wash API wrapper now adds cache-busting/no-store requests, but the shared service worker should still be checked later to ensure `/carwash/api/`, `/api/alerts/` and `/api/conversations/` are network-first or network-only.
