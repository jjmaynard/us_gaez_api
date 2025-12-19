"""
Overlay user-provided horizon data onto SSURGO map data.

This module provides a function to properly merge user field measurements
with SSURGO database horizons, preserving subsurface data when users only
measure surface horizons.
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


def overlay_user_horizons(user_horizons: pd.DataFrame, ssurgo_data: pd.DataFrame, bedrock_depth: float = None) -> pd.DataFrame:
    """
    Overlay user-provided horizon measurements onto SSURGO data.
    
    Key behavior:
    - User data for surface horizons (e.g., 0-25 cm) replaces SSURGO data for those depths
    - SSURGO data for deeper horizons is preserved (e.g., 25-200 cm) 
    - If bedrock_depth is provided, profile is truncated to that depth
    - If no bedrock_depth, assumes soil continues to full SSURGO depth
    - Only updates raw measurement columns, preserves derived/calculated columns
    
    Args:
        user_horizons: DataFrame with columns like hzdept, hzdepb, sandtotal, claytotal, ph, etc.
        ssurgo_data: DataFrame with SSURGO horizon data (after phase classification)
        bedrock_depth: Optional bedrock depth in cm. If None, assumes deep soil (>200 cm)
    
    Returns:
        DataFrame with user data overlaid on SSURGO data
    """
    result = ssurgo_data.copy()
    
    # Column mapping from API names to SSURGO raw measurement names
    # ONLY map to _r (raw) columns to avoid breaking derived columns
    column_mapping = {
        'sandtotal': 'sandtotal_r',
        'silttotal': 'silttotal_r', 
        'claytotal': 'claytotal_r',
        'om': 'om_r',
        'ph': 'ph1to1h2o_r',
        'cecs': 'cec7_r',
        'ec': 'ec_r',
        'caco3': 'caco3_r',
        'gypsum': 'gypsum_r',
        'DB': 'dbovendry_r',
        'CF': 'total_frag_volume'  # This is aggregated coarse fragments
    }
    
    # Get depth columns from SSURGO
    if 'hzdept_r' in result.columns and 'hzdepb_r' in result.columns:
        depth_top_col = 'hzdept_r'
        depth_bot_col = 'hzdepb_r'
    else:
        logger.warning("SSURGO data missing standard depth columns (hzdept_r, hzdepb_r)")
        return result
    
    # Apply bedrock depth truncation if specified
    if bedrock_depth is not None and bedrock_depth < 200:
        logger.info(f"Truncating profile to bedrock depth: {bedrock_depth} cm")
        result = result[result[depth_top_col] < bedrock_depth].copy()
        # Adjust bottom depth of last horizon if it extends past bedrock
        if len(result) > 0 and result.iloc[-1][depth_bot_col] > bedrock_depth:
            result.iloc[-1, result.columns.get_loc(depth_bot_col)] = bedrock_depth
    
    # For each user horizon, find overlapping SSURGO horizons and update properties
    for idx, user_hz in user_horizons.iterrows():
        user_top = user_hz['hzdept']
        user_bot = user_hz['hzdepb']
        
        # Find SSURGO horizons that overlap with this user horizon
        # Overlap: user_top < ssurgo_bot AND user_bot > ssurgo_top
        overlapping = (
            (result[depth_top_col] < user_bot) &
            (result[depth_bot_col] > user_top)
        )
        
        if not overlapping.any():
            continue
        
        # Update properties for overlapping horizons
        for api_col, ssurgo_col in column_mapping.items():
            if api_col in user_hz.index and ssurgo_col in result.columns:
                value = user_hz[api_col]
                if pd.notna(value):  # Only update if user provided a value
                    result.loc[overlapping, ssurgo_col] = value
                    logger.debug(f"Updated {ssurgo_col} for depth {user_top}-{user_bot} cm: {value}")
    
    logger.info(f"Overlaid {len(user_horizons)} user horizons onto {len(result)} SSURGO horizons")
    
    return result
