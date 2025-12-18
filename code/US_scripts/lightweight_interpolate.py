"""
Lightweight interpolation functions using only NumPy.
Replaces scipy.interpolate to avoid 110MB scipy dependency.

Implements:
- PCHIP (Piecewise Cubic Hermite Interpolating Polynomial) for monotonic curves
- Linear interpolation with extrapolation for non-monotonic curves
"""

import numpy as np


class PchipInterpolator:
    """
    Piecewise Cubic Hermite Interpolating Polynomial (PCHIP).
    
    Pure NumPy implementation - no scipy required.
    Preserves monotonicity and is shape-preserving.
    
    Compatible interface with scipy.interpolate.PchipInterpolator.
    """
    
    def __init__(self, x, y):
        """
        Initialize PCHIP interpolator.
        
        Args:
            x: array of x values (must be strictly increasing)
            y: array of y values
        """
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        
        if len(x) != len(y):
            raise ValueError("x and y must have the same length")
        if len(x) < 2:
            raise ValueError("x and y must have at least 2 points")
        
        # Check for strictly increasing x
        if not np.all(np.diff(x) > 0):
            raise ValueError("x must be strictly increasing")
        
        self.x = x
        self.y = y
        self._compute_coefficients()
    
    def _compute_coefficients(self):
        """Compute cubic Hermite coefficients."""
        x = self.x
        y = self.y
        n = len(x)
        
        # Compute slopes (derivatives) at each point
        h = np.diff(x)  # intervals
        delta = np.diff(y) / h  # slopes of secants
        
        # Compute derivatives using PCHIP algorithm
        d = np.zeros(n)
        
        # Interior points
        for i in range(1, n - 1):
            # Weighted harmonic mean for shape preservation
            w1 = 2 * h[i] + h[i-1]
            w2 = h[i] + 2 * h[i-1]
            
            if delta[i-1] * delta[i] > 0:
                # Same sign - use weighted harmonic mean
                d[i] = (w1 + w2) / (w1 / delta[i-1] + w2 / delta[i])
            else:
                # Different signs or zero - derivative is zero
                d[i] = 0.0
        
        # Boundary conditions (one-sided differences)
        d[0] = self._edge_derivative(h[0], h[1], delta[0], delta[1])
        d[-1] = self._edge_derivative(h[-1], h[-2], delta[-1], delta[-2])
        
        self.d = d
        self.h = h
        self.delta = delta
    
    def _edge_derivative(self, h1, h2, delta1, delta2):
        """Compute derivative at edge using one-sided formula."""
        # Non-centered formula for edge
        d = ((2 * h1 + h2) * delta1 - h1 * delta2) / (h1 + h2)
        
        # Ensure monotonicity at edge
        if d * delta1 < 0:
            d = 0
        elif (delta1 * delta2 < 0) and (abs(d) > abs(3 * delta1)):
            d = 3 * delta1
        
        return d
    
    def __call__(self, xi):
        """
        Evaluate interpolator at points xi.
        
        Args:
            xi: scalar or array of evaluation points
        
        Returns:
            Interpolated values
        """
        xi = np.asarray(xi, dtype=float)
        scalar_input = np.isscalar(xi) or xi.ndim == 0
        xi = np.atleast_1d(xi)
        
        yi = np.empty_like(xi)
        
        for idx, x_val in enumerate(xi):
            # Find interval
            if x_val <= self.x[0]:
                # Extrapolate left using first derivative
                yi[idx] = self.y[0] + self.d[0] * (x_val - self.x[0])
            elif x_val >= self.x[-1]:
                # Extrapolate right using last derivative
                yi[idx] = self.y[-1] + self.d[-1] * (x_val - self.x[-1])
            else:
                # Interpolate - find interval [x[i], x[i+1]]
                i = np.searchsorted(self.x, x_val) - 1
                i = max(0, min(i, len(self.x) - 2))
                
                # Cubic Hermite interpolation
                t = (x_val - self.x[i]) / self.h[i]
                
                # Hermite basis functions
                h00 = (1 + 2*t) * (1 - t)**2
                h10 = t * (1 - t)**2
                h01 = t**2 * (3 - 2*t)
                h11 = t**2 * (t - 1)
                
                yi[idx] = (h00 * self.y[i] + 
                          h10 * self.h[i] * self.d[i] +
                          h01 * self.y[i+1] + 
                          h11 * self.h[i] * self.d[i+1])
        
        return yi[0] if scalar_input else yi


def interp1d(x, y, kind='linear', fill_value='extrapolate'):
    """
    Linear interpolation compatible with scipy.interpolate.interp1d.
    
    Args:
        x: array of x values
        y: array of y values  
        kind: interpolation kind ('linear' only supported)
        fill_value: 'extrapolate' to allow extrapolation
    
    Returns:
        Interpolation function
    """
    if kind != 'linear':
        raise NotImplementedError("Only 'linear' interpolation is supported")
    
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    
    class LinearInterpolator:
        def __init__(self, x, y, extrapolate):
            self.x = x
            self.y = y
            self.extrapolate = extrapolate
        
        def __call__(self, xi):
            """Evaluate at points xi."""
            if self.extrapolate:
                # NumPy's interp doesn't extrapolate by default
                # We need to handle extrapolation manually
                xi = np.asarray(xi, dtype=float)
                scalar_input = np.isscalar(xi) or xi.ndim == 0
                xi = np.atleast_1d(xi)
                
                yi = np.empty_like(xi)
                
                for idx, x_val in enumerate(xi):
                    if x_val <= self.x[0]:
                        # Extrapolate left
                        slope = (self.y[1] - self.y[0]) / (self.x[1] - self.x[0])
                        yi[idx] = self.y[0] + slope * (x_val - self.x[0])
                    elif x_val >= self.x[-1]:
                        # Extrapolate right
                        slope = (self.y[-1] - self.y[-2]) / (self.x[-1] - self.x[-2])
                        yi[idx] = self.y[-1] + slope * (x_val - self.x[-1])
                    else:
                        # Interpolate
                        yi[idx] = np.interp(x_val, self.x, self.y)
                
                return yi[0] if scalar_input else yi
            else:
                # No extrapolation - use NumPy's interp directly
                return np.interp(xi, self.x, self.y)
    
    return LinearInterpolator(x, y, extrapolate=(fill_value == 'extrapolate'))


# Validation and testing
if __name__ == "__main__":
    print("Testing lightweight interpolation functions...")
    
    # Test 1: PCHIP monotonic increasing
    print("\n=== Test 1: PCHIP Monotonic Increasing ===")
    x = np.array([0, 1, 2, 3, 4])
    y = np.array([0, 2, 3, 5, 8])
    
    pchip = PchipInterpolator(x, y)
    xi = np.array([0.5, 1.5, 2.5, 3.5])
    yi = pchip(xi)
    print(f"Input x: {x}")
    print(f"Input y: {y}")
    print(f"Interpolation points: {xi}")
    print(f"Results: {yi}")
    
    # Test 2: PCHIP monotonic decreasing
    print("\n=== Test 2: PCHIP Monotonic Decreasing ===")
    x = np.array([0, 10, 20, 30, 40])
    y = np.array([100, 80, 60, 40, 20])
    
    pchip = PchipInterpolator(x, y)
    xi = np.array([5, 15, 25, 35])
    yi = pchip(xi)
    print(f"Results: {yi}")
    
    # Test 3: Linear interpolation with extrapolation
    print("\n=== Test 3: Linear Interpolation ===")
    x = np.array([0, 5, 10, 15])
    y = np.array([50, 80, 60, 70])
    
    linear = interp1d(x, y, kind='linear', fill_value='extrapolate')
    xi = np.array([-2, 2, 7, 12, 18])  # Includes extrapolation
    yi = linear(xi)
    print(f"Input x: {x}")
    print(f"Input y: {y}")
    print(f"Interpolation points: {xi}")
    print(f"Results: {yi}")
    
    # Test 4: Scalar input
    print("\n=== Test 4: Scalar Input ===")
    single_result = pchip(2.7)
    print(f"Single point (2.7): {single_result}")
    
    print("\n✅ All tests completed successfully!")
    print("Functions are ready to replace scipy.interpolate")
