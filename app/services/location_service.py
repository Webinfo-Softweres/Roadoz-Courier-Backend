import httpx
from app.core.config import settings

async def get_coordinates_from_address(address_string: str):
    """
    Get latitude and longitude from an address string using HERE Geocoding API.
    """
    if not address_string:
        return None
        
    try:
        url = "https://geocode.search.hereapi.com/v1/geocode"
        params = {
            "q": address_string,
            "apikey": settings.HERE_API_KEY,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            
        if response.status_code != 200:
            print(f"HERE Geocoding API Error: {response.status_code} - {response.text}")
            return None
            
        data = response.json()
        items = data.get("items", [])
        
        if not items:
            return None
            
        position = items[0].get("position", {})
        lat = position.get("lat")
        lng = position.get("lng")
        
        if lat is not None and lng is not None:
            return {"lat": float(lat), "lng": float(lng)}
            
        return None
    except Exception as e:
        print(f"HERE Geocoding error: {e}")
        return None

async def get_full_location_from_lat_lng(lat: float, lng: float):
    """
    Get full location details from GPS coordinates using HERE Reverse Geocoding API.
    """
    try:
        url = "https://revgeocode.search.hereapi.com/v1/revgeocode"
        params = {
            "at": f"{lat},{lng}",
            "lang": "en-US",
            "apikey": settings.HERE_API_KEY,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            
        if response.status_code != 200:
            print(f"HERE API Error: {response.status_code} - {response.text}")
            return None
            
        data = response.json()
        items = data.get("items", [])
        
        if not items:
            return None
            
        return items[0]
    except Exception as e:
        print(f"HERE Geocoding error: {e}")
        return None
