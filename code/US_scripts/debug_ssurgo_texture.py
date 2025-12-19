"""
Debug script to examine SSURGO data before and after user data integration.
"""

import sys
import logging
from pathlib import Path
import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO)

from GAEZ_SSURGO_data import get_SSURGO_data, gettt, getTXT_id
from GAEZ_US_phase_calc import classify_gaez_v4_phases

# Test Nebraska location  
lat = 41.2
lon = -101.6

print("="*80)
print(f"Fetching SSURGO data for ({lat}, {lon})")
print("="*80)

# Get SSURGO data
ssurgo_df = get_SSURGO_data(lat, lon)

if ssurgo_df is None or len(ssurgo_df) == 0:
    print("No SSURGO data found!")
    sys.exit(1)

print(f"\nRetrieved {len(ssurgo_df)} horizons")
print("\nKey columns:")
print(ssurgo_df[['hzdept_r', 'hzdepb_r', 'sandtotal_r', 'silt total_r', 'claytotal_r', 
                 'texcl', 'texture_class_id']].to_string())

print("\n" + "="*80)
print("Classifying phases")
print("="*80)

ssurgo_with_phases = classify_gaez_v4_phases(ssurgo_df)

print("\nAfter phase classification:")
print(ssurgo_with_phases[['hzdept_r', 'hzdepb_r', 'sandtotal_r', 'silttotal_r', 'claytotal_r',
                          'texcl', 'texture_class_id']].to_string())

# Check if texture_class_id is valid
print("\n" + "="*80)
print("Texture class ID validation")
print("="*80)

for idx, row in ssurgo_with_phases.iterrows():
    texture_id = row['texture_class_id']
    texture_name = row['texcl']
    sand = row['sandtotal_r']
    silt = row['silttotal_r']
    clay = row['claytotal_r']
    
    print(f"\nHorizon {idx} ({row['hzdept_r']}-{row['hzdepb_r']} cm):")
    print(f"  Sand={sand:.1f}%, Silt={silt:.1f}%, Clay={clay:.1f}%")
    print(f"  SSURGO texture: '{texture_name}' (ID={texture_class_id})")
    
    # Recalculate texture
    calc_texture = gettt(sand, silt, clay)
    calc_id = getTXT_id(calc_texture) if calc_texture else None
    
    print(f"  Calculated texture: '{calc_texture}' (ID={calc_id})")
    
    if pd.isna(texture_id):
        print(f"  ⚠️  WARNING: texture_class_id is NaN!")
    elif texture_id != calc_id:
        print(f"  ⚠️  WARNING: ID mismatch (SSURGO={texture_id} vs calculated={calc_id})")
