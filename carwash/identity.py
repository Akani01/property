"""Public identity helpers for the car-wash UI.

Internal UUIDs remain available to the API, but all user-facing labels should
flow through these helpers so Google/allauth users and profile users are named
consistently across the map, requests, reviews and safety tools.
"""


def _clean(value):
    return str(value or '').strip()


def public_user_name(user):
    """User/applicant: profile first+last -> account first+last -> username."""
    if not user:
        return 'OppoGlobe user'

    # OppoGlobe's applicant profile is the authoritative personal profile when
    # available. Access defensively because not every account has one.
    try:
        profile = getattr(user, 'applicantprofile', None)
    except Exception:
        profile = None

    if profile:
        first = _clean(getattr(profile, 'first_name', ''))
        last = _clean(getattr(profile, 'last_name', ''))
        full = ' '.join(part for part in (first, last) if part)
        if full:
            return full

    first = _clean(getattr(user, 'first_name', ''))
    last = _clean(getattr(user, 'last_name', ''))
    full = ' '.join(part for part in (first, last) if part)
    if full:
        return full

    try:
        username = _clean(user.get_username())
    except Exception:
        username = _clean(getattr(user, 'username', ''))
    return username or 'OppoGlobe user'


def public_business_name(business):
    """Business: business/company name -> Google/account username.

    Do not expose the owner's personal first/last name as the fallback for a
    business identity.
    """
    if not business:
        return 'Car wash business'
    name = _clean(getattr(business, 'name', ''))
    if name:
        return name
    owner = getattr(business, 'owner', None)
    if owner:
        try:
            username = _clean(owner.get_username())
        except Exception:
            username = _clean(getattr(owner, 'username', ''))
        if username:
            return username
    return 'Car wash business'


def public_worker_name(worker):
    """Worker: explicit display name -> profile/account name -> username."""
    if not worker:
        return 'Washer'
    display = _clean(getattr(worker, 'display_name', ''))
    if display:
        return display
    return public_user_name(getattr(worker, 'user', None))
