"""Entry point for Streamlit UI."""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add project root to Python path (parent of scripts folder)
project_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(project_root))

# Load .env file
load_dotenv(project_root / '.env')

# Set PYTHONPATH environment variable
os.environ['PYTHONPATH'] = str(project_root)

if __name__ == "__main__":
    # Import after path is set
    import subprocess
    
    app_path = project_root / "src" / "ui" / "app.py"
    
    port = os.environ.get("PORT", os.environ.get("UI_PORT", "8501"))
    
    # Run streamlit with proper Python path
    result = subprocess.run([
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        f"--server.port={port}",
        "--server.address=0.0.0.0"
    ], env={**os.environ, 'PYTHONPATH': str(project_root)})
    
    sys.exit(result.returncode)


