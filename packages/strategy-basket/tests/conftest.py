# ponytail: the package is not in .cursor/install.sh or the uv workspace yet (it merges after the main
# build), so tests put its src on sys.path; drop this once it is installed with the other packages.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
