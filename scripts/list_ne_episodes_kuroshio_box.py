"""
Same method as the first diagnosis (which used the Jul-Sep 2023 ERA5 file),
now applied to the full 2023-07 .. 2025-05 download:

  - average u10/v10 over the single Kuroshio box 135-150E, 35-45N
  - speed = |u,v|, dir_from = (atan2(u,v) + 180) mod 360
  - NE wind = direction 22.5-67.5 deg and speed >= 3 m/s
  - consecutive NE hours grouped into episodes

Each episode is then matched against the SWOT passes that cross the same
box, so the output says which episodes SWOT actually observed.

Output: $RESEARCH_DATA/derived/pj1/tables/ne_episodes_kuroshio_box.csv
"""
import glob
import json
import os
import urllib.request

from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

BASE = Path(os.environ["RESEARCH_DATA"])
ERA5_DIR = BASE / "ERA5" / "wind10m_NP_2023-2025"
OUT_CSV = BASE / "derived" / "pj1" / "tables" / "ne_episodes_kuroshio_box.csv"

# the original box from the first diagnosis
LON_MIN, LON_MAX = 135, 150
LAT_MIN, LAT_MAX = 35, 45

NE_DIR_MIN, NE_DIR_MAX = 22.5, 67.5
NE_SPEED_MIN = 3.0

COLLECTION = "C2799465497-POCLOUD"
TEMPORAL = "2023-01-01T00:00:00Z,2026-09-15T00:00:00Z"


def box_wind():
    frames = []
    for f in sorted(glob.glob(str(ERA5_DIR / "era5_wind_??????.nc"))):
        with xr.open_dataset(f) as ds:
            tname = "valid_time" if "valid_time" in ds.dims else "time"
            m = (ds.latitude > LAT_MIN) & (ds.latitude < LAT_MAX) & \
                (ds.longitude > LON_MIN) & (ds.longitude < LON_MAX)
            u = ds["u10"].where(m).mean(dim=["latitude", "longitude"], skipna=True)
            v = ds["v10"].where(m).mean(dim=["latitude", "longitude"], skipna=True)
            frames.append(pd.DataFrame(
                {"speed": np.sqrt(u**2 + v**2).values,
                 "dir_from": ((np.degrees(np.arctan2(u, v)) + 180) % 360).values},
                index=pd.to_datetime(ds[tname].values)))
        print(f"  {os.path.basename(f)}")
    return pd.concat(frames).sort_index()


def swot_passes():
    entries, page = [], 1
    while True:
        url = ("https://cmr.earthdata.nasa.gov/search/granules.json"
               f"?collection_concept_id={COLLECTION}"
               f"&bounding_box={LON_MIN},{LAT_MIN},{LON_MAX},{LAT_MAX}"
               f"&temporal={TEMPORAL}&page_size=2000&page_num={page}")
        with urllib.request.urlopen(url) as r:
            page_entries = json.load(r)["feed"]["entry"]
        entries.extend(page_entries)
        if len(page_entries) < 2000:
            break
        page += 1
    rows = []
    for e in entries:
        s = pd.Timestamp(e["time_start"]).tz_localize(None)
        t = pd.Timestamp(e["time_end"]).tz_localize(None)
        u = next((l["href"] for l in e.get("links", [])
                  if l.get("href", "").startswith("https://archive")
                  and l["href"].endswith(".nc")
                  and "cumulus-protected" in l["href"]), None)
        rows.append({"title": e["title"], "mid": s + (t - s) / 2, "url": u})
    df = pd.DataFrame(rows)
    df["hour"] = df["mid"].dt.round("h")
    return df


def main():
    print(f"Averaging ERA5 over {LON_MIN}-{LON_MAX}E, {LAT_MIN}-{LAT_MAX}N")
    wind = box_wind()
    swot = swot_passes()
    print(f"\n{len(wind)} ERA5 hours | {len(swot)} SWOT passes crossing the box")

    ne = (wind["dir_from"] >= NE_DIR_MIN) & (wind["dir_from"] <= NE_DIR_MAX) & \
         (wind["speed"] >= NE_SPEED_MIN)
    hours = wind.index[ne]
    print(f"NE hours: {len(hours)} / {len(wind)} ({len(hours)/len(wind)*100:.1f}%)")

    breaks = np.where(np.diff(hours.values) != np.timedelta64(1, "h"))[0]
    groups = np.split(np.arange(len(hours)), breaks + 1)

    records = []
    for g in groups:
        h = hours[g]
        spd, dirs = wind.loc[h, "speed"], wind.loc[h, "dir_from"]
        u = -(spd * np.sin(np.radians(dirs))).mean()
        v = -(spd * np.cos(np.radians(dirs))).mean()
        hit = swot[swot["hour"].isin(h)]
        records.append({
            "start": h[0], "end": h[-1], "n_hours": len(h),
            "mean_speed": round(spd.mean(), 2),
            "max_speed": round(spd.max(), 2),
            "mean_dir": round((np.degrees(np.arctan2(u, v)) + 180) % 360, 1),
            "n_swot_passes": len(hit),
            "swot_times": ";".join(t.strftime("%Y-%m-%dT%H:%M") for t in hit["mid"]),
            "granules": ";".join(hit["title"]),
            "urls": ";".join(x for x in hit["url"] if x),
        })

    out = pd.DataFrame(records)
    out.to_csv(OUT_CSV, index=False)
    with_swot = out[out["n_swot_passes"] > 0]

    print(f"\n{len(out)} NE episodes total, "
          f"{len(with_swot)} observed by SWOT "
          f"({with_swot['n_swot_passes'].sum()} passes)")
    print(f"Saved to {OUT_CSV}\n")

    cols = ["start", "end", "n_hours", "mean_speed", "max_speed",
            "mean_dir", "n_swot_passes"]
    print("--- all episodes with SWOT coverage, strongest first ---")
    print(with_swot.sort_values("max_speed", ascending=False)[cols]
          .to_string(index=False))


if __name__ == "__main__":
    main()
