import os
from pathlib import Path

# Get the project root directory (2 levels up from this file: US_scripts -> code -> root)
_current_file = Path(__file__)
_project_root = _current_file.parent.parent.parent

# file paths for GAEZ crop requirement lookup tables (GAEZ_crop_req.py)
# Use relative paths from project root
profile_req_url = str(_project_root / "data" / "raw_data" / "GAEZ_profile_req_rf.csv")
phase_req_url = str(_project_root / "data" / "raw_data" / "GAEZ_phase_req_rf.csv")
drainage_req_url = str(_project_root / "data" / "raw_data" / "GAEZ_drainage_req_rf.csv")
texture_req_url = str(_project_root / "data" / "raw_data" / "GAEZ_text_req_rf.csv")
terrain_req_url = str(_project_root / "data" / "raw_data" / "GAEZ_terrain_req_rf.csv")

# define top and bottom depth column names for depth weight calculations (GAEZ_SQI_functions.py)
class hz_names:
    top_col_name = 'hzdept_r'
    bottom_col_name = 'hzdepb_r'
