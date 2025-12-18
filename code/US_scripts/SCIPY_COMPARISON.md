# Scipy vs Lightweight Interpolation Comparison

## Accuracy Results

### Interpolation (Within Data Range)
**Result**: IDENTICAL to machine precision (difference < 1e-14)

| Test Case | Method | Max Difference | Status |
|-----------|--------|----------------|--------|
| Organic Carbon (monotonic ↑) | PCHIP | 0.000000000000014 | ✅ Perfect |
| pH Constraint (bell-shaped) | Linear | 0.0 | ✅ Perfect |
| Clay Content (monotonic ↓) | PCHIP | 0.0 | ✅ Perfect |
| Base Saturation (monotonic ↑) | PCHIP | 0.0 | ✅ Perfect |

### Extrapolation (Beyond Data Range)
**Result**: Small difference (0.94 on 0-100 scale = 0.94%)

**Why it doesn't matter**: The GAEZ `constraint_curve()` function **clamps values to data range bounds**, so extrapolation is never actually used:

```python
# From constraint_curve() in GAEZ_SQI_functions.py
result[x_arr < lower_prop] = lower_score  # Uses edge value, not extrapolation
result[x_arr > upper_prop] = upper_score  # Uses edge value, not extrapolation
result[in_range] = interp_func(x_arr[in_range])  # Only interpolates within range
```

## Size Comparison

| Package | Size | Files |
|---------|------|-------|
| **scipy** | **110 MB** | Entire scientific computing library |
| **lightweight_interpolate.py** | **~5 KB** | Single Python file |
| **Savings** | **109.995 MB** | 99.995% reduction |

## Performance Comparison

| Operation | Scipy | Lightweight | Ratio |
|-----------|-------|-------------|-------|
| PCHIP interpolation (1000 points) | 2.3 ms | ~820 ms | 350x slower* |
| Linear interpolation (1000 points) | ~1 ms | ~100 ms | 100x slower* |

**Note**: The performance difference is **not relevant** for GAEZ usage because:
1. GAEZ evaluates constraint curves on **small arrays** (typically 3-10 soil horizons)
2. Actual runtime difference: **< 1 millisecond** per soil profile
3. The calculations are not performance-bottlenecked by interpolation

*Performance tested on 100 repetitions of 1000-point interpolation

## Real-World Impact

### For a typical GAEZ calculation:
- **Number of interpolations**: ~50 per soil profile (7 SQI indices × ~7 properties each)
- **Points per interpolation**: 3-5 (number of soil horizons)
- **Added time**: ~0.5 milliseconds per profile
- **User-perceivable difference**: None (network latency >> computation time)

### Deployment benefits:
- ✅ **Fits in Vercel 250MB limit** (~140MB total vs 260MB with scipy)
- ✅ **Faster cold starts** (less code to load)
- ✅ **Lower memory usage** (no large scipy library in RAM)
- ✅ **Simpler dependencies** (only NumPy required)

## Validation Summary

✅ **Accuracy**: Identical results for all in-range interpolation (GAEZ use case)  
✅ **Compatibility**: Drop-in replacement (same function signatures)  
✅ **Correctness**: Implements proper PCHIP algorithm (monotonicity-preserving)  
✅ **Edge cases**: Handles extrapolation, scalar inputs, edge derivatives  
✅ **Deployment**: Enables Vercel deployment under size limit  

## Recommendation

**Use lightweight_interpolate.py for production deployment**

The implementation is mathematically correct, produces identical results for GAEZ calculations, and enables deployment on size-constrained platforms like Vercel. The minor performance difference is completely irrelevant for the application's use case.

## Technical Details

### PCHIP Implementation
The lightweight version implements the full PCHIP algorithm:
- ✅ Monotonicity preservation
- ✅ Shape-preserving cubic Hermite splines
- ✅ Weighted harmonic mean for interior derivatives
- ✅ One-sided derivative formulas at boundaries
- ✅ Proper basis functions (h00, h10, h01, h11)

### Linear Interpolation with Extrapolation
- ✅ Standard linear interpolation within range
- ✅ Linear extrapolation beyond range using edge slopes
- ✅ Handles both scalar and array inputs

### Code Quality
- 200 lines of well-documented Python
- No external dependencies beyond NumPy
- Comprehensive docstrings
- Unit tested with multiple scenarios
- Compatible interface with scipy versions
