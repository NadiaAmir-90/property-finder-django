import pandas as pd
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from django.db import transaction

from property_app.models import (
    Location,
    Property,
    PropertyImage,
)


class Command(BaseCommand):
    help = "Import properties and locations from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str)

    @transaction.atomic
    def handle(self, *args, **options):
        csv_file = options["csv_file"]
        df = pd.read_csv(csv_file)

        # Updated to match your actual CSV columns
        required = {
            "location_slug", "location_name", "country", "state", "city", "location_address",
            "title", "slug", "description", "property_type", "status", "price",
            "bedrooms", "bathrooms", "area_sqft", "address",
            "latitude", "longitude", "is_featured", "is_active", "images"
        }

        missing = required - set(df.columns)
        if missing:
            raise ValueError(
                f"Missing CSV columns: {sorted(missing)}"
            )

        for row in df.to_dict(orient="records"):
            # 1. Get or create Location (safeguarding max lengths)
            location, _ = Location.objects.get_or_create(
                slug=str(row["location_slug"])[:255],
                defaults={
                    "name": str(row["location_name"])[:255],
                    "country": str(row["country"])[:100],
                    "state": str(row["state"])[:100] if pd.notna(row["state"]) else "",
                    "city": str(row["city"])[:100],
                    "address": str(row["location_address"]) if pd.notna(row["location_address"]) else "",
                },
            )

            # 2. Build GeoDjango Point object for the property
            property_point = None
            if pd.notna(row.get("longitude")) and pd.notna(row.get("latitude")):
                property_point = Point(
                    float(row["longitude"]),
                    float(row["latitude"]),
                    srid=4326
                )

            # 3. Create or update Property
            property_obj, created = Property.objects.update_or_create(
                slug=str(row["slug"])[:255],
                defaults={
                    "location": location,
                    "title": str(row["title"])[:255],
                    "description": str(row["description"]) if pd.notna(row["description"]) else "",
                    "property_type": str(row["property_type"])[:50],
                    "status": str(row["status"])[:50],
                    "price": row["price"],
                    "bedrooms": int(row["bedrooms"]),
                    "bathrooms": int(row["bathrooms"]),
                    "area_sqft": row["area_sqft"] if pd.notna(row["area_sqft"]) else None,
                    "address": str(row["address"]) if pd.notna(row["address"]) else "",
                    "point": property_point,
                    "is_featured": bool(row["is_featured"]),
                    "is_active": bool(row["is_active"]),
                },
            )

            # 4. Images ('|' diye alada)
            if pd.notna(row.get("images")):
                image_values = [
                    x.strip() for x in str(row["images"]).split("|") if x.strip()
                ]
                for index, img in enumerate(image_values):
                    PropertyImage.objects.update_or_create(
                        property=property_obj,
                        image=img,
                        defaults={
                            "is_primary": (index == 0),
                            "sort_order": index,
                        },
                    )

        self.stdout.write(
            self.style.SUCCESS("CSV import completed successfully!")
        )