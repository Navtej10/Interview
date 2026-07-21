import sys
from pathlib import Path

# Ensure `app` package is importable from tests
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
