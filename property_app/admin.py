from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from django.utils.html import format_html

from .models import Location, Property, PropertyImage


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1
    fields = ("image", "preview", "alt_text", "is_primary", "sort_order")
    readonly_fields = ("preview",)

    @admin.display(description="Preview")
    def preview(self, obj):
        if obj.pk and obj.image:
            return format_html(
                '<img src="{}" style="height:60px;border-radius:4px;">',
                obj.image.url,
            )
        return "-"


@admin.register(Location)
class LocationAdmin(GISModelAdmin):
    list_display = ("name", "city", "state", "country", "is_active")
    list_filter = ("country", "state", "is_active")
    search_fields = ("name", "city", "state", "country", "address")
    prepopulated_fields = {"slug": ("name",)}
    exclude = ("embedding",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Property)
class PropertyAdmin(GISModelAdmin):
    list_display = (
        "title",
        "location",
        "price",
        "bedrooms",
        "is_featured",
        "is_active",
    )
    list_filter = ("is_active", "is_featured", "property_type", "status")
    search_fields = ("title", "description", "address", "location__name", "location__city")
    prepopulated_fields = {"slug": ("title",)}
    list_select_related = ("location",)
    autocomplete_fields = ("location",)
    exclude = ("embedding",)
    readonly_fields = ("created_at", "updated_at")
    inlines = [PropertyImageInline]