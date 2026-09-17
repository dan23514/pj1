"""
Step 2 of the "metadata-first" workflow.

Run this AFTER download_era5_for_swot_passes.py has finished downloading
the monthly era5_wind_YYYYMM.nc files into era5_swot_passes/.

For every SWOT overpass, look up the ERA5 wind at the nearest hour,
averaged over the Kuroshio box (135-150E, 35-45N), and flag the ones
where the wind is blowing from the northeast.
"""
import glob
import json
import os

import numpy as np
import pandas as pd
import xarray as xr

OUTDIR = "/home/takamio/Projects/pj1/era5_swot_passes"
GRANULE_CACHE = os.path.join(OUTDIR, "swot_granules.json")

# Kuroshio region average box (same as the earlier ERA5-only analysis)
LAT_MIN, LAT_MAX = 35, 45
LON_MIN, LON_MAX = 135, 150

NE_DIR_MIN, NE_DIR_MAX = 22.5, 67.5
NE_SPEED_MIN = 3.0


def load_swot_passes():
    with open(GRANULE_CACHE) as f:
        entries = json.load(f)
    df = pd.DataFrame([
        {
            "title": e["title"],
            "start": pd.Timestamp(e["time_start"]).tz_localize(None),
            "end": pd.Timestamp(e["time_end"]).tz_localize(None),
        }
        for e in entries
    ])
    df["mid"] = df["start"] + (df["end"] - df["start"]) / 2
    return df.sort_values("mid").reset_index(drop=True)


def load_era5():
    files = sorted(glob.glob(os.path.join(OUTDIR, "era5_wind_??????.nc")))
    if not files:
        raise FileNotFoundError(
            f"No era5_wind_*.nc files found in {OUTDIR}. "
            "Run download_era5_for_swot_passes.py first."
        )
    ds = xr.open_mfdataset(files, combine="by_coords")
    mask = (ds.latitude > LAT_MIN) & (ds.latitude < LAT_MAX) & \
           (ds.longitude > LON_MIN) & (ds.longitude < LON_MAX)
    u = ds["u10"].where(mask).mean(dim=["latitude", "longitude"], skipna=True)
    v = ds["v10"].where(mask).mean(dim=["latitude", "longitude"], skipna=True)
    time_dim = "valid_time" if "valid_time" in ds.dims else "time"
    speed = np.sqrt(u**2 + v**2)
    dir_from = (np.degrees(np.arctan2(u, v)) + 180) % 360
    wind_df = pd.DataFrame({
        "speed": speed.values,
        "dir_from": dir_from.values,
    }, index=pd.to_datetime(ds[time_dim].values)).sort_index()
    return wind_df


def main():
    passes = load_swot_passes()
    wind = load_era5()

    passes["nearest_era5_hour"] = passes["mid"].dt.round("h")
    merged = passes.merge(wind, left_on="nearest_era5_hour", right_index=True, how="left")

    ne_mask = (merged["dir_from"] >= NE_DIR_MIN) & (merged["dir_from"] <= NE_DIR_MAX) & \
              (merged["speed"] >= NE_SPEED_MIN)

    print(f"Total SWOT passes checked: {len(merged)}")
    print(f"Passes with usable ERA5 wind: {merged['speed'].notna().sum()}")
    print(f"NE-wind SWOT passes (dir {NE_DIR_MIN}-{NE_DIR_MAX} deg, "
          f"speed>={NE_SPEED_MIN} m/s): {ne_mask.sum()}")
    print()
    print(merged[ne_mask][["title", "mid", "speed", "dir_from"]].to_string(index=False))

    out_csv = os.path.join(OUTDIR, "ne_wind_swot_matches.csv")
    merged[ne_mask].to_csv(out_csv, index=False)
    print(f"\nSaved matches to {out_csv}")
    print("Only these granule(s) need to be downloaded from PO.DAAC for plotting.")


if __name__ == "__main__":
    main()
