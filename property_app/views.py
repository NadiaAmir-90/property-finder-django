from django.core.paginator import Paginator
from django.db.models import Q, Prefetch
from django.shortcuts import render, get_object_or_404
from django.contrib.gis.db.models.functions import Distance

from .models import Location,Property, PropertyImage

from django.http import JsonResponse
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.contrib.gis.db.models.functions import Distance
from pgvector.django import CosineDistance

from .semantic import embed_text


def published_properties():
    image_queryset = PropertyImage.objects.order_by(
        "-is_primary",
        "sort_order",
        "id",
    )

    return (
        Property.objects
        .filter(is_active=True, status__iexact="published")
        .select_related("location")
        .prefetch_related(
            Prefetch(
                "property_images",
                queryset=image_queryset,
                to_attr="ordered_images",
            )
        )
        .order_by("-is_featured", "-created_at")
    )


def home(request):
    return render(request, "property_app/home.html")


def property_list(request):
    query = request.GET.get("q", "").strip()

    properties = published_properties()

    if query:
        properties = properties.filter(
            Q(title__icontains=query)
            | Q(location__name__icontains=query)
            | Q(location__city__icontains=query)
            | Q(location__state__icontains=query)
            | Q(location__country__icontains=query)
            | Q(location__address__icontains=query)
            | Q(address__icontains=query)
        ).distinct()

    paginator = Paginator(properties, 6)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "property_app/property_list.html",
        {
            "page_obj": page_obj,
            "properties": page_obj.object_list,
            "query": query,
        },
    )


def property_detail(request, slug):
    property_obj = get_object_or_404(
        published_properties(),
        slug=slug,
    )

    if (
        property_obj.point
        and property_obj.location
        and property_obj.location.point
    ):
        property_obj.distance_from_location = (
            Property.objects
            .filter(pk=property_obj.pk)
            .annotate(
                calculated_distance=Distance(
                    "point",
                    "location__point",
                )
            )
            .values_list("calculated_distance", flat=True)
            .first()
        )
    else:
        property_obj.distance_from_location = None
    
    # Find the 6 nearest published properties
    if property_obj.point:
        nearby_properties = (
            published_properties()
            .filter(
                point__isnull=False,
                point__distance_lte=(
                    property_obj.point,
                    D(km=5),
                ),
                
            )
            .exclude(pk=property_obj.pk)
            .annotate(
                distance=Distance(
                    "point",
                    property_obj.point,
                )
            )
            .order_by("distance")[:6]
        )
    else:
        nearby_properties = Property.objects.none()

    return render(
        request,
       "property_app/property_detail.html",
       {
        "property": property_obj,
        "nearby_properties": nearby_properties,
       },
    )




def location_semantic_search(request):
    query = request.GET.get("q", "").strip()

    if not query:
        return JsonResponse(
            {"error": "Query parameter 'q' is required."},
            status=400,
        )

    try:
        query_vector = embed_text(query)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    locations = (
        Location.objects
        .filter(semantic_embedding__isnull=False)
        .annotate(
            semantic_distance=CosineDistance(
                "semantic_embedding",
                query_vector,
            )
        )
        .order_by("semantic_distance")[:10]
    )

    results = [
        {
            "id": location.pk,
            "name": location.name,
            "city": getattr(location, "city", ""),
            "country": getattr(location, "country", ""),
            "similarity": round(
                1 - location.semantic_distance,
                4,
            ),
        }
        for location in locations
    ]

    return JsonResponse({
        "query": query,
        "results": results,
    })


def property_semantic_search(request):
    query = request.GET.get("q", "").strip()

    if not query:
        return JsonResponse(
            {"error": "Query parameter 'q' is required."},
            status=400,
        )

    query_vector = embed_text(query)

    properties = (
        Property.objects
        .filter(
            is_active=True,
            status__iexact="published",
            embedding__isnull=False,
        )
        .annotate(
            semantic_distance=CosineDistance(
                "embedding",
                query_vector,
            )
        )
        .order_by("semantic_distance")[:10]
    )

    results = [
        {
            "id": prop.pk,
            "title": prop.title,
            "slug": prop.slug,
            "similarity": round(
                1 - prop.semantic_distance,
                4,
            ),
        }
        for prop in properties
    ]

    return JsonResponse({
        "query": query,
        "results": results,
    })


def property_hybrid_search(request):
    query = request.GET.get("q", "").strip()
    latitude = request.GET.get("latitude", "").strip()
    longitude = request.GET.get("longitude", "").strip()
    radius_km = request.GET.get("radius_km", "10").strip()

    if not query or not latitude or not longitude:
        return JsonResponse(
            {
                "error": (
                    "Provide q, latitude, and longitude."
                )
            },
            status=400,
        )

    try:
        latitude = float(latitude)
        longitude = float(longitude)
        radius_km = float(radius_km)

        if not (
            -90 <= latitude <= 90
            and -180 <= longitude <= 180
            and 0 < radius_km <= 500
        ):
            raise ValueError("Coordinates or radius out of range.")

        query_vector = embed_text(query)

    except (ValueError, TypeError) as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    user_point = Point(longitude, latitude, srid=4326)

    properties = (
        Property.objects
        .filter(
            is_active=True,
            status__iexact="published",
            embedding__isnull=False,
            point__isnull=False,
            point__distance_lte=(
                user_point,
                D(m=radius_km * 1000),
            ),
        )
        .annotate(
            semantic_distance=CosineDistance(
                "embedding",
                query_vector,
            ),
            geo_distance=Distance("point", user_point),
        )
        .order_by("semantic_distance")[:10]
    )

    results = [
        {
            "id": prop.pk,
            "title": prop.title,
            "slug": prop.slug,
            "similarity": round(
                1 - prop.semantic_distance,
                4,
            ),
            "distance_km": round(prop.geo_distance.km, 2),
        }
        for prop in properties
    ]

    return JsonResponse({
        "query": query,
        "radius_km": radius_km,
        "results": results,
    })
