"""Entry point for FastAPI backend."""

import sys
import os
from pathlib import Path

# Add project root to Python path (parent of scripts folder)
project_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", os.environ.get("API_PORT", "8000")))
    
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )


