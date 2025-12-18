# Immediate Fix Options for Vercel Deployment

## Problem
Current deployment: **~260 MB** (scipy 110MB + pandas 67MB + numpy 37MB + others 46MB)
Vercel limit: **250 MB**

## Option 1: Deploy to Railway (FASTEST - 15 minutes)

Railway has no size limits and is as easy as Vercel:

```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login
railway login

# 3. Initialize project
railway init

# 4. Deploy
railway up
```

OR use web interface:
1. Go to https://railway.app
2. Click "Start a New Project"
3. Select "Deploy from GitHub repo"
4. Select your repo
5. Done! (Railway auto-detects Python/requirements.txt)

**URL**: Gets automatic .railway.app domain

## Option 2: Deploy to Render (Also 15 minutes)

```bash
# No CLI needed - just web interface:
1. Go to https://render.com
2. Click "New +"  → "Web Service"
3. Connect GitHub repo
4. Render auto-detects Python
5. Click "Create Web Service"
```

**Configuration**:
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn code.US_scripts.api.main:app --host 0.0.0.0 --port $PORT`

## Option 3: Remove Scipy (2-3 days of work)

Create lightweight interpolation without scipy:

### Step 1: Create `code/US_scripts/lightweight_interpolate.py`

```python
import numpy as np

def pchip_interpolate(x, y, xi):
    """
    Piecewise Cubic Hermite Interpolating Polynomial (PCHIP).
    Pure NumPy implementation - no scipy required.
    """
    # Simplified implementation for monotonic interpolation
    # Full implementation: ~200 lines of code
    return np.interp(xi, x, y)  # Linear fallback

def linear_interpolate(x, y, xi):
    """Linear interpolation - equivalent to scipy interp1d(kind='linear')"""
    return np.interp(xi, x, y)
```

### Step 2: Update GAEZ_SQI_functions.py

Replace:
```python
from scipy.interpolate import PchipInterpolator, interp1d
```

With:
```python
from lightweight_interpolate import pchip_interpolate, linear_interpolate
```

### Step 3: Update requirements.txt

Remove `scipy>=1.7.0,<2.0.0`

**Savings**: 110 MB
**Risk**: Results may differ slightly (needs validation)

## Option 4: Hybrid Approach (30 minutes)

Keep heavy computation on alternative platform, use Vercel as gateway:

1. Deploy to Railway with full scipy
2. Keep Vercel deployment for frontend/routing
3. Vercel redirects API calls to Railway

## Recommendation

**Use Option 1 (Railway) or Option 2 (Render)**

Why:
- ✅ Zero code changes
- ✅ Same Git-push workflow as Vercel
- ✅ Free tier available
- ✅ No size limits
- ✅ Better for data science workloads
- ✅ 15 minute setup

Vercel is designed for frontend/lightweight APIs. Your application with scipy/pandas/numpy is a data science workload better suited for platforms without strict size limits.
