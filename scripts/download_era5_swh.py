"""
Download ERA5 significant wave height (swh) for the same days and the same
box as the 10 m wind already fetched by download_era5_for_swot_passes.py.

The day list is read from the cached SWOT granule metadata, so wind and
wave cover exactly the same hours. The grid is the wave model's native
0.5 deg (asking for 0.25 deg would only interpolate).

Output: $RESEARCH_DATA/ERA5/swh_NP_2023-2025/era5_swh_YYYYMM.nc
"""
import json
import os
from collections import defaultdict
from pathlib import Path

import pandas as pd
import cdsapi

# same box as the wind download
LON_MIN, LON_MAX = 120, 180
LAT_MIN, LAT_MAX = 15, 55

BASE = Path(os.environ["RESEARCH_DATA"])
GRANULE_CACHE = BASE / "derived" / "pj1" / "tables" / "swot_granules.json"
OUTDIR = BASE / "ERA5" / "swh_NP_2023-2025"


def days_by_year_month():
    entries = json.load(open(GRANULE_CACHE))
    times = pd.to_datetime([e["time_start"] for e in entries]).tz_localize(None)
    groups = defaultdict(set)
    for d in sorted(set(times.floor("D"))):
        groups[(d.year, d.month)].add(d.day)
    return {k: sorted(v) for k, v in sorted(groups.items())}


def main():
    groups = days_by_year_month()
    print(f"{sum(len(v) for v in groups.values())} days across {len(groups)} "
          f"year-months")
    os.makedirs(OUTDIR, exist_ok=True)
    c = cdsapi.Client()
    for (year, month), days in groups.items():
        out_path = OUTDIR / f"era5_swh_{year:04d}{month:02d}.nc"
        if out_path.exists():
            print(f"skip (already downloaded): {out_path}")
            continue
        print(f"requesting {year}-{month:02d}, {len(days)} days -> {out_path}")
        c.retrieve(
            "reanalysis-era5-single-levels",
            {
                "product_type": "reanalysis",
                "format": "netcdf",
                "variable": ["significant_height_of_combined_wind_waves_and_swell"],
                "year": f"{year:04d}",
                "month": f"{month:02d}",
                "day": [f"{d:02d}" for d in days],
                "time": [f"{h:02d}:00" for h in range(24)],
                "area": [LAT_MAX, LON_MIN, LAT_MIN, LON_MAX],  # N, W, S, E
                "grid": [0.5, 0.5],
            },
            str(out_path),
        )
        print(f"saved {out_path}")
    print("Done.")


if __name__ == "__main__":
    main()
