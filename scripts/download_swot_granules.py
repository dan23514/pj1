"""
Download the SWOT L2 LR SSH Expert granules observed during the NE-wind
episodes listed by list_ne_episodes_kuroshio_box.py, using an Earthdata
Login bearer token (~/.edl_token).

Usage:
    python3 download_swot_granules.py [min_episode_max_speed]

    min_episode_max_speed : only episodes whose peak wind reached this
                            value, m/s (default 0 = every episode)

Already-downloaded files are skipped if their size matches the server's,
so the script is safe to re-run / resume after an interruption.
"""
import os
import sys
from pathlib import Path

import pandas as pd
import requests

BASE = Path(os.environ["RESEARCH_DATA"])
EVENTS_CSV = BASE / "derived" / "pj1" / "tables" / "ne_episodes_kuroshio_box.csv"
DEST = BASE / "SWOT" / "L2_LR_SSH_Expert"
TOKEN_FILE = os.path.expanduser("~/.edl_token")


def select(min_peak):
    """One row per granule, carrying the episode it belongs to."""
    df = pd.read_csv(EVENTS_CSV)
    df = df[(df["n_swot_passes"] > 0) & (df["max_speed"] >= min_peak)]
    rows = []
    for _, ep in df.iterrows():
        for url, title in zip(str(ep["urls"]).split(";"),
                              str(ep["granules"]).split(";")):
            if url:
                rows.append({"url": url, "title": title,
                             "episode_start": ep["start"],
                             "max_speed": ep["max_speed"]})
    return (pd.DataFrame(rows).drop_duplicates(subset="url")
            .sort_values("episode_start").reset_index(drop=True))


def main():
    min_peak = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0

    token = open(TOKEN_FILE).read().strip()
    headers = {"Authorization": f"Bearer {token}"}

    sel = select(min_peak)
    os.makedirs(DEST, exist_ok=True)
    print(f"episodes with peak wind >= {min_peak} m/s")
    print(f"{len(sel)} granules to fetch -> {DEST}\n")

    done = skipped = failed = 0
    for i, row in sel.iterrows():
        url = row["url"]
        path = os.path.join(DEST, os.path.basename(url))
        try:
            with requests.get(url, headers=headers, stream=True, timeout=120) as r:
                r.raise_for_status()
                remote_size = int(r.headers.get("content-length", 0))
                if os.path.exists(path) and os.path.getsize(path) == remote_size:
                    skipped += 1
                    continue
                tmp = path + ".part"
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        f.write(chunk)
                os.rename(tmp, path)
            done += 1
            print(f"[{i+1}/{len(sel)}] {os.path.basename(path)} "
                  f"({remote_size/1e6:.0f} MB)  episode {row['episode_start']}",
                  flush=True)
        except Exception as exc:
            failed += 1
            print(f"[{i+1}/{len(sel)}] FAILED {os.path.basename(url)}: {exc}", flush=True)

    print(f"\ndownloaded={done} skipped={skipped} failed={failed}")


if __name__ == "__main__":
    main()
