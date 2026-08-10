import sys
from pathlib import Path

# Allow `import app.xxx` when pytest is run from the repo root or from backend/.
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
