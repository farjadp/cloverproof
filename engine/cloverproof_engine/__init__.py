"""CloverProof engine: pure calculation library (no I/O, no DB calls).

File reading is confined to `loaders.py` (packs, golden cases).
"""

from cloverproof_engine.engine import recommend
from cloverproof_engine.version import ENGINE_VERSION

__version__ = ENGINE_VERSION

__all__ = ["ENGINE_VERSION", "__version__", "recommend"]
