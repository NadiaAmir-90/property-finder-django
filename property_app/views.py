from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.contrib.gis.db.models.functions import Distance

from .forms import PropertySearchForm
from .models import Property


def home(request):
    form = PropertySearchForm(request.GET or None)

    return render(
        request,
        "property_app/home.html",
        {"form": form},
    )


def property_list(request):
    form = PropertySearchForm(request.GET or None)

    # properties = (
    #     Property.objects
    #     .filter(is_active=False, status__iexact="published")
    #     .select_related("location")
    #     .prefetch_related("images")
    #     .order_by("-is_featured", "-created_at")

    # )

    properties = Property.objects.all()

    if form.is_valid():
        city = form.cleaned_data.get("city")
        keyword = form.cleaned_data.get("keyword")
        min_price = form.cleaned_data.get("min_price")
        max_price = form.cleaned_data.get("max_price")
        bedrooms = form.cleaned_data.get("bedrooms")
        property_type = form.cleaned_data.get("property_type")

        if city:
            properties = properties.filter(
                Q(location__city__icontains=city)
                | Q(location__name__icontains=city)
            )

        if keyword:
            properties = properties.filter(
                Q(title__icontains=keyword)
                | Q(description__icontains=keyword)
                | Q(location__city__icontains=keyword)
                | Q(address__icontains=keyword)
            )

        if min_price is not None:
            properties = properties.filter(price__gte=min_price)

        if max_price is not None:
            properties = properties.filter(price__lte=max_price)

        if bedrooms is not None:
            properties = properties.filter(
                bedrooms__gte=bedrooms
            )

        if property_type:
            properties = properties.filter(
                property_type__icontains=property_type
            )

    paginator = Paginator(properties, 2)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "property_app/property_list.html",
        {
            "form": form,
            "page_obj": page_obj,
        },
    )


def property_detail(request, slug):
    property_obj = get_object_or_404(
        Property.objects
        .filter(is_active=True)
        .select_related("location")
        # .prefetch_related("images")
        .annotate(
            distance_from_location=Distance(
                "point",
                "location__point",
            )
        ),
        slug=slug,
    )

    return render(
        request,
        "property_app/property_detail.html",
        {"property": property_obj},
    )
