
from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("properties/", views.property_list, name="property_list"),
    path(
        "locations/search/",
        views.location_semantic_search,
        name="location_semantic_search",
    ),
    path(
        "properties/semantic-search/",
        views.property_semantic_search,
        name="property_semantic_search",
    ),
    path(
        "properties/hybrid-search/",
        views.property_hybrid_search,
        name="property_hybrid_search",
    ),
    path(
        "properties/<slug:slug>/",
        views.property_detail,
        name="property_detail",
    ),

]
