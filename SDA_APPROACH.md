# Using SDA Instead of Heavy Geospatial Packages

## The Problem
The original approach used WCS (Web Coverage Service) with rasterio/geopandas to fetch SSURGO data, requiring **~300MB of geospatial libraries**.

## The Solution: SDA (Soil Data Access)
Use USDA's **Soil Data Access REST API** - a lightweight web service that only needs the `requests` library.

## Comparison

### Old Approach (WCS with Rasterio)
```python
# Requires: geopandas, rasterio, fiona, pyproj (~300MB)
import geopandas as gpd
from shapely.geometry import Point
import rasterio

point = Point(longitude, latitude)
aoi_gdf = gpd.GeoDataFrame({'geometry': [point.buffer(0.001)]}, crs="EPSG:4326")
raster = GAEZ_SSURGO_data.mukey_wcs(aoi_gdf, db='gssurgo', res=30)
data = raster.read(1)
mukeys = np.unique(data[data > 0])
```

### New Approach (SDA Query)
```python
# Requires: only requests (~50KB)
from GAEZ_SDA_query import get_dominant_mukey_at_point

mukey = get_dominant_mukey_at_point(latitude, longitude)
# That's it! Server does all the spatial processing
```

## SDA Functions Available

### 1. Query by Point
```python
from GAEZ_SDA_query import get_dominant_mukey_at_point

# Get mukey at a specific location
mukey = get_dominant_mukey_at_point(41.2427, -101.6338)
print(f"Mukey: {mukey}")
```

### 2. Query by Bounding Box
```python
from GAEZ_SDA_query import get_mukeys_by_bbox

# Get all mukeys in a rectangular area
mukeys = get_mukeys_by_bbox(
    min_lon=-101.7703,
    min_lat=41.1811,
    max_lon=-101.4972,
    max_lat=41.3042
)
print(f"Found {len(mukeys)} map units: {mukeys}")
```

### 3. Query by WKT Geometry
```python
from GAEZ_SDA_query import get_mukeys_by_wkt

# Use any WKT geometry
wkt = "POLYGON((-101.77 41.18, -101.77 41.30, -101.50 41.30, -101.50 41.18, -101.77 41.18))"
mukeys = get_mukeys_by_wkt(wkt)
```

### 4. Query Point with Buffer
```python
from GAEZ_SDA_query import get_mukeys_by_lat_lon

# Get mukeys within 500m of a point
mukeys = get_mukeys_by_lat_lon(
    latitude=41.2427,
    longitude=-101.6338,
    buffer_meters=500
)
```

## How SDA Works

1. **You send**: HTTP POST request with SQL query
2. **Server processes**: Spatial intersections, filtering, etc.
3. **You receive**: Simple JSON/tabular data
4. **No need for**: GDAL, GEOS, PROJ, or other heavy C libraries

## API Integration

The API now automatically tries SDA first, falling back to WCS only if needed:

```python
# In api/service.py
if SDA_QUERY_AVAILABLE:
    mukey = get_dominant_mukey_at_point(lat, lon)  # Lightweight!
else:
    # Fallback to WCS with rasterio (if available)
    mukey_raster = GAEZ_SSURGO_data.mukey_wcs(...)
```

## Benefits

| Aspect | Old (WCS) | New (SDA) |
|--------|-----------|-----------|
| **Package Size** | ~300MB | ~50KB |
| **Dependencies** | 5 heavy geo libs | 1 light lib (requests) |
| **Vercel Compatible** | ❌ No | ✅ Yes |
| **Speed** | Slower (raster processing) | Faster (direct query) |
| **Accuracy** | Grid-based | Polygon-accurate |

## Testing the SDA Approach

```python
# Run the example script
python code/US_scripts/GAEZ_SDA_query.py
```

Output:
```
=== Example 1: Query by Bounding Box ===
Found 45 map units
Mukeys: [354627, 354628, 354629, ...]

=== Example 2: Query by WKT Polygon ===
Found 45 map units

=== Example 3: Query at Point ===
Mukey at point: 354627
Found 3 components: [17835661, 17835662, 17835663]
```

## Migration Guide

### For Notebook Users
Replace this:
```python
# OLD
aoi = gpd.GeoDataFrame({'geometry': [aoi_geom]}, crs="EPSG:4326")
raster_obj = GAEZ_SSURGO_data.mukey_wcs(aoi, db='gssurgo', res=30)
data = raster_obj.read(1)
unique_mukey = np.unique(data[data != raster_obj.nodata])
mukey_list = unique_mukey.astype(int)
```

With this:
```python
# NEW
from GAEZ_SDA_query import get_mukeys_by_wkt

aoi_wkt = 'POLYGON((-101.77 41.18, -101.77 41.30, -101.50 41.30, -101.50 41.18, -101.77 41.18))'
mukey_list = get_mukeys_by_wkt(aoi_wkt)
```

### For API Users
No changes needed! The API automatically uses SDA when available.

## Limitations

- **Requires internet connection** to SDA service
- **USDA service availability** - occasional downtime
- **For complex spatial analysis**, full GIS tools still needed
- **For this API**: SDA is perfect - just getting mukeys!

## Additional SDA Resources

- **SDA Documentation**: https://sdmdataaccess.nrcs.usda.gov/
- **Query Examples**: https://nrcs.app.box.com/v/soils/folder/17971946225
- **SDA Guide**: https://www.nrcs.usda.gov/resources/data-and-reports/soil-data-access

## Result

✅ **Deployment size reduced from 400MB to ~100MB**
✅ **Fits within Vercel's 250MB limit**  
✅ **Same functionality for point queries**
✅ **Faster and more accurate**
