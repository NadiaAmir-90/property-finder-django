from unittest.mock import patch

from django.contrib.gis.geos import Point
from django.test import TestCase
from django.urls import reverse

from .models import Location, Property

DIMS = 384

# New York Grand Hotel and Jersey City Grand Villa are ~3.5 km apart.
NEW_YORK = (40.7171115, -74.0244963)      # (lat, lng)
JERSEY_CITY = (40.7146727, -74.066361)
BRISBANE = (-27.4730696, 153.0041461)


def vec(*head):
    """384-dim vector whose first values are `head`, rest zeros."""
    return list(head) + [0.0] * (DIMS - len(head))


def make_property(slug, lat, lng, embedding, **overrides):
    location, _ = Location.objects.get_or_create(
        slug=f"loc-{slug}",
        defaults={"name": slug, "country": "Test", "city": slug},
    )
    data = {
        "location": location,
        "title": slug.replace("-", " ").title(),
        "slug": slug,
        "property_type": "Hotel",
        "status": "published",
        "price": "100.00",
        "is_active": True,
        "point": Point(lng, lat, srid=4326),
        "embedding": embedding,
    }
    data.update(overrides)
    return Property.objects.create(**data)


class HybridSearchBase(TestCase):
    url = None

    def setUp(self):
        self.url = reverse("property_hybrid_search")
        # Every query is embedded as [1, 0, 0, ...]
        patcher = patch("property_app.views.embed_text", return_value=vec(1.0))
        self.mock_embed = patcher.start()
        self.addCleanup(patcher.stop)

    def search(self, **params):
        return self.client.get(self.url, params)


class HybridSearchValidationTests(HybridSearchBase):
    def test_missing_all_params_returns_400(self):
        self.assertEqual(self.client.get(self.url).status_code, 400)

    def test_missing_query_returns_400(self):
        r = self.search(latitude=40.7, longitude=-74.0)
        self.assertEqual(r.status_code, 400)
        self.assertIn("error", r.json())

    def test_missing_latitude_returns_400(self):
        r = self.search(q="hotel", longitude=-74.0)
        self.assertEqual(r.status_code, 400)

    def test_missing_longitude_returns_400(self):
        r = self.search(q="hotel", latitude=40.7)
        self.assertEqual(r.status_code, 400)

    def test_blank_query_returns_400(self):
        r = self.search(q="   ", latitude=40.7, longitude=-74.0)
        self.assertEqual(r.status_code, 400)

    def test_non_numeric_coordinates_return_400(self):
        r = self.search(q="hotel", latitude="abc", longitude="xyz")
        self.assertEqual(r.status_code, 400)

    def test_latitude_out_of_range_returns_400(self):
        r = self.search(q="hotel", latitude=91, longitude=0)
        self.assertEqual(r.status_code, 400)

    def test_longitude_out_of_range_returns_400(self):
        r = self.search(q="hotel", latitude=0, longitude=181)
        self.assertEqual(r.status_code, 400)

    def test_zero_radius_returns_400(self):
        r = self.search(q="hotel", latitude=40.7, longitude=-74.0, radius_km=0)
        self.assertEqual(r.status_code, 400)

    def test_negative_radius_returns_400(self):
        r = self.search(q="hotel", latitude=40.7, longitude=-74.0, radius_km=-5)
        self.assertEqual(r.status_code, 400)

    def test_radius_above_500_returns_400(self):
        r = self.search(q="hotel", latitude=40.7, longitude=-74.0, radius_km=501)
        self.assertEqual(r.status_code, 400)

    def test_non_numeric_radius_returns_400(self):
        r = self.search(q="hotel", latitude=40.7, longitude=-74.0, radius_km="far")
        self.assertEqual(r.status_code, 400)

    def test_embedding_failure_returns_400(self):
        self.mock_embed.side_effect = ValueError("embedding failed")
        r = self.search(q="hotel", latitude=40.7, longitude=-74.0)
        self.assertEqual(r.status_code, 400)
        self.assertIn("embedding failed", r.json()["error"])

    def test_valid_request_returns_200_with_expected_shape(self):
        r = self.search(q="hotel", latitude=40.7, longitude=-74.0)
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["query"], "hotel")
        self.assertEqual(body["radius_km"], 10.0)
        self.assertEqual(body["results"], [])

    def test_default_radius_is_10_km(self):
        r = self.search(q="hotel", latitude=40.7, longitude=-74.0)
        self.assertEqual(r.json()["radius_km"], 10.0)

    def test_query_is_embedded(self):
        self.search(q="luxury hotel", latitude=40.7, longitude=-74.0)
        self.mock_embed.assert_called_once_with("luxury hotel")


class HybridSearchSpatialTests(HybridSearchBase):
    def setUp(self):
        super().setUp()
        self.ny = make_property("new-york-hotel", *NEW_YORK, embedding=vec(1.0))
        self.jc = make_property("jersey-city-villa", *JERSEY_CITY, embedding=vec(1.0))
        self.bris = make_property("brisbane-resort", *BRISBANE, embedding=vec(1.0))

    def slugs(self, response):
        return {item["slug"] for item in response.json()["results"]}

    def test_includes_properties_inside_radius(self):
        r = self.search(q="hotel", latitude=NEW_YORK[0], longitude=NEW_YORK[1], radius_km=10)
        self.assertEqual(self.slugs(r), {"new-york-hotel", "jersey-city-villa"})

    def test_excludes_properties_outside_radius(self):
        r = self.search(q="hotel", latitude=NEW_YORK[0], longitude=NEW_YORK[1], radius_km=10)
        self.assertNotIn("brisbane-resort", self.slugs(r))

    def test_small_radius_excludes_nearby_city(self):
        # Jersey City is ~3.5 km away, so a 1 km radius keeps only New York.
        r = self.search(q="hotel", latitude=NEW_YORK[0], longitude=NEW_YORK[1], radius_km=1)
        self.assertEqual(self.slugs(r), {"new-york-hotel"})

    def test_large_radius_still_excludes_other_continent(self):
        r = self.search(q="hotel", latitude=NEW_YORK[0], longitude=NEW_YORK[1], radius_km=500)
        self.assertEqual(self.slugs(r), {"new-york-hotel", "jersey-city-villa"})

    def test_search_near_brisbane_returns_only_brisbane(self):
        r = self.search(q="resort", latitude=BRISBANE[0], longitude=BRISBANE[1], radius_km=10)
        self.assertEqual(self.slugs(r), {"brisbane-resort"})

    def test_distance_km_is_reported(self):
        r = self.search(q="hotel", latitude=NEW_YORK[0], longitude=NEW_YORK[1], radius_km=10)
        by_slug = {i["slug"]: i for i in r.json()["results"]}
        self.assertAlmostEqual(by_slug["new-york-hotel"]["distance_km"], 0.0, places=1)
        self.assertAlmostEqual(by_slug["jersey-city-villa"]["distance_km"], 3.5, delta=0.3)

    def test_draft_property_is_excluded(self):
        self.jc.status = "draft"
        self.jc.save()
        r = self.search(q="hotel", latitude=NEW_YORK[0], longitude=NEW_YORK[1])
        self.assertEqual(self.slugs(r), {"new-york-hotel"})

    def test_status_match_is_case_insensitive(self):
        self.jc.status = "PUBLISHED"
        self.jc.save()
        r = self.search(q="hotel", latitude=NEW_YORK[0], longitude=NEW_YORK[1])
        self.assertIn("jersey-city-villa", self.slugs(r))

    def test_inactive_property_is_excluded(self):
        self.jc.is_active = False
        self.jc.save()
        r = self.search(q="hotel", latitude=NEW_YORK[0], longitude=NEW_YORK[1])
        self.assertEqual(self.slugs(r), {"new-york-hotel"})

    def test_property_without_point_is_excluded(self):
        make_property("no-point", *NEW_YORK, embedding=vec(1.0), point=None)
        r = self.search(q="hotel", latitude=NEW_YORK[0], longitude=NEW_YORK[1])
        self.assertNotIn("no-point", self.slugs(r))

    def test_property_without_embedding_is_excluded(self):
        make_property("no-embedding", *NEW_YORK, embedding=None)
        r = self.search(q="hotel", latitude=NEW_YORK[0], longitude=NEW_YORK[1])
        self.assertNotIn("no-embedding", self.slugs(r))

    def test_no_properties_in_radius_returns_empty_list(self):
        r = self.search(q="hotel", latitude=0, longitude=0, radius_km=10)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["results"], [])


class HybridSearchVectorRankingTests(HybridSearchBase):
    """All properties sit at the same spot; only the embedding differs."""

    def setUp(self):
        super().setUp()
        lat, lng = NEW_YORK
        # Query vector is [1, 0, ...] (see HybridSearchBase.setUp).
        self.exact = make_property("exact-match", lat, lng, vec(1.0, 0.0))     # cosine sim 1.0
        self.partial = make_property("partial-match", lat, lng, vec(1.0, 1.0)) # cosine sim ~0.7071
        self.orthogonal = make_property("orthogonal", lat, lng, vec(0.0, 1.0)) # cosine sim 0.0

    def results(self):
        r = self.search(q="hotel", latitude=NEW_YORK[0], longitude=NEW_YORK[1])
        self.assertEqual(r.status_code, 200)
        return r.json()["results"]

    def test_results_are_ordered_by_similarity_desc(self):
        slugs = [i["slug"] for i in self.results()]
        self.assertEqual(slugs, ["exact-match", "partial-match", "orthogonal"])

    def test_similarity_values(self):
        sims = {i["slug"]: i["similarity"] for i in self.results()}
        self.assertAlmostEqual(sims["exact-match"], 1.0, places=3)
        self.assertAlmostEqual(sims["partial-match"], 0.7071, places=3)
        self.assertAlmostEqual(sims["orthogonal"], 0.0, places=3)

    def test_similarity_is_non_increasing(self):
        sims = [i["similarity"] for i in self.results()]
        self.assertEqual(sims, sorted(sims, reverse=True))

    def test_different_query_vector_changes_ranking(self):
        self.mock_embed.return_value = vec(0.0, 1.0)
        slugs = [i["slug"] for i in self.results()]
        self.assertEqual(slugs[0], "orthogonal")
        self.assertEqual(slugs[-1], "exact-match")

    def test_ranking_ignores_distance_when_inside_radius(self):
        # Closer property with a worse embedding must rank below a farther, better one.
        far_lat, far_lng = JERSEY_CITY
        make_property("far-but-best", far_lat, far_lng, vec(1.0, 0.0))
        slugs = [i["slug"] for i in self.results()]
        self.assertLess(slugs.index("far-but-best"), slugs.index("orthogonal"))

    def test_results_capped_at_10(self):
        lat, lng = NEW_YORK
        for i in range(12):
            make_property(f"extra-{i}", lat, lng, vec(1.0, 0.1 * i))
        self.assertEqual(len(self.results()), 10)