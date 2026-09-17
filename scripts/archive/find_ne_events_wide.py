"""
Detect northeasterly-wind SWOT overpasses along the Kuroshio path.

Instead of averaging over the whole wide ERA5 box (which mixes unrelated
weather systems and cancels out), the wind is averaged separately in four
sub-regions following the current, and a pass is flagged if ANY of them
meets the NE condition. The sub-region that triggered is recorded.

Inputs : era5_swot_passes/swot_granules.json  (4116 passes, CMR metadata)
         era5_swot_passes/era5_wind_YYYYMM.nc (wide-box ERA5 u10/v10)
Output : era5_swot_passes/ne_events_wide.csv
"""
import glob
import json
import os

import numpy as np
import pandas as pd
import xarray as xr

OUTDIR = "/home/takamio/Projects/pj1/era5_swot_passes"
GRANULE_CACHE = os.path.join(OUTDIR, "swot_granules.json")
OUT_CSV = os.path.join(OUTDIR, "ne_events_wide.csv")

# Sub-regions along the Kuroshio path: name -> (lon_min, lon_max, lat_min, lat_max)
REGIONS = {
    "upstream":       (122, 132, 21, 29),   # east of Taiwan - Ryukyu
    "midstream":      (130, 140, 29, 35),   # south of Shikoku / Honshu
    "downstream":     (140, 160, 33, 40),   # Kuroshio Extension
    "extension_east": (160, 180, 33, 42),   # eastern Extension
}

NE_DIR_MIN, NE_DIR_MAX = 22.5, 67.5
NE_SPEED_MIN = 3.0


def regional_wind_timeseries():
    """Month-by-month so memory stays low; returns one DataFrame indexed by
    time with speed_/dir_ columns per sub-region."""
    files = sorted(glob.glob(os.path.join(OUTDIR, "era5_wind_??????.nc")))
    if not files:
        raise FileNotFoundError(f"No era5_wind_*.nc in {OUTDIR}")
    frames = []
    for f in files:
        with xr.open_dataset(f) as ds:
            tname = "valid_time" if "valid_time" in ds.dims else "time"
            cols = {}
            for name, (lo_lon, hi_lon, lo_lat, hi_lat) in REGIONS.items():
                m = (ds.latitude >= lo_lat) & (ds.latitude <= hi_lat) & \
                    (ds.longitude >= lo_lon) & (ds.longitude <= hi_lon)
                u = ds["u10"].where(m).mean(dim=["latitude", "longitude"], skipna=True)
                v = ds["v10"].where(m).mean(dim=["latitude", "longitude"], skipna=True)
                cols[f"speed_{name}"] = np.sqrt(u**2 + v**2).values
                cols[f"dir_{name}"] = ((np.degrees(np.arctan2(u, v)) + 180) % 360).values
            frames.append(pd.DataFrame(cols, index=pd.to_datetime(ds[tname].values)))
        print(f"  processed {os.path.basename(f)}")
    return pd.concat(frames).sort_index()


def load_passes():
    entries = json.load(open(GRANULE_CACHE))
    rows = []
    for e in entries:
        url = next((l["href"] for l in e.get("links", [])
                    if l.get("href", "").startswith("https://archive")
                    and l["href"].endswith(".nc")
                    and "cumulus-protected" in l["href"]), None)
        start = pd.Timestamp(e["time_start"]).tz_localize(None)
        end = pd.Timestamp(e["time_end"]).tz_localize(None)
        rows.append({"title": e["title"], "start": start, "end": end,
                     "mid": start + (end - start) / 2, "url": url})
    return pd.DataFrame(rows).sort_values("mid").reset_index(drop=True)


def main():
    print("Building regional wind time series...")
    wind = regional_wind_timeseries()
    passes = load_passes()
    print(f"{len(passes)} SWOT passes, {len(wind)} ERA5 hours")

    passes["hour"] = passes["mid"].dt.round("h")
    merged = passes.merge(wind, left_on="hour", right_index=True, how="left")

    hit_cols = []
    for name in REGIONS:
        hit = (merged[f"dir_{name}"] >= NE_DIR_MIN) & \
              (merged[f"dir_{name}"] <= NE_DIR_MAX) & \
              (merged[f"speed_{name}"] >= NE_SPEED_MIN)
        merged[f"ne_{name}"] = hit
        hit_cols.append(f"ne_{name}")

    merged["ne_any"] = merged[hit_cols].any(axis=1)
    merged["ne_regions"] = merged[hit_cols].apply(
        lambda r: ",".join(n.replace("ne_", "") for n in hit_cols if r[n]), axis=1)

    events = merged[merged["ne_any"]].copy()
    print(f"\nNE-wind passes: {len(events)} / {len(merged)} "
          f"({len(events)/len(merged)*100:.1f}%)")
    for name in REGIONS:
        print(f"  {name:15s}: {merged[f'ne_{name}'].sum()}")
    print(f"\nUnique granules to download: {events['url'].notna().sum()}")
    print(f"Estimated download size: ~{events['url'].notna().sum()*35/1024:.1f} GB "
          f"(at ~35 MB/granule)")

    events.to_csv(OUT_CSV, index=False)
    print(f"\nSaved to {OUT_CSV}")


if __name__ == "__main__":
    main()
