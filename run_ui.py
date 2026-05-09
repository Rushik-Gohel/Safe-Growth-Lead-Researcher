"""Entry point for Streamlit UI."""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent.resolve()
sys.path.insert(0, str(project_root))

# Load .env file
load_dotenv(project_root / '.env')

# Set PYTHONPATH environment variable
os.environ['PYTHONPATH'] = str(project_root)

if __name__ == "__main__":
    # Import after path is set
    import subprocess
    
    app_path = project_root / "src" / "ui" / "app.py"
    
    # Run streamlit with proper Python path
    result = subprocess.run([
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.port=8501",
        "--server.address=0.0.0.0"
    ], env={**os.environ, 'PYTHONPATH': str(project_root)})
    
    sys.exit(result.returncode)

# Made with Bob
