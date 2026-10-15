from django.urls import path
from . import views
app_name = "oppo_seo"
urlpatterns = [
    path("robots.txt", views.robots, name="robots"),
    path("sitemap.xml", views.sitemap, name="sitemap"),
    path("ads.txt", views.ads, name="ads"),
    path("education/guides/", views.guides, name="guides"),
    path("education/guides/<slug:slug>/", views.guide, name="guide"),
    path("education/editorial/", views.editorial, name="editorial"),
    path("site-cookies/", views.cookies, name="cookies"),
]
