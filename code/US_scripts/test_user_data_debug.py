"""
Quick test script to debug user data integration and SQI calculations.
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Set up detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from api.models import (
    CalculationRequest, 
    Location, 
    UserData, 
    PlotDataHorizon, 
    SiteData,
    LabData
)
from api.service import GAEZCalculationService

def test_original_location():
    """Test at Kansas location from user's first example."""
    print("\n" + "="*80)
    print("TEST 0: Location 37.3988876, -101.0458298 WITHOUT user data (baseline)")
    print("="*80)
    
    request = CalculationRequest(
        location=Location(latitude=37.3988876, longitude=-101.0458298),
        crop_id="4",  # Maize
        input_level="L"
    )
    
    service = GAEZCalculationService()
    response = service.calculate_soil_quality(request)
    
    print(f"\nResults at Kansas location:")
    print(f"  SQ1 (Nutrient Avail): {response.soil_quality_indices.SQ1:.2f}")
    print(f"  SQ2 (Nutrient Ret):   {response.soil_quality_indices.SQ2:.2f}")
    print(f"  SQ3 (Rooting):        {response.soil_quality_indices.SQ3:.2f}")
    print(f"  SR (Overall):         {response.soil_quality_indices.SR:.2f}")
    print(f"  Component: {response.data_sources.ssurgo_component}")
    
    return response


def test_without_user_data():
    """Test at Nebraska location without user data."""
    print("\n" + "="*80)
    print("TEST 1: Location 41.2, -101.6 WITHOUT user data")
    print("="*80)
    
    request = CalculationRequest(
        location=Location(latitude=41.2, longitude=-101.6),
        crop_id="4",  # Maize
        input_level="L"
    )
    
    service = GAEZCalculationService()
    response = service.calculate_soil_quality(request)
    
    print(f"\nResults WITHOUT user data:")
    print(f"  SQ1 (Nutrient Avail): {response.soil_quality_indices.SQ1:.2f}")
    print(f"  SQ2 (Nutrient Ret):   {response.soil_quality_indices.SQ2:.2f}")
    print(f"  SQ3 (Rooting):        {response.soil_quality_indices.SQ3:.2f}")
    print(f"  SR (Overall):         {response.soil_quality_indices.SR:.2f}")
    print(f"  Component: {response.data_sources.ssurgo_component}")
    
    return response


def test_with_user_data():
    """Test at Nebraska location WITH user data."""
    print("\n" + "="*80)
    print("TEST 2: Location 41.2, -101.6 WITH user data")
    print("="*80)
    
    request = CalculationRequest(
        location=Location(latitude=41.2, longitude=-101.6),
        crop_id="4",  # Maize
        input_level="H",
        user_data=UserData(
            plot_data=[
                PlotDataHorizon(
                    hzdept=0,
                    hzdepb=25,
                    sand_pct=45.0,
                    silt_pct=35.0,
                    clay_pct=20.0,
                    ph_h2o=6.5,
                    organic_matter_pct=3.2
                )
            ],
            site_data=SiteData(
                drainage_cl="well drained",
                slope=2.5
            ),
            lab_data=[
                LabData(
                    depth_cm=15,
                    ph_h2o=6.8,
                    organic_carbon_pct=2.0,  # Will be converted to OM
                    cec_cmol_kg=18.5
                )
            ]
        )
    )
    
    service = GAEZCalculationService()
    response = service.calculate_soil_quality(request)
    
    print(f"\nResults WITH user data:")
    print(f"  SQ1 (Nutrient Avail): {response.soil_quality_indices.SQ1:.2f}")
    print(f"  SQ2 (Nutrient Ret):   {response.soil_quality_indices.SQ2:.2f}")
    print(f"  SQ3 (Rooting):        {response.soil_quality_indices.SQ3:.2f}")
    print(f"  SR (Overall):         {response.soil_quality_indices.SR:.2f}")
    print(f"  User plot data used: {response.data_sources.user_plot_data_used}")
    print(f"  User site data used: {response.data_sources.user_site_data_used}")
    print(f"  User lab data used: {response.data_sources.user_lab_data_used}")
    
    return response


def test_again_without_user_data():
    """Test again without user data to check for persistence."""
    print("\n" + "="*80)
    print("TEST 3: Location 41.2, -101.6 WITHOUT user data (checking persistence)")
    print("="*80)
    
    request = CalculationRequest(
        location=Location(latitude=41.2, longitude=-101.6),
        crop_id="4",  # Maize
        input_level="L"
    )
    
    service = GAEZCalculationService()
    response = service.calculate_soil_quality(request)
    
    print(f"\nResults WITHOUT user data (2nd time):")
    print(f"  SQ1 (Nutrient Avail): {response.soil_quality_indices.SQ1:.2f}")
    print(f"  SQ2 (Nutrient Ret):   {response.soil_quality_indices.SQ2:.2f}")
    print(f"  SQ3 (Rooting):        {response.soil_quality_indices.SQ3:.2f}")
    print(f"  SR (Overall):         {response.soil_quality_indices.SR:.2f}")
    
    return response


if __name__ == "__main__":
    try:
        # Run tests in sequence
        resp0 = test_original_location()
        resp1 = test_without_user_data()
        resp2 = test_with_user_data()
        resp3 = test_again_without_user_data()
        
        # Summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        print(f"Test 0 (Kansas, no user):  SR = {resp0.soil_quality_indices.SR:.2f}")
        print(f"Test 1 (Nebraska, no user): SR = {resp1.soil_quality_indices.SR:.2f}")
        print(f"Test 2 (with user data):   SR = {resp2.soil_quality_indices.SR:.2f}")
        print(f"Test 3 (no user data):     SR = {resp3.soil_quality_indices.SR:.2f}")
        
        if resp1.soil_quality_indices.SR != resp3.soil_quality_indices.SR:
            print("\n⚠️  WARNING: SR changed between test 1 and test 3!")
            print("   This indicates data persistence/corruption bug.")
        else:
            print("\n✓ SR consistent between test 1 and test 3 - no persistence issue.")
        
        if resp2.soil_quality_indices.SR == 0:
            print("\n⚠️  WARNING: Test 2 (with user data) returned SR=0!")
            print("   This indicates texture recalculation or SQI query issue.")
        else:
            print(f"\n✓ Test 2 (with user data) returned valid SR={resp2.soil_quality_indices.SR:.2f}")
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
