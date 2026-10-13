
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


class Property(models.Model):
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="properties",
    )

    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    property_type = models.CharField(max_length=50)
    status = models.CharField(
        max_length=50,
        default="available",
    )

    price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )
    bedrooms = models.PositiveSmallIntegerField(default=0)
    bathrooms = models.PositiveSmallIntegerField(default=0)
    area_sqft = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    address = models.TextField(blank=True)

    point = gis_models.PointField(
        geography=True,
        srid=4326,
        null=True,
        blank=True,
    )
    footprint = gis_models.PolygonField(
        srid=4326,
        null=True,
        blank=True,
    )

    embedding = VectorField(
        dimensions=384,
        null=True,
        blank=True,
    )

    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class Meta:
    indexes = [
        HnswIndex(
            name="property_embedding_hnsw",
            fields=["embedding"],
            m=16,
            ef_construction=64,
            opclasses=["vector_cosine_ops"],
        ),
    ]

#property_image_model
class PropertyImage(models.Model):
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="images",
    )

    image = models.ImageField(
        upload_to="properties/%Y/%m/",
        max_length=500,
    )
    alt_text = models.CharField(
        max_length=255,
        blank=True,
    )
    caption = models.TextField(blank=True)

    width = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    height = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    file_size = models.BigIntegerField(
        null=True,
        blank=True,
    )

    # Future image embeddings can use a matching
    # 512-dimensional CLIP-compatible model.
    embedding = VectorField(
        dimensions=512,
        null=True,
        blank=True,
    )

    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.property.title}"


