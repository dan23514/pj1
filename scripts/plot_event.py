"""
Plot wind / wave / current for one NE-wind episode.

    python3 plot_event.py "2025-01-24 23:00" [--extent lon0 lon1 lat0 lat1]

The episode is looked up in ne_episodes_kuroshio_box.csv; every SWOT pass it
contains gets three figures (ERA5 background + SWOT swath for wind and wave,
SWOT SSH geostrophy for current), each titled with its time.

Colour limits are derived from the episode's own values, using percentiles
so a few outliers do not flatten the scale. They are shared by every pass of
the episode, so the panels stay comparable as the wind builds. This means
scales differ BETWEEN episodes -- do not compare colours across events.

With no --extent, the map is framed on where the swath actually is, which
matters because a pass flagged by the 135-150E/35-45N screening box can in
fact be observing a quite different part of the Kuroshio.

Output: results/event<YYYYMMDD>/{wind,wave,current}_YYYYMMDDTHHMM.png
"""
import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from numpy.lib.stride_tricks import sliding_window_view
from matplotlib import pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

BASE = Path(os.environ["RESEARCH_DATA"])
SWOT_DIR = BASE / "SWOT" / "L2_LR_SSH_Expert"
EVENTS_CSV = BASE / "derived" / "pj1" / "tables" / "ne_episodes_kuroshio_box.csv"
RESULTS = Path(__file__).resolve().parent.parent / "results"

W = 4  # half-width of the plane-fit window (9x9)
LAT_BAND = (25, 46)  # latitudes worth framing around Japan


def open_swot(fname):
    ds = xr.open_dataset(SWOT_DIR / fname)
    return ds.assign_coords(longitude=((ds.longitude + 180) % 360) - 180)


def swath_extent(swot, pad=2.0):
    lat, lon = swot.latitude.values, swot.longitude.values
    m = (lat > LAT_BAND[0]) & (lat < LAT_BAND[1]) & (lon > 110) & (lon < 170)
    return [lon[m].min() - pad, lon[m].max() + pad, LAT_BAND[0], LAT_BAND[1]]


def in_extent(lat, lon, extent):
    return (lon > extent[0]) & (lon < extent[1]) & (lat > extent[2]) & (lat < extent[3])


def geostrophic_speed(swot, extent):
    """Current speed from a 9x9 plane fit to the absolute dynamic topography."""
    ssh = (swot["ssha_karin"] + swot["height_cor_xover"]
           + swot["mean_dynamic_topography"])
    qual = ((swot["ssha_karin_qual"] == 0)
            & (swot["height_cor_xover_qual"] == 0)
            & (swot["ancillary_surface_classification_flag"] == 0))
    box = in_extent(swot.latitude, swot.longitude, extent)
    j = np.flatnonzero(box.any("num_pixels").values)
    if j.size == 0:
        return None, None, None
    ssh = ssh.where(qual).isel(num_lines=slice(max(j[0] - W, 0), j[-1] + 1 + W))
    lat, lon = ssh.latitude, ssh.longitude

    R, g = 6371e3, 9.8
    omega = 2 * np.pi / (23 * 3600 + 56 * 60 + 4)
    plane = (2 * W + 1, 2 * W + 1)
    Z = sliding_window_view(ssh.values, plane)
    LAT = sliding_window_view(lat.values, plane)
    LON = sliding_window_view(lon.values, plane)
    lat0 = LAT[:, :, W, W][:, :, None, None]
    lon0 = LON[:, :, W, W][:, :, None, None]
    x = R * np.cos(np.deg2rad(lat0)) * np.deg2rad(LON - lon0)
    y = R * np.deg2rad(LAT - lat0)
    ok = np.isfinite(Z) & np.isfinite(x) & np.isfinite(y)

    n, m = Z.shape[:2]
    dhdx = np.full((n, m), np.nan)
    dhdy = np.full((n, m), np.nan)
    for i in range(n):
        for k in range(m):
            sel = ok[i, k]
            if sel.sum() < 40:
                continue
            A = np.column_stack([np.ones(sel.sum()), x[i, k][sel], y[i, k][sel]])
            _, b, c = np.linalg.lstsq(A, Z[i, k][sel], rcond=None)[0]
            dhdx[i, k], dhdy[i, k] = b, c

    la_c = lat.values[W:-W, W:-W]
    lo_c = lon.values[W:-W, W:-W]
    f = 2 * omega * np.sin(np.deg2rad(la_c))
    return lo_c, la_c, np.hypot((g / f) * dhdy, (g / f) * dhdx)


def collect(swot, era5_wind, era5_swh, tstr, extent):
    """Everything the three figures need, so colour limits can be set from
    the whole episode before anything is drawn."""
    era_w = era5_wind.sel(valid_time=tstr)
    era_w = era_w.where(in_extent(era_w.latitude, era_w.longitude, extent), drop=True)
    era_s = era5_swh.sel(valid_time=tstr)
    era_s = era_s["swh"].where(in_extent(era_s.latitude, era_s.longitude, extent), drop=True)

    sw_wind = swot["wind_speed_karin"]
    sw_wind = sw_wind.where(in_extent(sw_wind.latitude, sw_wind.longitude, extent)
                            & (swot["wind_speed_karin_qual"] == 0), drop=True)
    sw_wave = swot["swh_karin"]
    sw_wave = sw_wave.where(in_extent(sw_wave.latitude, sw_wave.longitude, extent)
                            & (swot["swh_karin_qual"] == 0), drop=True)

    lo_c, la_c, cur = geostrophic_speed(swot, extent)
    return {
        "extent": extent,
        "u": era_w["u10"], "v": era_w["v10"],
        "wind_era": np.sqrt(era_w["u10"] ** 2 + era_w["v10"] ** 2),
        "wind_swot": sw_wind,
        "wave_era": era_s, "wave_swot": sw_wave,
        "cur_lon": lo_c, "cur_lat": la_c, "cur": cur,
    }


def limits(arrays, lo_pct, hi_pct, step, floor_zero=False):
    """Percentile range over the episode, snapped outward to a round step."""
    vals = np.concatenate([np.asarray(a).ravel() for a in arrays if a is not None])
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        return 0.0, 1.0
    lo, hi = np.percentile(vals, [lo_pct, hi_pct])
    lo = 0.0 if floor_zero else np.floor(lo / step) * step
    hi = np.ceil(hi / step) * step
    if hi <= lo:
        hi = lo + step
    return float(lo), float(hi)


def new_axes(title, extent):
    fig = plt.figure(figsize=(8, 7))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.coastlines()
    ax.set_extent(extent)
    ax.set_title(title)
    return fig, ax


def save(fig, prefix, name):
    outdir = RESULTS / prefix
    outdir.mkdir(parents=True, exist_ok=True)
    fig.savefig(outdir / name, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {prefix}/{name}", flush=True)


def plot_wind(d, tstr, vmin, vmax, prefix, stamp):
    fig, ax = new_axes(f"10 m wind  {tstr.replace('T', ' ')} UTC", d["extent"])
    cmap = plt.colormaps["YlGn_r"]
    ax.pcolormesh(d["wind_era"].longitude.values, d["wind_era"].latitude.values,
                  d["wind_era"].values, vmin=vmin, vmax=vmax, shading="nearest",
                  cmap=cmap, transform=ccrs.PlateCarree())
    thin = 4
    q = ax.quiver(d["u"].longitude.values[::thin], d["u"].latitude.values[::thin],
                  d["u"].values[::thin, ::thin], d["v"].values[::thin, ::thin],
                  transform=ccrs.PlateCarree(), scale=250, width=0.004)
    # inside the axes: a tall narrow extent makes the title and a key above
    # the frame collide
    ax.quiverkey(q, 0.82, 0.03, 10, "10 m/s", labelpos="E", coordinates="axes",
                 labelsep=0.05)
    sw = d["wind_swot"]
    pcm = ax.pcolormesh(sw.longitude.values, sw.latitude.values, sw.values,
                        vmin=vmin, vmax=vmax, shading="nearest", cmap=cmap,
                        transform=ccrs.PlateCarree())
    ax.add_feature(cfeature.LAND, facecolor="0.85", zorder=10)
    plt.colorbar(pcm, ax=ax).set_label("wind speed [m/s]")
    save(fig, prefix, f"wind_{stamp}.png")


def plot_wave(d, tstr, vmin, vmax, prefix, stamp):
    fig, ax = new_axes(f"significant wave height  {tstr.replace('T', ' ')} UTC",
                       d["extent"])
    cmap = plt.colormaps["plasma"]
    ax.pcolormesh(d["wave_era"].longitude.values, d["wave_era"].latitude.values,
                  d["wave_era"].values, vmin=vmin, vmax=vmax, shading="nearest",
                  cmap=cmap, transform=ccrs.PlateCarree())
    sw = d["wave_swot"]
    pcm = ax.pcolormesh(sw.longitude.values, sw.latitude.values, sw.values,
                        vmin=vmin, vmax=vmax, shading="nearest", cmap=cmap,
                        transform=ccrs.PlateCarree())
    ax.add_feature(cfeature.LAND, facecolor="0.85", zorder=10)
    plt.colorbar(pcm, ax=ax).set_label("significant wave height [m]")
    save(fig, prefix, f"wave_{stamp}.png")


def plot_current(d, tstr, vmin, vmax, prefix, stamp):
    if d["cur"] is None:
        print(f"  no swath inside extent at {tstr}; skipping current")
        return
    fig, ax = new_axes(f"geostrophic current speed  {tstr.replace('T', ' ')} UTC",
                       d["extent"])
    pcm = ax.pcolormesh(d["cur_lon"], d["cur_lat"], d["cur"], vmin=vmin, vmax=vmax,
                        shading="nearest", cmap=plt.colormaps["viridis"],
                        transform=ccrs.PlateCarree())
    ax.add_feature(cfeature.LAND, facecolor="0.85", zorder=10)
    plt.colorbar(pcm, ax=ax).set_label("current speed [m/s]")
    save(fig, prefix, f"current_{stamp}.png")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("start", help='episode start, e.g. "2025-01-24 23:00"')
    ap.add_argument("--extent", nargs=4, type=float,
                    metavar=("LON0", "LON1", "LAT0", "LAT1"))
    args = ap.parse_args()

    df = pd.read_csv(EVENTS_CSV)
    key = pd.Timestamp(args.start)
    row = df[pd.to_datetime(df["start"]) == key]
    if row.empty:
        raise SystemExit(f"no episode starting {key} in {EVENTS_CSV}")
    ep = row.iloc[0]
    prefix = f"event{key.strftime('%Y%m%d')}"
    print(f"{ep['start']} - {ep['end']}  {ep['n_hours']}h  "
          f"peak {ep['max_speed']} m/s  dir {ep['mean_dir']}deg  "
          f"{ep['n_swot_passes']} pass(es)")

    era5_wind = xr.open_dataset(
        BASE / f"ERA5/wind10m_NP_2023-2025/era5_wind_{key.strftime('%Y%m')}.nc")
    era5_swh = xr.open_dataset(
        BASE / f"ERA5/swh_NP_2023-2025/era5_swh_{key.strftime('%Y%m')}.nc")

    fields = []
    for tstr, granule in zip(str(ep["swot_times"]).split(";"),
                             str(ep["granules"]).split(";")):
        swot = open_swot(granule.replace("_swot", "") + ".nc")
        extent = args.extent if args.extent else swath_extent(swot)
        hour = pd.Timestamp(tstr).round("h")
        print(f"--- pass {tstr} -> ERA5 {hour:%Y-%m-%dT%H:%M}, extent "
              f"{[round(e, 1) for e in extent]} ---", flush=True)
        fields.append((hour, collect(swot, era5_wind, era5_swh,
                                     f"{hour:%Y-%m-%dT%H:%M}", extent)))

    wind_lim = limits([d["wind_era"].values for _, d in fields]
                      + [d["wind_swot"].values for _, d in fields], 1, 99, 1)
    wave_lim = limits([d["wave_era"].values for _, d in fields]
                      + [d["wave_swot"].values for _, d in fields], 1, 99, 0.5)
    cur_lim = limits([d["cur"] for _, d in fields], 0, 98, 0.25, floor_zero=True)
    print(f"colour limits for this episode: wind {wind_lim} m/s, "
          f"wave {wave_lim} m, current {cur_lim} m/s")

    for hour, d in fields:
        tstr = f"{hour:%Y-%m-%dT%H:%M}"
        stamp = f"{hour:%Y%m%dT%H%M}"
        plot_wind(d, tstr, *wind_lim, prefix, stamp)
        plot_wave(d, tstr, *wave_lim, prefix, stamp)
        plot_current(d, tstr, *cur_lim, prefix, stamp)


if __name__ == "__main__":
    main()
