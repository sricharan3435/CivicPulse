from threading import Lock
from time import monotonic
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/geocode", tags=["location search"])
_CACHE = {}
_LOCK = Lock()
_LAST_REQUEST_AT = 0.0


@router.get("/search")
def search_places(q: str = Query(min_length=3, max_length=120)):
    """Search a place only when the user submits the search form."""
    global _LAST_REQUEST_AT
    normalized = " ".join(q.split()).casefold()
    with _LOCK:
        if normalized in _CACHE:
            return {"results": _CACHE[normalized]}
        now = monotonic()
        if now - _LAST_REQUEST_AT < 1.0:
            raise HTTPException(status_code=429, detail="Please wait a moment before searching again")
        _LAST_REQUEST_AT = now

    params = urlencode({"q": q.strip(), "format": "jsonv2", "limit": 5, "addressdetails": 0})
    request = Request(
        f"https://nominatim.openstreetmap.org/search?{params}",
        headers={"User-Agent": "CivicPulse/1.0 (community civic issue reporting)", "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=8) as response:
            places = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise HTTPException(status_code=503, detail="Location search is temporarily unavailable") from exc
    except (URLError, TimeoutError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Could not reach the OpenStreetMap location search") from exc

    results = [{
        "name": place.get("display_name", "Place"),
        "latitude": float(place["lat"]),
        "longitude": float(place["lon"]),
    } for place in places if "lat" in place and "lon" in place]
    with _LOCK:
        if len(_CACHE) >= 128:
            _CACHE.pop(next(iter(_CACHE)))
        _CACHE[normalized] = results
    return {"results": results}
