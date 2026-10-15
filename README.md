# Property Finder — Django, GeoDjango, PostGIS & pgvector
A property management and discovery API built with Django, Django REST Framework (DRF), GeoDjango, PostgreSQL/PostGIS, and `pgvector`. Docker Compose runs the database, while `uv` manages the Python environment and dependencies.

## Setup and Run the Project

```bash
git clone https://github.com/NadiaAmir-90/property-finder-django
cd property-finder-django
chmod +x run.sh
./run.sh
```
## API testing

Check the server:
```bash
# Property list
curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:8000/properties/"

# New York search
curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:8000/properties/?q=New%20York"

# New York property detail
curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:8000/properties/new-york-grand-hotel-0001/"

# Other property details
curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:8000/properties/jersey-city-grand-villa-0025/"
curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:8000/properties/brisbane-central-resort-0011/"

# Pagination
curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:8000/properties/?page=2"

# Location semantic search
curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:8000/locations/search/?q=New%20York"

# Property semantic search
curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:8000/properties/semantic-search/?q=luxury%20hotel%20in%20New%20York"

# Property hybrid search

BASE="http://127.0.0.1:8000/properties/hybrid-search/"

for url in \
  "?q=luxury%20hotel&latitude=40.7171115&longitude=-74.0244963&radius_km=10" \
  "?q=villa&latitude=40.7146727&longitude=-74.066361&radius_km=10" \
  "?q=resort&latitude=-27.4730696&longitude=153.0041461&radius_km=10" \
  "?q=house&latitude=34.7074277&longitude=135.4749562&radius_km=10" \
  "?q=resort&latitude=48.8703272&longitude=2.3583824&radius_km=10" \
  "?q=apartment&latitude=52.5098345&longitude=13.4312977&radius_km=10" \
  "?q=hostel&latitude=43.7034051&longitude=7.277543&radius_km=10"; do
  resp=$(curl -s "$BASE$url")
  count=$(echo "$resp" | python3 -c "import sys,json; print(len(json.load(sys.stdin)['results']))")
  echo "results=$count  $url"
done

```

## Features

The project is designed to cover these areas:

### Location management
- Country, state/region, and city hierarchy.
- Geographic coordinates and administrative boundaries.
- Spatial database fields and indexes.
- Location-based filtering.

### Property management
- Property listing details, location, pricing, and metadata.
- Property footprints represented as geographic polygons, where required.
- Property images, including an optional featured image.

### Spatial search
- Radius-based search.
- Nearest-property search.
- Distance calculations 

### Semantic search
- Text or image embeddings stored as vectors.
- Similarity search using `pgvector`.
- Hybrid ranking that combines geographic conditions and vector similarity.


## Technology stack

| Technology | Purpose |
|---|---|
| Python | Application language |
| Django | Web framework, models, admin, and migrations |
| Django REST Framework | REST API tools such as serializers and API views |
| GeoDjango | Geographic model fields and spatial ORM queries |
| PostgreSQL | Relational database |
| PostGIS | Geographic types, spatial functions, and indexes |
| `pgvector` | Vector storage and similarity operations in PostgreSQL |
| Docker Compose | Runs the database service in a container |
| `uv` | Python dependency and virtual-environment management |


## Production notes

Before production use:

- Set `DEBUG = False`.
- Configure `ALLOWED_HOSTS` and HTTPS correctly.
- Keep secrets outside source control.
- Use a production-grade WSGI/ASGI server rather than Django's development server.
- Use persistent database storage and backups.
- Configure durable media storage.
- Review authentication, authorization, input validation, and upload security.
- Add tests for API validation, spatial queries, and vector ranking.
- Review database indexes and query performance.
- Apply migrations as a controlled deployment step.
- Monitor logs and errors without logging credentials or sensitive data.

## License

This project was developed as part of the **W3 Engineers Ltd Internship Assignment-06**.