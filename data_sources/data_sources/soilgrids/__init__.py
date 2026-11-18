"""Offline SoilGrids v2.0 cache (ADR 0006).

`fetch` clips ISRIC's public VRT/COG layers into `data/cache/soilgrids/`;
`estimate_at` reads only that cache. N-only: no phosphorus/potassium anywhere.
"""

from data_sources.soilgrids.catalog import (
    ALLOWED_PROPERTIES,
    ATTRIBUTION,
    CITATION,
    UnsupportedDepthError,
    UnsupportedPropertyError,
)
from data_sources.soilgrids.estimate import (
    CacheMissingError,
    NoDataError,
    OutsideCacheError,
    estimate_at,
    lookup_estimate,
)
from data_sources.soilgrids.fetch import FetchError, fetch
from data_sources.soilgrids.models import EstimateValue, NoEstimate, SoilEstimate, SoilLookup

__all__ = [
    "ALLOWED_PROPERTIES",
    "ATTRIBUTION",
    "CITATION",
    "CacheMissingError",
    "EstimateValue",
    "FetchError",
    "NoDataError",
    "NoEstimate",
    "OutsideCacheError",
    "SoilEstimate",
    "SoilLookup",
    "UnsupportedDepthError",
    "UnsupportedPropertyError",
    "estimate_at",
    "fetch",
    "lookup_estimate",
]
