# Vercel Deployment Size Fix

## Problem
Vercel Serverless Functions have a 250MB unzipped size limit. The original requirements.txt included heavy geospatial libraries that exceeded this limit:

- **geopandas** + GDAL dependencies: ~100MB+
- **rasterio** + GDAL: ~80MB+
- **fiona** + GDAL: ~60MB+
- **pyproj** + PROJ: ~40MB+
- **Total**: ~300-400MB (exceeds 250MB limit)

## Solution Applied

### 1. Reduced Dependencies
The `requirements.txt` has been updated to remove heavy geospatial libraries while keeping core functionality:

**Removed:**
- geopandas (heavy GDAL dependency)
- rasterio (heavy GDAL dependency)
- fiona (heavy GDAL dependency)
- pyproj (heavy PROJ dependency)

**Kept:**
- shapely (lightweight geometry library, ~15-20MB)
- All other core dependencies (numpy, pandas, fastapi, etc.)

**New total size**: ~100-150MB (within Vercel's 250MB limit)

### 2. Optional Imports
Made geospatial library imports optional with graceful fallbacks:
- [api/service.py](code/US_scripts/api/service.py): GeoPandas import wrapped in try/except
- [GAEZ_SSURGO_data.py](code/US_scripts/GAEZ_SSURGO_data.py): All heavy geospatial imports optional with clear error messages

### 3. Enhanced .vercelignore
Added exclusions for:
- Heavy notebook files (*.nb.html)
- Test code directories
- Ghana-specific code
- PyAEZ modules not needed for API

## Limitations

### Features Not Available in Lightweight Deployment:
- **SSURGO data fetching** via `mukey_wcs()` - requires rasterio/geopandas
- **Automatic spatial data downloads** - requires full geospatial stack

### Workarounds:
1. **Provide soil data directly**: Use the API with manual horizon data instead of relying on automatic SSURGO fetches
2. **Pre-process data**: Fetch SSURGO data elsewhere and pass to API
3. **Use the `user_horizons` parameter** to override automatic data fetching

## Alternative Deployment Options

If you need full geospatial functionality, consider these platforms with larger limits:

### AWS Lambda with Docker
- **Size limit**: 10 GB container image
- **Setup**: Use Docker image with full GDAL/geospatial stack
- **Cost**: Pay per invocation
- **Recommendation**: Best for production with full features

### Google Cloud Run
- **Size limit**: 32 GB memory, no hard container size limit
- **Setup**: Deploy as containerized app
- **Cost**: Pay for actual usage
- **Recommendation**: Great for high-memory geospatial workloads

### Railway.app
- **Size limit**: No strict limits
- **Setup**: Simple git push deployment
- **Cost**: ~$5/month minimum
- **Recommendation**: Easiest migration from Vercel

### Render.com
- **Size limit**: More generous than Vercel
- **Setup**: Similar to Vercel (git-based)
- **Cost**: Free tier available, $7/month for production
- **Recommendation**: Good balance of ease and features

## Testing the Deployment

After deploying with reduced dependencies:

```bash
# Test that core API works
curl https://your-app.vercel.app/

# Test calculation with manual horizon data (no SSURGO fetch)
curl -X POST https://your-app.vercel.app/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 40.7128,
    "longitude": -74.0060,
    "crop": "corn",
    "user_horizons": [
      {"depth_top": 0, "depth_bottom": 20, "clay": 25, "sand": 35, "ph": 6.5},
      {"depth_top": 20, "depth_bottom": 50, "clay": 30, "sand": 30, "ph": 6.8}
    ]
  }'
```

## Files Changed

1. **requirements.txt** - Removed heavy geospatial dependencies
2. **code/US_scripts/api/service.py** - Made geopandas import optional
3. **code/US_scripts/GAEZ_SSURGO_data.py** - Made all geospatial imports optional with error messages
4. **.vercelignore** - Added more exclusions to reduce deployment size

## Reverting to Full Functionality

To use full geospatial features locally or on another platform:

```bash
# Install full requirements
pip install geopandas rasterio fiona pyproj

# Or use requirements-full.txt if you create one
pip install -r requirements-full.txt
```

## Next Steps

1. **Test the lightweight deployment on Vercel** - Should now build successfully
2. **Verify API functionality** with manual horizon data
3. **If you need SSURGO fetching**, consider migrating to AWS Lambda or Google Cloud Run
4. **Document API limitations** in user-facing docs regarding automatic data fetching

## Questions?

- Check Vercel build logs: `vercel logs <deployment-url>`
- Monitor package sizes: `pip list --format=columns`
- Test locally with minimal deps: `pip install -r requirements.txt`
