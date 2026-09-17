"""
Step 1 of the "metadata-first" workflow.

1. Query NASA CMR for every SWOT L2 LR SSH Expert granule whose footprint
   touches the Kuroshio region, across the whole mission (metadata only,
   no data download -- this part needs no credentials).
2. Group the resulting overpass dates by (year, month) and download ONLY
   the needed days of ERA5 10m wind (u10, v10), cropped to a small box
   around the Kuroshio region, via the CDS API.

Requires: `pip install cdsapi` and a working ~/.cdsapirc
(register at https://cds.climate.copernicus.eu/, get the API key from your
profile page, and accept the ERA5 dataset's terms of use once on the site).

Run this yourself after ~/.cdsapirc is in place:
    python3 download_era5_for_swot_passes.py
"""
import json
import os
import urllib.request
from collections import defaultdict
from pathlib import Path

import pandas as pd
import cdsapi

# ---------------------------------------------------------------------------
# Region of interest: SW(15N,120E) - NE(55N,180E), covering the whole
# Kuroshio path (upstream, downstream, and the Extension), not just the
# downstream/Extension box used previously.
# ---------------------------------------------------------------------------
LON_MIN, LON_MAX = 120, 180
LAT_MIN, LAT_MAX = 15, 55

# CMR area="North, West, South, East" for the SWOT search (same box)
CMR_COLLECTION_ID = "C2799465497-POCLOUD"  # SWOT_L2_LR_SSH_EXPERT_2.0 (POCLOUD)
TEMPORAL_START = "2023-01-01T00:00:00Z"
TEMPORAL_END = "2026-09-15T00:00:00Z"  # extend as needed

BASE = Path(os.environ["RESEARCH_DATA"])
OUTDIR = BASE / "ERA5" / "wind10m_NP_2023-2025"
GRANULE_CACHE = BASE / "derived" / "pj1" / "tables" / "swot_granules.json"


def fetch_swot_granule_metadata():
    """Metadata-only CMR query: granule name + start/end time. No science
    data is downloaded here (0 bytes of SWOT swath data). Paginated since
    a wide box easily exceeds a single page (CMR max page_size is 2000)."""
    os.makedirs(GRANULE_CACHE.parent, exist_ok=True)
    page_size = 2000
    entries = []
    page_num = 1
    while True:
        url = (
            "https://cmr.earthdata.nasa.gov/search/granules.json"
            f"?collection_concept_id={CMR_COLLECTION_ID}"
            f"&bounding_box={LON_MIN},{LAT_MIN},{LON_MAX},{LAT_MAX}"
            f"&temporal={TEMPORAL_START},{TEMPORAL_END}"
            f"&page_size={page_size}&page_num={page_num}"
        )
        with urllib.request.urlopen(url) as resp:
            data = json.load(resp)
        page_entries = data["feed"]["entry"]
        entries.extend(page_entries)
        print(f"  fetched page {page_num}: {len(page_entries)} granules "
              f"(running total {len(entries)})")
        if len(page_entries) < page_size:
            break
        page_num += 1
    with open(GRANULE_CACHE, "w") as f:
        json.dump(entries, f)
    print(f"Found {len(entries)} SWOT passes touching the region "
          f"({TEMPORAL_START} - {TEMPORAL_END}).")
    return entries


def granules_to_dates(entries):
    times = pd.to_datetime([e["time_start"] for e in entries]).tz_localize(None)
    return sorted(set(times.floor("D")))


def group_by_year_month(dates):
    """CDS API takes year/month/day as independent lists (Cartesian
    product), so to fetch only the needed days without over-fetching we
    must issue one request per (year, month) with just that month's days."""
    groups = defaultdict(set)
    for d in dates:
        groups[(d.year, d.month)].add(d.day)
    return {k: sorted(v) for k, v in sorted(groups.items())}


def download_era5(groups):
    c = cdsapi.Client()
    os.makedirs(OUTDIR, exist_ok=True)
    for (year, month), days in groups.items():
        out_path = os.path.join(OUTDIR, f"era5_wind_{year:04d}{month:02d}.nc")
        if os.path.exists(out_path):
            print(f"skip (already downloaded): {out_path}")
            continue
        print(f"requesting {year}-{month:02d}, days={days} -> {out_path}")
        c.retrieve(
            "reanalysis-era5-single-levels",
            {
                "product_type": "reanalysis",
                "format": "netcdf",
                "variable": ["10m_u_component_of_wind", "10m_v_component_of_wind"],
                "year": f"{year:04d}",
                "month": f"{month:02d}",
                "day": [f"{d:02d}" for d in days],
                "time": [f"{h:02d}:00" for h in range(24)],
                "area": [LAT_MAX, LON_MIN, LAT_MIN, LON_MAX],  # N, W, S, E
                "grid": [0.25, 0.25],
            },
            out_path,
        )
        print(f"saved {out_path}")


if __name__ == "__main__":
    entries = fetch_swot_granule_metadata()
    dates = granules_to_dates(entries)
    print(f"unique calendar days needed: {len(dates)}")
    groups = group_by_year_month(dates)
    print(f"-> grouped into {len(groups)} CDS requests (one per year-month)")
    download_era5(groups)
    print("Done. Next: run list_ne_episodes_kuroshio_box.py")
