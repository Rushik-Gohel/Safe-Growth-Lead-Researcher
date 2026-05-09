"""Entry point for Streamlit UI."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Now run the Streamlit app
if __name__ == "__main__":
    import streamlit.web.cli as stcli
    import sys
    
    sys.argv = [
        "streamlit",
        "run",
        str(project_root / "src" / "ui" / "app.py"),
        "--server.port=8501",
        "--server.address=0.0.0.0"
    ]
    
    sys.exit(stcli.main())

# Made with Bob
