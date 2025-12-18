"""
Lightweight SSURGO data access using SDA (Soil Data Access) REST API.
No heavy geospatial packages required - only uses 'requests'.

This replaces the WCS-based approach with direct SQL queries to SDA.
"""

import requests
import json
from typing import List, Tuple, Optional, Dict, Any
import logging
import time

logger = logging.getLogger(__name__)

# SDA REST endpoint
SDA_URL = "https://sdmdataaccess.sc.egov.usda.gov/tabular/post.rest"


def query_sda(sql: str, format: str = "json", timeout: int = 60, retries: int = 2) -> Dict[str, Any]:
    """
    Execute a SQL query against the SDA service with retry logic.
    
    Args:
        sql: SQL query string
        format: Response format ('json' or 'xml')
        timeout: Timeout in seconds
        retries: Number of retry attempts
    
    Returns:
        Dict containing the query results
        
    Raises:
        requests.RequestException: If the query fails after all retries
    """
    payload = {
        "query": sql,
        "format": format
    }
    
    last_error = None
    for attempt in range(retries + 1):
        try:
            if attempt > 0:
                wait_time = 2 ** attempt  # Exponential backoff: 2, 4 seconds
                logger.info(f"Retrying after {wait_time} seconds (attempt {attempt + 1}/{retries + 1})...")
                time.sleep(wait_time)
            
            response = requests.post(SDA_URL, data=payload, timeout=timeout)
            response.raise_for_status()
            
            if format == "json":
                return response.json()
            else:
                return {"response": response.text}
                
        except requests.Timeout as e:
            last_error = e
            logger.warning(f"SDA query timeout (attempt {attempt + 1}/{retries + 1})")
            continue
        except requests.RequestException as e:
            last_error = e
            logger.error(f"SDA query failed: {str(e)}")
            raise
    
    # All retries failed
    logger.error(f"SDA query failed after {retries + 1} attempts")
    raise last_error


def get_mukeys_by_bbox(min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> List[int]:
    """
    Get list of map unit keys (mukeys) for a bounding box.
    
    Args:
        min_lon: Minimum longitude (west)
        min_lat: Minimum latitude (south)
        max_lon: Maximum longitude (east)
        max_lat: Maximum latitude (north)
    
    Returns:
        List of mukey integers
        
    Example:
        >>> mukeys = get_mukeys_by_bbox(-101.7703, 41.1811, -101.4972, 41.3042)
    """
    # Create WKT polygon from bbox
    wkt = f"POLYGON(({min_lon} {min_lat}, {max_lon} {min_lat}, {max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))"
    
    return get_mukeys_by_wkt(wkt)


def get_mukeys_by_wkt(wkt_geometry: str) -> List[int]:
    """
    Get list of map unit keys (mukeys) for a WKT geometry.
    
    Args:
        wkt_geometry: Well-Known Text geometry string (EPSG:4326)
                     e.g., 'POLYGON((-101.77 41.18, -101.77 41.30, -101.50 41.30, -101.50 41.18, -101.77 41.18))'
    
    Returns:
        List of mukey integers
    """
    sql = f"""
    SELECT DISTINCT mukey
    FROM mapunit mu
    INNER JOIN legend l ON mu.lkey = l.lkey
    WHERE mu.mukey IN (
        SELECT DISTINCT mukey
        FROM mupolygon
        WHERE mupolygongeo.STIntersects(
            geometry::STGeomFromText('{wkt_geometry}', 4326)
        ) = 1
    )
    ORDER BY mukey
    """
    
    try:
        result = query_sda(sql)
        
        # Extract mukeys from response
        if "Table" in result and len(result["Table"]) > 0:
            mukeys = [int(row[0]) for row in result["Table"]]
            logger.info(f"Found {len(mukeys)} map units in AOI")
            return mukeys
        else:
            logger.warning("No map units found in specified area")
            return []
            
    except Exception as e:
        logger.error(f"Failed to query mukeys: {str(e)}")
        raise


def get_mukeys_by_lat_lon(latitude: float, longitude: float, buffer_meters: float = 100) -> List[int]:
    """
    Get map unit keys for a point location with optional buffer.
    
    Args:
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees
        buffer_meters: Buffer distance in meters (default 100m for a small area)
    
    Returns:
        List of mukey integers
    """
    # For a point, we'll create a small bounding box
    # Approximate: 1 degree lat ~ 111km, 1 degree lon ~ 111km * cos(lat)
    import math
    
    buffer_deg_lat = buffer_meters / 111000  # meters to degrees latitude
    buffer_deg_lon = buffer_meters / (111000 * math.cos(math.radians(latitude)))
    
    min_lon = longitude - buffer_deg_lon
    max_lon = longitude + buffer_deg_lon
    min_lat = latitude - buffer_deg_lat
    max_lat = latitude + buffer_deg_lat
    
    return get_mukeys_by_bbox(min_lon, min_lat, max_lon, max_lat)


def get_dominant_mukey_at_point(latitude: float, longitude: float) -> Optional[int]:
    """
    Get the most likely/dominant map unit key at a specific point.
    Uses a tiny bounding box around the point - same fast query as bbox method.
    
    Args:
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees
    
    Returns:
        Single mukey integer or None if not found
    """
    # Use a very small bounding box around the point (~10m x 10m)
    # This uses the same fast query pattern as get_mukeys_by_bbox
    buffer = 0.0001  # ~10 meters
    mukeys = get_mukeys_by_bbox(
        longitude - buffer,
        latitude - buffer, 
        longitude + buffer,
        latitude + buffer
    )
    
    if mukeys:
        mukey = mukeys[0]  # Return first mukey found
        logger.info(f"Found mukey {mukey} at ({latitude}, {longitude})")
        return mukey
    else:
        logger.warning(f"No map unit found at ({latitude}, {longitude})")
        return None


def get_mukey_with_cokey_list(mukey: int) -> List[int]:
    """
    Get list of component keys (cokeys) for a given mukey.
    
    Args:
        mukey: Map unit key
    
    Returns:
        List of cokey integers
    """
    sql = f"""
    SELECT cokey
    FROM component
    WHERE mukey = {mukey}
    ORDER BY comppct_r DESC
    """
    
    try:
        result = query_sda(sql)
        
        if "Table" in result and len(result["Table"]) > 0:
            cokeys = [int(row[0]) for row in result["Table"]]
            return cokeys
        else:
            return []
            
    except Exception as e:
        logger.error(f"Failed to query cokeys for mukey {mukey}: {str(e)}")
        return []


# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Example 1: Query by bounding box
    print("\n=== Example 1: Query by Bounding Box ===")
    mukeys = get_mukeys_by_bbox(-101.7703, 41.1811, -101.4972, 41.3042)
    print(f"Found {len(mukeys)} map units")
    print(f"Mukeys: {mukeys[:10]}...")  # Show first 10
    
    # Example 2: Query by WKT polygon
    print("\n=== Example 2: Query by WKT Polygon ===")
    wkt = "POLYGON((-101.7703 41.1811, -101.7703 41.3042, -101.4972 41.3042, -101.4972 41.1811, -101.7703 41.1811))"
    mukeys = get_mukeys_by_wkt(wkt)
    print(f"Found {len(mukeys)} map units")
    
    # Example 3: Query by point
    print("\n=== Example 3: Query at Point ===")
    mukey = get_dominant_mukey_at_point(41.2427, -101.6338)
    if mukey:
        print(f"Mukey at point: {mukey}")
        
        # Get components for this mukey
        cokeys = get_mukey_with_cokey_list(mukey)
        print(f"Found {len(cokeys)} components: {cokeys}")
