
import pandas as pd

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from property_app.models import (
    Location,
    Property,
    PropertyImage,
)


def clean_text(value, default=""):
    """Convert a CSV value to a clean string."""
    if pd.isna(value):
        return default

    return str(value).strip()


def parse_bool(value, default=False):
    """Parse CSV boolean values safely."""
    if pd.isna(value):
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return value != 0

    value = str(value).strip().lower()

    if value in {"true", "1", "yes", "y"}:
        return True

    if value in {"false", "0", "no", "n"}:
        return False

    raise ValueError(f"Invalid boolean value: {value!r}")


def parse_optional_float(value):
    """Return a float or None for an empty CSV value."""
    if pd.isna(value) or str(value).strip() == "":
        return None

    return float(value)


def parse_optional_int(value):
    """Return an integer or None for an empty CSV value."""
    number = parse_optional_float(value)

    if number is None:
        return None

    if not number.is_integer():
        raise ValueError(f"Expected an integer, got: {value!r}")

    return int(number)


class Command(BaseCommand):
    help = (
        "Import and synchronize locations, properties, "
        "and property images from a CSV file."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file",
            type=str,
            help="Path to the properties CSV file.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        csv_file = options["csv_file"]

        # 1. Read the CSV file
        try:
            df = pd.read_csv(csv_file)
        except (OSError, UnicodeError, pd.errors.ParserError) as exc:
            raise CommandError(
                f"Could not read CSV file {csv_file!r}: {exc}"
            ) from exc

        # 2. Validate required columns
        required = {
            "location_slug",
            "location_name",
            "country",
            "state",
            "city",
            "location_address",
            "title",
            "slug",
            "description",
            "property_type",
            "status",
            "price",
            "bedrooms",
            "bathrooms",
            "area_sqft",
            "address",
            "latitude",
            "longitude",
            "is_featured",
            "is_active",
            "images",
        }

        missing = required - set(df.columns)

        if missing:
            raise CommandError(
                f"Missing CSV columns: {sorted(missing)}"
            )

        # Prevent accidental full synchronization from an empty file.
        if df.empty:
            raise CommandError(
                "The CSV file contains no property rows. "
                "Import cancelled."
            )

        created_properties = 0
        updated_properties = 0
        created_locations = 0
        updated_locations = 0
        synced_image_records = 0

        # 3. Process every CSV row in one database transaction
        for row_number, row in enumerate(
            df.to_dict(orient="records"),
            start=2,
        ):
            try:
                location_slug = clean_text(
                    row["location_slug"]
                )

                property_slug = clean_text(row["slug"])

                if not location_slug:
                    raise ValueError("location_slug is empty")

                if not property_slug:
                    raise ValueError("slug is empty")

                # 4. Create or update the Location
                location_defaults = {
                    "name": clean_text(row["location_name"])[:255],
                    "country": clean_text(row["country"])[:100],
                    "state": clean_text(row["state"])[:100],
                    "city": clean_text(row["city"])[:100],
                    "address": clean_text(row["location_address"]),
                }

                location, location_created = (
                    Location.objects.update_or_create(
                        slug=location_slug[:255],
                        defaults=location_defaults,
                    )
                )

                if location_created:
                    created_locations += 1
                else:
                    updated_locations += 1

                # 5. Build the geographic point
                latitude = parse_optional_float(row["latitude"])
                longitude = parse_optional_float(row["longitude"])

                property_point = None

                if latitude is not None and longitude is not None:
                    if not -90 <= latitude <= 90:
                        raise ValueError(
                            f"Invalid latitude: {latitude}"
                        )

                    if not -180 <= longitude <= 180:
                        raise ValueError(
                            f"Invalid longitude: {longitude}"
                        )

                    # GeoDjango Point uses longitude first.
                    property_point = Point(
                        longitude,
                        latitude,
                        srid=4326,
                    )

                # 6. Prepare property fields
                property_defaults = {
                    "location": location,
                    "title": clean_text(row["title"])[:255],
                    "description": clean_text(row["description"]),
                    "property_type": clean_text(
                        row["property_type"]
                    )[:50],
                    "status": clean_text(row["status"])[:50],
                    "price": row["price"],
                    "bedrooms": parse_optional_int(row["bedrooms"]),
                    "bathrooms": parse_optional_int(row["bathrooms"]),
                    "area_sqft": parse_optional_float(
                        row["area_sqft"]
                    ),
                    "address": clean_text(row["address"]),
                    "point": property_point,
                    "is_featured": parse_bool(row["is_featured"]),
                    "is_active": parse_bool(row["is_active"]),
                }

                # 7. Create or update the property by slug
                property_obj, property_created = (
                    Property.objects.update_or_create(
                        slug=property_slug[:255],
                        defaults=property_defaults,
                    )
                )

                if property_created:
                    created_properties += 1
                else:
                    updated_properties += 1

                # 8. Parse the image URLs separated by "|"
                raw_images = row["images"]

                image_values = []

                if pd.notna(raw_images):
                    image_values = [
                        image_url.strip()
                        for image_url in str(raw_images).split("|")
                        if image_url.strip()
                    ]

                # 9. Synchronize images with the CSV.
                # CSV is treated as the complete image list.
                PropertyImage.objects.filter(
                    property=property_obj
                ).delete()

                for index, image_url in enumerate(image_values):
                    PropertyImage.objects.create(
                        property=property_obj,
                        image=image_url,
                        is_primary=(index == 0),
                        sort_order=index,
                    )

                synced_image_records += len(image_values)

            except Exception as exc:
                raise CommandError(
                    f"Import failed at CSV row {row_number}: {exc}"
                ) from exc

        # 10. Print import summary
        self.stdout.write(
            self.style.SUCCESS(
                "CSV import and image synchronization completed!"
            )
        )

        self.stdout.write(f"Locations created: {created_locations}")
        self.stdout.write(f"Locations updated: {updated_locations}")
        self.stdout.write(f"Properties created: {created_properties}")
        self.stdout.write(f"Properties updated: {updated_properties}")
        self.stdout.write(
            f"Image records synchronized: {synced_image_records}"
        )