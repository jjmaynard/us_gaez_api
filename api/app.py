"""
Vercel serverless function entry point for GAEZ API.
"""
import sys
import os
from pathlib import Path

# Setup paths - add US_scripts to path before any other imports
base_path = Path(__file__).parent.parent
us_scripts_path = str(base_path / "code" / "US_scripts")
if us_scripts_path not in sys.path:
    sys.path.insert(0, us_scripts_path)

# Now import the FastAPI app
from api.main import app

# Vercel will automatically wrap this for serverless
# The app variable is what Vercel looks for
