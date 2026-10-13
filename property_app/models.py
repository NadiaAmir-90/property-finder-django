
from django.db import models
from django.contrib.gis.db import models as gis_models
from pgvector.django import VectorField, HnswIndex

class Location(models.Model):
    name = models.CharField(max_length=255)

    slug = models.SlugField(unique=True)

    country = models.CharField(max_length=100)

    state = models.CharField(
        max_length=100,
        blank=True,
    )

    city = models.CharField(max_length=100)

    address = models.TextField(blank=True)

    point = gis_models.PointField(
        geography=True,
        srid=4326,
        null=True,
        blank=True,
    )

    boundary = gis_models.MultiPolygonField(
        srid=4326,
        null=True,
        blank=True,
    )

    embedding = VectorField(
        dimensions=1536,
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return self.name


