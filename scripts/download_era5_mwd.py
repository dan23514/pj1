"""
Download ERA5 mean wave direction (mwd) for exactly the same hours and box
as the significant wave height already fetched by download_era5_swh.py.

The day list is read from the existing swh files themselves (not from the
SWOT granule cache), so mwd and swh are guaranteed to match hour for hour.
Grid is the wave model's native 0.5 deg, as for swh.

mwd is the direction waves come FROM, degrees clockwise from north
(meteorological convention), for the combined wind-sea + swell spectrum.

Output: $RESEARCH_DATA/ERA5/mwd_NP_2023-2025/era5_mwd_YYYYMM.nc
"""
import os
from pathlib import Path

import pandas as pd
import xarray as xr
import cdsapi

# same box as the swh / wind downloads
LON_MIN, LON_MAX = 120, 180
LAT_MIN, LAT_MAX = 15, 55

BASE = Path(os.environ["RESEARCH_DATA"])
SWH_DIR = BASE / "ERA5" / "swh_NP_2023-2025"
OUTDIR = BASE / "ERA5" / "mwd_NP_2023-2025"


def days_by_year_month():
    """{(year, month): [days]} taken from the valid_time of each swh file."""
    groups = {}
    for f in sorted(SWH_DIR.glob("era5_swh_*.nc")):
        with xr.open_dataset(f) as ds:
            times = pd.to_datetime(ds["valid_time"].values)
        days = sorted(set(times.day))
        year, month = times[0].year, times[0].month
        assert (times.year == year).all() and (times.month == month).all(), f
        groups[(year, month)] = days
    return groups


def main():
    groups = days_by_year_month()
    print(f"{sum(len(v) for v in groups.values())} days across {len(groups)} "
          f"year-months (from {SWH_DIR})")
    os.makedirs(OUTDIR, exist_ok=True)
    c = cdsapi.Client()
    for (year, month), days in groups.items():
        out_path = OUTDIR / f"era5_mwd_{year:04d}{month:02d}.nc"
        if out_path.exists():
            print(f"skip (already downloaded): {out_path}")
            continue
        print(f"requesting {year}-{month:02d}, {len(days)} days -> {out_path}")
        c.retrieve(
            "reanalysis-era5-single-levels",
            {
                "product_type": "reanalysis",
                "format": "netcdf",
                "variable": ["mean_wave_direction"],
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
