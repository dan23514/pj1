"""
List the periods where ERA5 shows northeasterly wind over a Kuroshio
sub-region AND SWOT actually observed that same sub-region during the
period.

For each sub-region:
  1. ask CMR which SWOT passes cross that specific box (metadata only),
  2. find contiguous runs of NE-wind hours in the ERA5 time series,
  3. keep the runs that contain at least one of those passes.

Output: era5_swot_passes/ne_episodes_with_swot.csv
"""
import json
import os
import urllib.request

import numpy as np
import pandas as pd

OUTDIR = "/home/takamio/Projects/pj1/era5_swot_passes"
WIND_CSV = os.path.join(OUTDIR, "regional_wind_hourly.csv")
OUT_CSV = os.path.join(OUTDIR, "ne_episodes_with_swot.csv")

REGIONS = {
    "upstream":       (122, 132, 21, 29),
    "midstream":      (130, 140, 29, 35),
    "downstream":     (140, 160, 33, 40),
    "extension_east": (160, 180, 33, 42),
}

COLLECTION = "C2799465497-POCLOUD"
TEMPORAL = "2023-01-01T00:00:00Z,2026-09-15T00:00:00Z"

NE_DIR_MIN, NE_DIR_MAX = 22.5, 67.5
NE_SPEED_MIN = 3.0


def passes_over(box):
    """CMR granules intersecting one sub-region box (metadata only)."""
    lo_lon, hi_lon, lo_lat, hi_lat = box
    entries, page = [], 1
    while True:
        url = ("https://cmr.earthdata.nasa.gov/search/granules.json"
               f"?collection_concept_id={COLLECTION}"
               f"&bounding_box={lo_lon},{lo_lat},{hi_lon},{hi_lat}"
               f"&temporal={TEMPORAL}&page_size=2000&page_num={page}")
        with urllib.request.urlopen(url) as r:
            page_entries = json.load(r)["feed"]["entry"]
        entries.extend(page_entries)
        if len(page_entries) < 2000:
            break
        page += 1
    rows = []
    for e in entries:
        start = pd.Timestamp(e["time_start"]).tz_localize(None)
        end = pd.Timestamp(e["time_end"]).tz_localize(None)
        url = next((l["href"] for l in e.get("links", [])
                    if l.get("href", "").startswith("https://archive")
                    and l["href"].endswith(".nc")
                    and "cumulus-protected" in l["href"]), None)
        rows.append({"title": e["title"], "mid": start + (end - start) / 2,
                     "url": url})
    df = pd.DataFrame(rows)
    df["hour"] = df["mid"].dt.round("h")
    return df


def episodes(series_dir, series_speed, index):
    """Contiguous runs of NE-wind hours. A gap of more than one hour
    (including days absent from the download) starts a new episode."""
    ne = (series_dir >= NE_DIR_MIN) & (series_dir <= NE_DIR_MAX) & \
         (series_speed >= NE_SPEED_MIN)
    hours = index[ne]
    if len(hours) == 0:
        return []
    breaks = np.where(np.diff(hours.values) != np.timedelta64(1, "h"))[0]
    groups = np.split(np.arange(len(hours)), breaks + 1)
    return [hours[g] for g in groups]


def main():
    wind = pd.read_csv(WIND_CSV, index_col=0, parse_dates=True).sort_index()
    records = []

    for region, box in REGIONS.items():
        swot = passes_over(box)
        print(f"{region:15s}: {len(swot)} SWOT passes cross this box")
        d = wind[f"dir_{region}"]
        s = wind[f"speed_{region}"]
        eps = episodes(d, s, wind.index)

        matched = 0
        for hours in eps:
            hit = swot[swot["hour"].isin(hours)]
            if hit.empty:
                continue
            matched += 1
            spd = s.loc[hours]
            dirs = d.loc[hours]
            # vector mean direction over the episode
            u = -(spd * np.sin(np.radians(dirs))).mean()
            v = -(spd * np.cos(np.radians(dirs))).mean()
            mean_dir = (np.degrees(np.arctan2(u, v)) + 180) % 360
            records.append({
                "region": region,
                "start": hours[0],
                "end": hours[-1],
                "n_hours": len(hours),
                "mean_speed": round(spd.mean(), 2),
                "max_speed": round(spd.max(), 2),
                "mean_dir": round(mean_dir, 1),
                "n_swot_passes": len(hit),
                "swot_times": ";".join(t.strftime("%Y-%m-%dT%H:%M")
                                       for t in hit["mid"]),
                "granules": ";".join(hit["title"]),
                "urls": ";".join(x for x in hit["url"] if x),
            })
        print(f"{'':15s}  -> {len(eps)} NE episodes, {matched} with SWOT coverage")

    out = pd.DataFrame(records).sort_values(["start", "region"]).reset_index(drop=True)
    out.to_csv(OUT_CSV, index=False)

    print(f"\n{len(out)} NE-wind episodes with simultaneous SWOT coverage")
    print(out.groupby("region")["n_hours"].agg(["count", "sum"]))
    print(f"\nSaved to {OUT_CSV}")

    show = ["region", "start", "end", "n_hours", "mean_speed",
            "max_speed", "mean_dir", "n_swot_passes"]
    print("\n--- strongest 20 by max wind speed ---")
    print(out.nlargest(20, "max_speed")[show].to_string(index=False))


if __name__ == "__main__":
    main()
