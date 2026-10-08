"""Original ReAct brain, isolated under the merged AI layer."""

from pathlib import Path
import sys

_brain_path = str(Path(__file__).resolve().parent)
if _brain_path not in sys.path:
    sys.path.insert(0, _brain_path)
