"""
Integrate user-provided data (plot, site, lab) with SSURGO map data.

Priority order: Lab data > Plot/Site data > Map data (SSURGO)
- Lab data supersedes plot data supersedes map data for the same property
- User data overlays on SSURGO - preserves unmeasured depths
- Recalculates derived columns (texture class) when particle size changes
"""

import pandas as pd
import numpy as np
import logging

# Import texture classification functions
try:
    from GAEZ_SSURGO_data import gettt, getTXT_id, getTextGroup
    TEXTURE_FUNCTIONS_AVAILABLE = True
except ImportError:
    TEXTURE_FUNCTIONS_AVAILABLE = False
    logging.warning("Texture classification functions not available")

logger = logging.getLogger(__name__)


def integrate_plot_data(user_horizons: pd.DataFrame, ssurgo_data: pd.DataFrame) -> pd.DataFrame:
    """
    Integrate user plot (field) measurements with SSURGO data.
    
    Updates raw measurement columns (_r suffix) for horizons where user provided data.
    Preserves SSURGO data for deeper unmeasured horizons.
    
    Args:
        user_horizons: DataFrame with API columns (hzdept, hzdepb, sandtotal, claytotal, ph, om, etc.)
        ssurgo_data: DataFrame with SSURGO data (after phase classification)
    
    Returns:
        Updated DataFrame with user plot data overlaid
    """
    result = ssurgo_data.copy()
    
    logger.info(f"SSURGO data columns: {list(result.columns)}")
    
    # Mapping from API column names to SSURGO columns
    # Note: After phase classification, columns are renamed (sand not sandtotal_r)
    column_map = {
        'sandtotal': 'sand',
        'silttotal': 'silt',
        'claytotal': 'clay',
        'om': 'om',
        'ph': 'ph',
        'DB': 'db',
        'CF': 'fragvol',
        'cecs': 'cecs',
        'ec': 'ec',
        'caco3': 'caco3',
        'gypsum': 'gypsum'
    }
    
    # Get SSURGO depth columns
    depth_top_col = 'hzdept_r'
    depth_bot_col = 'hzdepb_r'
    
    if depth_top_col not in result.columns or depth_bot_col not in result.columns:
        logger.warning("Cannot integrate plot data - missing depth columns")
        return result
    
    # For each user horizon, find overlapping SSURGO horizons
    updated_count = 0
    texture_updated_rows = []  # Track rows where sand/silt/clay changed
    
    for idx, user_hz in user_horizons.iterrows():
        user_top = user_hz['hzdept']
        user_bot = user_hz['hzdepb']
        
        logger.info(f"User horizon {idx}: depth {user_top}-{user_bot} cm, data: {user_hz.to_dict()}")
        
        # Find overlapping SSURGO horizons
        overlapping = (
            (result[depth_top_col] < user_bot) &
            (result[depth_bot_col] > user_top)
        )
        
        if not overlapping.any():
            logger.warning(f"No overlapping SSURGO horizons for user horizon {idx}")
            continue
        
        # Track if texture components changed (need to recalculate texture class)
        texture_changed = False
        
        # Update each mapped property
        for api_col, ssurgo_col in column_map.items():
            if api_col in user_hz.index and ssurgo_col in result.columns:
                value = user_hz[api_col]
                if pd.notna(value):
                    logger.info(f"  Updating {ssurgo_col} from {result.loc[overlapping, ssurgo_col].values} to {value}")
                    result.loc[overlapping, ssurgo_col] = value
                    updated_count += 1
                    # Track if particle size changed
                    if api_col in ['sandtotal', 'silttotal', 'claytotal']:
                        texture_changed = True
            else:
                if api_col in user_hz.index:
                    logger.debug(f"  Column {ssurgo_col} not in SSURGO data (api_col={api_col})")
                else:
                    logger.debug(f"  {api_col} not in user data")
        
        # If texture components changed, mark rows for recalculation
        if texture_changed:
            texture_updated_rows.extend(result[overlapping].index.tolist())
    
    # Recalculate texture class for affected horizons
    if texture_updated_rows and TEXTURE_FUNCTIONS_AVAILABLE:
        texture_updated_rows = list(set(texture_updated_rows))  # Remove duplicates
        logger.info(f"Recalculating texture class for {len(texture_updated_rows)} horizons")
        
        for idx in texture_updated_rows:
            sand = result.loc[idx, 'sand']
            clay = result.loc[idx, 'clay']
            silt = result.loc[idx, 'silt']
            
            if pd.notna(sand) and pd.notna(clay) and pd.notna(silt):
                try:
                    # Recalculate texture class
                    texture_class = gettt(sand=sand, silt=silt, clay=clay)
                    if texture_class:
                        result.loc[idx, 'texture'] = texture_class
                        
                        # Recalculate texture class ID
                        try:
                            texture_id = getTXT_id(texture_class)
                            if pd.notna(texture_id):
                                result.loc[idx, 'texture_class_id'] = int(texture_id)
                                logger.info(f"Row {idx}: Recalculated texture from sand={sand:.1f}%, silt={silt:.1f}%, clay={clay:.1f}% -> '{texture_class}' (ID={int(texture_id)})")
                            else:
                                logger.error(f"Row {idx}: getTXT_id returned NaN/None for texture='{texture_class}'. This will cause SQI calculation failures!")
                        except Exception as e:
                            logger.error(f"Row {idx}: Failed to get texture_class_id for '{texture_class}': {e}")
                        
                        # Recalculate texture group (PSCL)
                        try:
                            pscl = getTextGroup(texture_class)
                            if pd.notna(pscl):
                                result.loc[idx, 'pscl'] = pscl
                                logger.debug(f"Row {idx}: Updated pscl to {pscl}")
                        except Exception as e:
                            logger.warning(f"Row {idx}: Failed to get pscl for {texture_class}: {e}")
                    else:
                        logger.error(f"Row {idx}: gettt returned None/empty for sand={sand:.1f}%, silt={silt:.1f}%, clay={clay:.1f}%")
                except Exception as e:
                    logger.warning(f"Failed to recalculate texture for row {idx}: {e}")
    
    logger.info(f"Plot data: Updated {updated_count} property values in overlapping horizons")
    return result


def integrate_site_data(site_info: dict, ssurgo_data: pd.DataFrame) -> pd.DataFrame:
    """
    Integrate user site characteristics with SSURGO data.
    
    Updates site-level properties that apply to entire profile.
    
    Args:
        site_info: Dict with site properties (drainage_class, slope, elevation, etc.)
        ssurgo_data: DataFrame with SSURGO data
    
    Returns:
        Updated DataFrame with site data integrated
    """
    result = ssurgo_data.copy()
    
    updated = []
    
    # Drainage class - affects all horizons
    if 'drainage_cl' in site_info and pd.notna(site_info['drainage_cl']):
        if 'drainagecl' in result.columns:
            result['drainagecl'] = site_info['drainage_cl']
            updated.append('drainage_class')
    
    # Slope - affects all horizons
    if 'slope' in site_info and pd.notna(site_info['slope']):
        result['slope'] = site_info['slope']
        updated.append('slope')
    
    # Elevation - affects all horizons  
    if 'elevation' in site_info and pd.notna(site_info['elevation']):
        if 'elev_r' in result.columns:
            result['elev_r'] = site_info['elevation']
            updated.append('elevation')
    
    # Bedrock depth - truncate profile if needed
    if 'bedrock_depth' in site_info and pd.notna(site_info['bedrock_depth']):
        bedrock = site_info['bedrock_depth']
        if bedrock < 200 and 'hzdept_r' in result.columns:
            # Truncate to bedrock depth
            result = result[result['hzdept_r'] < bedrock].copy()
            # Adjust last horizon bottom
            if len(result) > 0 and 'hzdepb_r' in result.columns:
                if result.iloc[-1]['hzdepb_r'] > bedrock:
                    result.iloc[-1, result.columns.get_loc('hzdepb_r')] = bedrock
            updated.append('bedrock_depth')
    
    if updated:
        logger.info(f"Site data: Updated {', '.join(updated)}")
    
    return result


def integrate_lab_data(lab_samples: pd.DataFrame, ssurgo_data: pd.DataFrame) -> pd.DataFrame:
    """
    Integrate laboratory measurements with SSURGO data.
    
    Lab data has highest priority - supersedes both plot and map data.
    
    Args:
        lab_samples: DataFrame with API columns (depth_cm, ph_h2o, organic_carbon_pct, cec_cmol_kg, etc.)
        ssurgo_data: DataFrame with SSURGO data
    
    Returns:
        Updated DataFrame with lab data integrated
    """
    result = ssurgo_data.copy()
    
    # Mapping from API column names to SSURGO columns
    column_map = {
        'ph_h2o': 'ph1to1h2o_r',
        'organic_carbon_pct': 'om_r',  # Will convert OC to OM
        'cec_cmol_kg': 'cec7_r',
        'ec_ds_m': 'ec_r',
        'esp_pct': 'esp_r',
        'base_sat_pct': 'sumbases_r',
        'caco3_pct': 'caco3_r',
        'gypsum_pct': 'gypsum_r'
    }
    
    depth_top_col = 'hzdept_r'
    depth_bot_col = 'hzdepb_r'
    
    if depth_top_col not in result.columns or depth_bot_col not in result.columns:
        logger.warning("Cannot integrate lab data - missing depth columns")
        return result
    
    # For each lab sample, find the horizon it belongs to
    updated_count = 0
    for idx, sample in lab_samples.iterrows():
        sample_depth = sample['depth_cm']
        
        # Find horizon containing this depth
        in_horizon = (
            (result[depth_top_col] <= sample_depth) &
            (result[depth_bot_col] > sample_depth)
        )
        
        if not in_horizon.any():
            logger.warning(f"Lab sample at {sample_depth} cm not within any horizon")
            continue
        
        # Update properties from this lab sample
        for api_col, ssurgo_col in column_map.items():
            if api_col in sample.index and ssurgo_col in result.columns:
                value = sample[api_col]
                if pd.notna(value):
                    # Convert OC to OM if needed (OM ≈ OC * 1.724)
                    if api_col == 'organic_carbon_pct' and ssurgo_col == 'om_r':
                        value = value * 1.724
                    
                    result.loc[in_horizon, ssurgo_col] = value
                    updated_count += 1
    
    logger.info(f"Lab data: Updated {updated_count} property values from {len(lab_samples)} samples")
    return result


def integrate_all_user_data(user_data, ssurgo_data: pd.DataFrame) -> tuple:
    """
    Integrate all user data with SSURGO following priority: Lab > Plot/Site > Map.
    
    Args:
        user_data: UserData object with optional plot_data, site_data, lab_data
        ssurgo_data: DataFrame with SSURGO data (after phase classification)
    
    Returns:
        Tuple of (updated_data, sources_info dict)
    """
    result = ssurgo_data.copy()
    sources = {
        'user_plot_data_used': False,
        'user_site_data_used': False,
        'user_lab_data_used': False
    }
    
    try:
        # Step 1: Apply plot data (lowest user priority, but higher than map)
        if user_data.plot_data and len(user_data.plot_data) > 0:
            # Convert plot data to DataFrame
            plot_records = []
            for hz in user_data.plot_data:
                record = {'hzdept': hz.top_depth, 'hzdepb': hz.bottom_depth}
                if hz.sand_pct is not None: record['sandtotal'] = hz.sand_pct
                if hz.silt_pct is not None: record['silttotal'] = hz.silt_pct
                if hz.clay_pct is not None: record['claytotal'] = hz.clay_pct
                if hz.ph is not None: record['ph'] = hz.ph
                if hz.organic_matter_pct is not None: record['om'] = hz.organic_matter_pct
                if hz.bulk_density is not None: record['DB'] = hz.bulk_density
                if hz.coarse_fragments_pct is not None: record['CF'] = hz.coarse_fragments_pct
                if hz.cec_soil is not None: record['cecs'] = hz.cec_soil
                if hz.ec is not None: record['ec'] = hz.ec
                if hz.caco3_pct is not None: record['caco3'] = hz.caco3_pct
                if hz.gypsum_pct is not None: record['gypsum'] = hz.gypsum_pct
                plot_records.append(record)
            
            plot_df = pd.DataFrame(plot_records)
            logger.info(f"Plot data DataFrame columns: {list(plot_df.columns)}")
            logger.info(f"Plot data values: {plot_df.to_dict('records')}")
            result = integrate_plot_data(plot_df, result)
            sources['user_plot_data_used'] = True
            logger.info(f"Integrated {len(plot_records)} plot horizons")
        
        # Step 2: Apply site data (affects entire profile)
        if user_data.site_data:
            site_dict = {}
            if user_data.site_data.drainage_class: site_dict['drainage_cl'] = user_data.site_data.drainage_class
            if user_data.site_data.slope_pct is not None: site_dict['slope'] = user_data.site_data.slope_pct
            if user_data.site_data.elevation_m is not None: site_dict['elevation'] = user_data.site_data.elevation_m
            if user_data.site_data.bedrock_depth_cm is not None: site_dict['bedrock_depth'] = user_data.site_data.bedrock_depth_cm
            
            if site_dict:
                result = integrate_site_data(site_dict, result)
                sources['user_site_data_used'] = True
                logger.info("Integrated site data")
        
        # Step 3: Apply lab data (highest priority - supersedes plot and map)
        if user_data.lab_data and len(user_data.lab_data) > 0:
            lab_records = []
            for sample in user_data.lab_data:
                record = {'depth_cm': sample.depth_cm}
                if sample.ph_h2o is not None: record['ph_h2o'] = sample.ph_h2o
                if sample.organic_carbon_pct is not None: record['organic_carbon_pct'] = sample.organic_carbon_pct
                if sample.cec_cmol_kg is not None: record['cec_cmol_kg'] = sample.cec_cmol_kg
                if sample.ec_ds_m is not None: record['ec_ds_m'] = sample.ec_ds_m
                if sample.esp_pct is not None: record['esp_pct'] = sample.esp_pct
                if sample.base_saturation_pct is not None: record['base_sat_pct'] = sample.base_saturation_pct
                if sample.caco3_pct is not None: record['caco3_pct'] = sample.caco3_pct
                if sample.gypsum_pct is not None: record['gypsum_pct'] = sample.gypsum_pct
                lab_records.append(record)
            
            lab_df = pd.DataFrame(lab_records)
            result = integrate_lab_data(lab_df, result)
            sources['user_lab_data_used'] = True
            logger.info(f"Integrated {len(lab_records)} lab samples")
        
    except Exception as e:
        logger.error(f"Error integrating user data: {e}", exc_info=True)
        # Return original data if integration fails
        return ssurgo_data, sources
    
    return result, sources
