"""Offline SoilGrids v2.0 cache (ADR 0006).

`fetch` clips ISRIC's public VRT/COG layers into `data/cache/soilgrids/`;
`estimate_at` reads only that cache. N-only: no phosphorus/potassium anywhere.
"""

from data_sources.soilgrids.catalog import (
    ALLOWED_PROPERTIES,
    UnsupportedDepthError,
    UnsupportedPropertyError,
)
from data_sources.soilgrids.estimate import CacheMissingError, NoDataError, estimate_at
from data_sources.soilgrids.fetch import FetchError, fetch
from data_sources.soilgrids.models import EstimateValue, SoilEstimate

__all__ = [
    "ALLOWED_PROPERTIES",
    "CacheMissingError",
    "EstimateValue",
    "FetchError",
    "NoDataError",
    "SoilEstimate",
    "UnsupportedDepthError",
    "UnsupportedPropertyError",
    "estimate_at",
    "fetch",
]
