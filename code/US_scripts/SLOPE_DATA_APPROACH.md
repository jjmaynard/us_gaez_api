# Slope Data Acquisition - Lightweight REST API Approach

## Overview

The system now fetches slope data using **USGS Elevation Point Query Service (EPQS)**, a free REST API that requires only the `requests` library. This eliminates the need for heavy geospatial packages like `rasterio`, `GDAL`, and `GEOS`.

## Implementation

### New Module: `GAEZ_elevation_slope.py`

Provides three slope calculation methods:

1. **`get_slope_simple(lat, lon)`** - Fast N-S sampling (~2 API calls, <1 sec)
2. **`estimate_slope_from_elevation(lat, lon)`** - Full 4-direction sampling (~5 API calls, ~2 sec)
3. **`get_slope_for_gaez(lat, lon, method='simple')`** - Main function with configurable method

### API Endpoint

- **Service**: USGS Elevation Point Query Service (EPQS)
- **URL**: `https://epqs.nationalmap.gov/v1/json`
- **Method**: GET with lat/lon parameters
- **Response**: JSON with elevation in meters
- **Cost**: Free, no API key required
- **Coverage**: Continental US, Alaska, Hawaii

### How It Works

1. **Elevation Sampling**: Queries elevation at center point and surrounding points (100m spacing)
2. **Slope Calculation**: Calculates rise/run percentage from elevation differences
3. **Direction Sampling**:
   - Simple method: North-South only (faster)
   - Full method: North, South, East, West (more accurate)
4. **Result**: Maximum slope percentage from all sampled directions

## Integration Points

### 1. Soil Data Processing (`GAEZ_soil_data_processing.py`)

- **`process_plot_data()`**: Automatically fetches slope when processing field data
- **`process_site_data()`**: Automatically fetches slope when processing site data
- Graceful fallback to 0% if API unavailable

### 2. API Service Layer (`api/service.py`)

- **`calculate_soil_quality()`**: Automatically adds slope to SSURGO data if missing
- Runs after SSURGO data retrieval, before user data integration
- Only fetches if slope column missing or all NaN values

### 3. Priority Hierarchy

1. **User-provided slope** (via `site_data.slope_pct`) - highest priority
2. **SSURGO slope** (from component data) - if available
3. **USGS API slope** (automatically fetched) - fallback
4. **Default 0%** - last resort if API fails

## Testing Results

### Flat Terrain
```
Location: Nebraska (41.2427, -101.6338)
Elevation: 959m
Simple slope: 0.3%
Full slope: 1.06%
```

### Steep Terrain
```
Location: Pikes Peak, CO (38.8409, -105.0423)
Elevation: 4,291m
Simple slope: 62.71%
Full slope: 62.71%
```

### Very Steep Terrain
```
Location: Yosemite Valley Wall (37.7459, -119.5332)
Elevation: 2,692m
Simple slope: 339.09%
Full slope: 424.96%
```

## Advantages

✅ **No heavy dependencies** - only `requests` library  
✅ **Free service** - no API key or registration  
✅ **Fast** - simple method takes <1 second  
✅ **Accurate** - validated against known terrain  
✅ **Reliable** - USGS official data source  
✅ **Automatic** - works transparently in pipeline  

## Limitations

- **US only** - USGS EPQS covers US territories only
- **Resolution** - ~10-30m depending on location (SRTM/NED data)
- **Rate limits** - Reasonable use policy (no specific limit documented)
- **Network required** - Needs internet connection to USGS servers

## Migration from Rasterio

### Before (Heavy)
```python
import rasterio
import rasterio.sample

olm_250_slope = "/vsicurl/https://s3.../dtm_slope_merit.dem..."
with rasterio.open(olm_250_slope) as ds:
    for val in rasterio.sample.sample_gen(ds, coords):
        slope = val[0]
```

**Dependencies**: rasterio (~80MB), GDAL (~60MB), numpy (~20MB), etc.  
**Total size**: ~300MB with all dependencies

### After (Lightweight)
```python
from GAEZ_elevation_slope import get_slope_for_gaez

slope = get_slope_for_gaez(latitude, longitude, method='simple')
```

**Dependencies**: requests (~50KB)  
**Total size**: <1MB

## Future Enhancements

Potential improvements for future versions:

1. **Caching**: Cache elevation results to reduce API calls
2. **Batch queries**: Process multiple locations in one request
3. **Alternative APIs**: Add OpenTopography, Mapbox, or other providers as fallbacks
4. **Global coverage**: Support international locations with different APIs
5. **Aspect calculation**: Add slope aspect (direction) calculation
6. **Terrain classification**: Add terrain ruggedness index, curvature, etc.

## Usage Examples

### Direct Function Call
```python
from GAEZ_elevation_slope import get_slope_for_gaez

# Simple (fast)
slope = get_slope_for_gaez(41.2427, -101.6338, method='simple')
print(f"Slope: {slope}%")

# Full 4-direction (more accurate)
slope = get_slope_for_gaez(41.2427, -101.6338, method='full')
print(f"Slope: {slope}%")
```

### Automatic Integration
```python
from api.service import GAEZCalculationService

# Slope automatically fetched if not in SSURGO or user data
service = GAEZCalculationService()
result = service.calculate_soil_quality(request)
# Result includes slope from USGS API if needed
```

### Manual Site Data Processing
```python
from GAEZ_soil_data_processing import process_site_data

site_data = pd.DataFrame([{
    'latitude': 41.2427,
    'longitude': -101.6338,
    'bedrock_depth': 150
    # slope_pct not provided - will be fetched automatically
}])

result = process_site_data(site_data, map_data)
# result now has 'slope' column with USGS data
```

## References

- [USGS Elevation Point Query Service](https://www.usgs.gov/the-national-map-data-delivery/gis-data-download)
- [USGS EPQS API Documentation](https://epqs.nationalmap.gov/v1/docs)
- [National Elevation Dataset (NED)](https://www.usgs.gov/core-science-systems/national-geospatial-program/national-map)
