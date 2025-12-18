# Vercel Deployment Size Analysis

## Current Situation

**Error**: Serverless Function exceeds 250 MB unzipped limit

## Package Size Breakdown

| Package | Size (MB) | Purpose | Required? |
|---------|-----------|---------|-----------|
| **scipy** | 110 | Interpolation (PchipInterpolator, interp1d) | **YES** - Core SQI calculations |
| **pandas** | 67 | DataFrames for soil data | **YES** - Throughout codebase |
| **numpy** | 37 | Array operations | **YES** - Required by pandas/scipy |
| pydantic | 3.4 | API validation | YES - FastAPI dependency |
| fastapi | 1.0 | API framework | YES - Core API |
| uvicorn | 0.5 | ASGI server | YES - Deployment |
| requests | 0.4 | HTTP client | YES - SDA/USGS APIs |
| **Subtotal** | **~220 MB** | | |
| **+ Dependencies** | **~30-40 MB** | httpx, starlette, etc. | |
| **TOTAL** | **~260 MB** | | **EXCEEDS 250MB** |

## Root Cause

**Scipy is 110MB** - nearly half the limit by itself. The interpolation functions (PchipInterpolator, interp1d) are used throughout GAEZ_SQI_functions.py for constraint curve calculations.

## Solutions (Ranked by Feasibility)

### Option 1: Switch to Alternative Deployment Platform (RECOMMENDED)

**Pros:**
- Immediate solution
- No code changes needed
- Higher limits (10GB+ on most platforms)

**Platforms:**
| Platform | Free Tier Limit | Deployment |
|----------|-----------------|------------|
| **AWS Lambda** | 10 GB (50MB zipped) | Requires packaging |
| **Google Cloud Run** | 32 GB | Docker container |
| **Railway** | No size limit | Git push |
| **Render** | No size limit | Git push |
| **Fly.io** | 8 GB | Docker |

**Best Choice**: **Railway** or **Render** - Same simplicity as Vercel, no size limits, free tier available.

### Option 2: Replace Scipy Interpolation with Pure NumPy

**Effort**: HIGH (2-3 days)
**Risk**: MEDIUM (potential accuracy loss)

Replace scipy.interpolate functions with NumPy-based alternatives:
- `PchipInterpolator` → Custom piecewise cubic Hermite implementation
- `interp1d` → `numpy.interp` (linear only) or custom cubic spline

**Savings**: ~110 MB
**Caveats**: 
- Must validate results match original
- Custom spline implementation needed for cubic
- Could affect calculation accuracy

### Option 3: Pandas Optimization

**Effort**: MEDIUM (1 day)
**Risk**: LOW

Reduce pandas size by excluding unnecessary components:
```bash
pip install pandas --no-deps
pip install numpy pytz python-dateutil
```

**Savings**: ~10-15 MB (not enough alone)

### Option 4: Use Pandas-Lite or Polars

**Effort**: VERY HIGH (1 week+)
**Risk**: HIGH (major refactoring)

Replace pandas with lightweight alternative:
- **polars**: ~15MB (but different API)
- **modin**: Still uses pandas backend

**Savings**: ~50 MB
**Caveats**: Massive code refactoring needed

### Option 5: Split into Multiple Functions

**Effort**: HIGH (2-3 days)
**Risk**: MEDIUM

Create separate Vercel functions:
- `/api/calculate` - Core SQI (with scipy)
- `/api/ssurgo` - Data fetching (no scipy)
- `/api/interpret` - Interpretations (no scipy)

**Savings**: None (each function still needs scipy)
**Benefit**: Better separation of concerns

### Option 6: External Calculation Service

**Effort**: HIGH (3-5 days)
**Risk**: MEDIUM

Host scipy-dependent calculations externally:
- Vercel API → calls → External service (Railway/Render)
- External service handles heavy computations
- Vercel only does routing/validation

**Savings**: Makes Vercel deployment lightweight
**Complexity**: Introduces dependency on external service

## Recommended Action Plan

### Phase 1: Immediate (Use Alternative Platform)

**Deploy to Railway** (easiest migration from Vercel):

1. Create Railway account
2. Connect GitHub repo
3. Railway auto-detects Python
4. Deploy (no size limits!)
5. Keep Vercel as backup/redirect

**Migration time**: < 30 minutes

### Phase 2: Long-term (Optimize for Vercel)

If must stay on Vercel, implement custom NumPy interpolation:

1. Create `lightweight_interpolate.py` with NumPy-only functions
2. Replace scipy calls in `GAEZ_SQI_functions.py`
3. Validate results match original
4. Update requirements.txt to remove scipy
5. Test deployment size

**Development time**: 2-3 days
**Risk**: Calculation accuracy changes

## Decision Matrix

| Criteria | Railway/Render | Custom NumPy | Keep Scipy |
|----------|----------------|--------------|------------|
| Time to deploy | ⭐⭐⭐⭐⭐ (< 1 hr) | ⭐⭐ (2-3 days) | ❌ Won't work |
| Maintenance | ⭐⭐⭐⭐⭐ (none) | ⭐⭐ (ongoing validation) | N/A |
| Accuracy | ⭐⭐⭐⭐⭐ (identical) | ⭐⭐⭐⭐ (needs validation) | N/A |
| Cost | ⭐⭐⭐⭐⭐ (free tier) | ⭐⭐⭐⭐⭐ (free tier) | N/A |
| Scalability | ⭐⭐⭐⭐⭐ (10GB+) | ⭐⭐⭐ (250MB limit) | N/A |

## Recommendation

**Deploy to Railway or Render immediately**. They offer:
- Same Git-push deployment as Vercel
- No size limits (can keep all packages)
- Free tier for development
- Easy migration path
- Better suited for data science workloads

Vercel is optimized for frontend/lightweight APIs. Scientific computing with scipy/pandas is better suited for platforms without strict size limits.

## Alternative: Vercel Pro

Vercel Pro ($20/month) increases limit to **50MB compressed** (roughly 200-250MB uncompressed) - still likely insufficient with scipy.
