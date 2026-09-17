"""
Download ERA5 10m wind (u10, v10) with a WIDE crop box, but only for the
calendar days of the NE-wind SWOT events already identified in
era5_swot_passes/narrow_box_v1/ne_wind_swot_matches.csv.

This gives wider spatial context (upstream Kuroshio included) for plotting
those specific confirmed events, without re-scanning/re-downloading the
whole SWOT mission over a huge area.

Requires: cdsapi + ~/.cdsapirc (already set up).
Run: python3 download_era5_wide_for_events.py
"""
import os
from collections import defaultdict

import pandas as pd
import cdsapi

# Wide box: SW(15N,120E) - NE(55N,180E), covers upstream + downstream +
# Extension of the Kuroshio, with margin.
LAT_MIN, LAT_MAX = 15, 55
LON_MIN, LON_MAX = 120, 180

MATCHES_CSV = "/home/takamio/Projects/pj1/era5_swot_passes/narrow_box_v1/ne_wind_swot_matches.csv"
OUTDIR = "/home/takamio/Projects/pj1/era5_swot_passes"


def event_days():
    df = pd.read_csv(MATCHES_CSV)
    df["mid"] = pd.to_datetime(df["mid"])
    days = sorted(set(df["mid"].dt.floor("D")))
    groups = defaultdict(set)
    for d in days:
        groups[(d.year, d.month)].add(d.day)
    return {k: sorted(v) for k, v in sorted(groups.items())}


def download(groups):
    c = cdsapi.Client()
    os.makedirs(OUTDIR, exist_ok=True)
    for (year, month), days in groups.items():
        out_path = os.path.join(OUTDIR, f"era5_wide_event_{year:04d}{month:02d}.nc")
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
    groups = event_days()
    print(f"{sum(len(v) for v in groups.values())} unique event days "
          f"across {len(groups)} year-months")
    download(groups)
    print("Done.")
