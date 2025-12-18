"""
Lightweight elevation and slope estimation using REST APIs.
No geospatial packages required - only uses 'requests'.
"""

import requests
import logging
import math

logger = logging.getLogger(__name__)


def get_elevation_usgs(latitude, longitude, units='Meters'):
    """
    Get elevation at a point using USGS Elevation Point Query Service.
    
    Args:
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees
        units: 'Meters' or 'Feet' (default: Meters)
    
    Returns:
        float: Elevation in specified units, or None if failed
        
    Example:
        >>> elev = get_elevation_usgs(41.2427, -101.6338)
        >>> print(f"Elevation: {elev}m")
    """
    url = "https://epqs.nationalmap.gov/v1/json"
    params = {
        'x': longitude,
        'y': latitude,
        'units': units,
        'output': 'json'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if 'value' in data:
            elevation = float(data['value'])
            if elevation != -1000000:  # USGS returns -1000000 for no data
                logger.info(f"Elevation at ({latitude}, {longitude}): {elevation}{units}")
                return elevation
        
        logger.warning(f"No elevation data available at ({latitude}, {longitude})")
        return None
        
    except Exception as e:
        logger.error(f"Failed to get elevation: {str(e)}")
        return None


def estimate_slope_from_elevation(latitude, longitude, distance_m=100):
    """
    Estimate slope percentage at a point by sampling elevations in 4 directions.
    
    This creates a small grid around the point and calculates the maximum
    slope from the elevation differences.
    
    Args:
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees
        distance_m: Distance in meters for sampling points (default 100m)
    
    Returns:
        float: Slope percentage (0-100), or 0 if calculation fails
        
    Example:
        >>> slope = estimate_slope_from_elevation(41.2427, -101.6338)
        >>> print(f"Slope: {slope}%")
    """
    # Convert distance to degrees (approximate)
    # At mid-latitudes: 1 degree lat ≈ 111km, 1 degree lon ≈ 111km * cos(lat)
    lat_offset = distance_m / 111000
    lon_offset = distance_m / (111000 * math.cos(math.radians(latitude)))
    
    # Get center elevation
    elev_center = get_elevation_usgs(latitude, longitude)
    if elev_center is None:
        logger.warning("Using default slope of 0% (no elevation data)")
        return 0.0
    
    # Sample elevations in 4 cardinal directions
    points = [
        (latitude + lat_offset, longitude, 'N'),      # North
        (latitude - lat_offset, longitude, 'S'),      # South
        (latitude, longitude + lon_offset, 'E'),      # East
        (latitude, longitude - lon_offset, 'W')       # West
    ]
    
    max_slope = 0.0
    for lat, lon, direction in points:
        elev = get_elevation_usgs(lat, lon)
        if elev is not None:
            # Calculate slope as rise/run * 100
            elevation_diff = abs(elev - elev_center)
            slope = (elevation_diff / distance_m) * 100
            max_slope = max(max_slope, slope)
            logger.debug(f"Slope {direction}: {slope:.2f}%")
    
    logger.info(f"Estimated slope at ({latitude}, {longitude}): {max_slope:.2f}%")
    return round(max_slope, 2)


def get_slope_simple(latitude, longitude):
    """
    Simplified slope estimation - just uses N-S elevation difference.
    Faster than full 4-direction sampling.
    
    Args:
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees
    
    Returns:
        float: Slope percentage, or 0 if calculation fails
    """
    distance_m = 100  # Sample 100m apart
    lat_offset = distance_m / 111000
    
    # Get elevations for center and north point
    elev_center = get_elevation_usgs(latitude, longitude)
    elev_north = get_elevation_usgs(latitude + lat_offset, longitude)
    
    if elev_center is None or elev_north is None:
        return 0.0
    
    elevation_diff = abs(elev_north - elev_center)
    slope = (elevation_diff / distance_m) * 100
    
    return round(slope, 2)


def get_slope_opentopography(latitude, longitude, dem='SRTMGL1'):
    """
    Get slope from OpenTopography Global DEM API.
    Note: Requires API key (free registration).
    
    Args:
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees
        dem: DEM dataset ('SRTMGL1', 'SRTMGL3', 'AW3D30', etc.)
    
    Returns:
        float: Slope in degrees, or None if failed
    """
    # This is a placeholder - requires API key
    # Documentation: https://portal.opentopography.org/apidocs/
    logger.warning("OpenTopography requires API key - not implemented")
    return None


def get_slope_for_gaez(latitude, longitude, method='simple'):
    """
    Main function to get slope for GAEZ calculations.
    Tries multiple methods and returns first successful result.
    
    Args:
        latitude: Latitude in decimal degrees  
        longitude: Longitude in decimal degrees
        method: 'simple' (N-S only) or 'full' (4-direction sampling)
    
    Returns:
        float: Slope percentage (0-100)
    """
    try:
        if method == 'full':
            slope = estimate_slope_from_elevation(latitude, longitude)
        else:
            slope = get_slope_simple(latitude, longitude)
        
        return slope if slope is not None else 0.0
        
    except Exception as e:
        logger.error(f"Failed to get slope: {str(e)}")
        return 0.0


# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test location: Nebraska
    lat, lon = 41.2427, -101.6338
    
    print("\n=== Example 1: Get Elevation ===")
    elevation = get_elevation_usgs(lat, lon)
    print(f"Elevation: {elevation}m")
    
    print("\n=== Example 2: Simple Slope (N-S) ===")
    slope = get_slope_simple(lat, lon)
    print(f"Slope: {slope}%")
    
    print("\n=== Example 3: Full Slope (4-direction) ===")
    slope = estimate_slope_from_elevation(lat, lon)
    print(f"Slope: {slope}%")
    
    print("\n=== Example 4: GAEZ Slope ===")
    slope = get_slope_for_gaez(lat, lon, method='simple')
    print(f"GAEZ Slope: {slope}%")
