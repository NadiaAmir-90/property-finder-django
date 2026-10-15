
from django.core.management.base import BaseCommand

from property_app.models import Location, Property
from property_app.semantic import embed_text


def value(obj, field):
    return str(getattr(obj, field, "") or "").strip()


def location_text(location):
    parts = [
        value(location, "name"),
        value(location, "city"),
        value(location, "state"),
        value(location, "country"),
        value(location, "address"),
    ]
    return " | ".join(part for part in parts if part)


def property_text(prop):
    location = prop.location

    parts = [
        value(prop, "title"),
        value(prop, "description"),
        value(prop, "property_type"),
        value(prop, "address"),
    ]

    if location:
        parts.append(location_text(location))

    return " | ".join(part for part in parts if part)


class Command(BaseCommand):
    help = "Generate semantic embeddings for locations and properties"

    def handle(self, *args, **options):
        locations_updated = 0
        properties_updated = 0
        errors = 0

        for location in Location.objects.all().iterator():
            text = location_text(location)

            if not text:
                continue

            try:
                location.semantic_embedding = embed_text(text)
                location.save(update_fields=["semantic_embedding"])
                locations_updated += 1
            except Exception as exc:
                errors += 1
                self.stderr.write(
                    f"Location {location.pk}: {exc}"
                )

        for prop in Property.objects.select_related("location").iterator():
            text = property_text(prop)

            if not text:
                continue

            try:
                prop.embedding = embed_text(text)
                prop.save(update_fields=["embedding"])
                properties_updated += 1
            except Exception as exc:
                errors += 1
                self.stderr.write(
                    f"Property {prop.pk}: {exc}"
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Locations updated: {locations_updated}; "
                f"properties updated: {properties_updated}; "
                f"errors: {errors}"
            )
        )

