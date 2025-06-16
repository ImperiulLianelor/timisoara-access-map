"""
Geospatial utility functions for the accessibility map.
"""
from flask import current_app
import math
from functools import lru_cache
import requests
import json


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees).
    
    Args:
        lat1, lon1: Coordinates of first point
        lat2, lon2: Coordinates of second point
        
    Returns:
        float: Distance in kilometers
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # Radius of earth in kilometers
    
    return c * r


def is_within_timisoara(lat, lng):
    """
    Check if coordinates are within Timisoara city bounds.
    
    Args:
        lat: Latitude
        lng: Longitude
        
    Returns:
        bool: True if within bounds, False otherwise
    """
    bounds = current_app.config.get('MAP_BOUNDS', {
        'north': 45.80,
        'south': 45.70,
        'east': 21.35,
        'west': 21.10
    })
    
    return (bounds['south'] <= lat <= bounds['north'] and 
            bounds['west'] <= lng <= bounds['east'])


@lru_cache(maxsize=100)
def geocode_address(address, city="Timisoara"):
    """
    Convert an address to coordinates using Nominatim OpenStreetMap API.
    
    Args:
        address: Street address to geocode
        city: City name (default: Timisoara)
        
    Returns:
        tuple: (latitude, longitude) or None if geocoding failed
    """
    # Add city to address if not present
    if city.lower() not in address.lower():
        search_address = f"{address}, {city}, Romania"
    else:
        search_address = f"{address}, Romania"
    
    try:
        # Using Nominatim API with proper User-Agent as required by their usage policy
        url = "https://nominatim.openstreetmap.org/search"
        headers = {
            "User-Agent": "TimisoaraAccessibilityMap/1.0"
        }
        params = {
            "q": search_address,
            "format": "json",
            "limit": 1
        }
        
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        
        if data and len(data) > 0:
            lat = float(data[0]["lat"])
            lon = float(data[0]["lon"])
            
            # Verify coordinates are within Timisoara
            if is_within_timisoara(lat, lon):
                return (lat, lon)
            else:
                return None
        else:
            return None
    except Exception as e:
        current_app.logger.error(f"Geocoding error: {str(e)}")
        return None


@lru_cache(maxsize=100)
def reverse_geocode(lat, lng):
    """
    Convert coordinates to an address using Nominatim OpenStreetMap API.
    
    Args:
        lat: Latitude
        lng: Longitude
        
    Returns:
        str: Address string or None if reverse geocoding failed
    """
    try:
        # Using Nominatim API with proper User-Agent as required by their usage policy
        url = "https://nominatim.openstreetmap.org/reverse"
        headers = {
            "User-Agent": "TimisoaraAccessibilityMap/1.0"
        }
        params = {
            "lat": lat,
            "lon": lng,
            "format": "json",
            "zoom": 18,  # Building level detail
            "addressdetails": 1
        }
        
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        
        if "display_name" in data:
            return data["display_name"]
        else:
            return None
    except Exception as e:
        current_app.logger.error(f"Reverse geocoding error: {str(e)}")
        return None


def get_route(start_lat, start_lng, end_lat, end_lng, wheelchair=False):
    """
    Get a walking or wheelchair route between two points using OSRM API.
    
    Args:
        start_lat, start_lng: Starting coordinates
        end_lat, end_lng: Ending coordinates
        wheelchair: If True, will request wheelchair accessible route
        
    Returns:
        dict: Route information including geometry and instructions
    """
    try:
        # Use OSRM open source routing machine
        base_url = "https://router.project-osrm.org/route/v1"
        profile = "foot" if not wheelchair else "wheelchair"  # Wheelchair profiles require specialized OSRM instances
        
        # Format coordinates for OSRM
        coords = f"{start_lng},{start_lat};{end_lng},{end_lat}"
        
        # Make request
        url = f"{base_url}/{profile}/{coords}"
        params = {
            "overview": "full",
            "geometries": "geojson",
            "steps": "true",
            "annotations": "true"
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if data["code"] == "Ok" and len(data["routes"]) > 0:
            return {
                "distance": data["routes"][0]["distance"],  # in meters
                "duration": data["routes"][0]["duration"],  # in seconds
                "geometry": data["routes"][0]["geometry"],
                "steps": data["routes"][0]["legs"][0]["steps"]
            }
        else:
            return None
    except Exception as e:
        current_app.logger.error(f"Routing error: {str(e)}")
        return None


def get_nearby_locations(lat, lng, radius=1.0, limit=10):
    """
    Get locations near a point within a given radius.
    
    Args:
        lat, lng: Center coordinates
        radius: Search radius in kilometers
        limit: Maximum number of results
        
    Returns:
        list: List of location IDs sorted by distance
    """
    from app.models import Location
    from sqlalchemy import func, desc
    from app import db
    
    try:
        # Calculate bounding box for faster initial filtering
        # 1 degree lat = ~111 km, 1 degree lng = ~111*cos(lat) km
        lat_radius = radius / 111.0
        lng_radius = radius / (111.0 * math.cos(math.radians(lat)))
        
        # First filter by bounding box (faster)
        locations = Location.query.filter(
            Location.is_approved == True,
            Location.lat.between(lat - lat_radius, lat + lat_radius),
            Location.lng.between(lng - lng_radius, lng + lng_radius)
        ).all()
        
        # Then calculate exact distances and filter by actual radius
        result = []
        for loc in locations:
            dist = calculate_distance(lat, lng, loc.lat, loc.lng)
            if dist <= radius:
                result.append({
                    'id': loc.id,
                    'distance': dist
                })
        
        # Sort by distance and limit results
        result.sort(key=lambda x: x['distance'])
        return result[:limit]
    except Exception as e:
        current_app.logger.error(f"Nearby search error: {str(e)}")
        return []
