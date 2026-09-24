import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Make the scanner package and the repo scripts importable from tests.
sys.path[:0] = [str(ROOT / "skills" / "complexity-optimizer" / "scripts"), str(ROOT / "scripts")]
