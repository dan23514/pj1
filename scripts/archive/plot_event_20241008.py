"""
NE-wind episode 2024-10-08 15:00 - 2024-10-10 20:00 UTC (54 h, peak 9.4 m/s).
SWOT crosses the region four times, so the wind/wave/current fields can be
followed as the wind strengthens.

For each of the four passes, three figures: wind, wave, current.
Wind and wave follow Boas25_Kuroshio.py (ERA5 background + SWOT swath);
current follows geostrophic_current.py (9x9 plane fit on SWOT SSH).

Output: results/event20241008_{wind,wave,current}_YYYYMMDDTHHMM.png
"""
import os
from pathlib import Path

import numpy as np
import xarray as xr
from numpy.lib.stride_tricks import sliding_window_view
from matplotlib import pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

BASE = Path(os.environ["RESEARCH_DATA"])
SWOT_DIR = BASE / "SWOT" / "L2_LR_SSH_Expert"
RESULTS = Path(__file__).resolve().parent.parent / "results"

PASSES = [
    ("SWOT_L2_LR_SSH_Expert_022_213_20241008T230715_20241008T235843_PIC0_01.nc", "2024-10-09T00:00"),
    ("SWOT_L2_LR_SSH_Expert_022_226_20241009T101604_20241009T110732_PIC0_01.nc", "2024-10-09T11:00"),
    ("SWOT_L2_LR_SSH_Expert_022_241_20241009T230746_20241009T235914_PIC0_01.nc", "2024-10-10T00:00"),
    ("SWOT_L2_LR_SSH_Expert_022_254_20241010T101634_20241010T110803_PIC0_01.nc", "2024-10-10T11:00"),
]

# one extent for all panels so the four times are comparable
EXTENT = [134, 150, 33, 45]
LON_MIN, LON_MAX, LAT_MIN, LAT_MAX = 134, 150, 33, 45

# widened from the single-event script: this episode reaches 19 m/s and 6.5 m,
# which the original 2-13 / 1-3 scales would have saturated
WIND_VMIN, WIND_VMAX = 2, 16
SWH_VMIN, SWH_VMAX = 1, 6
CUR_VMIN, CUR_VMAX = 0, 2.0

W = 4  # half-width of the 9x9 plane-fit window


def new_axes(title):
    fig = plt.figure(figsize=(8, 6))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.coastlines()
    ax.set_extent(EXTENT)
    ax.set_title(title)
    return fig, ax


def open_swot(fname):
    ds = xr.open_dataset(SWOT_DIR / fname)
    return ds.assign_coords(longitude=((ds.longitude + 180) % 360) - 180)


def region_mask(lat, lon):
    return (lat > LAT_MIN) & (lat < LAT_MAX) & (lon > LON_MIN) & (lon < LON_MAX)


def plot_wind(era5, swot, tstr, stamp):
    era = era5.sel(valid_time=tstr)
    m = region_mask(era.latitude, era.longitude)
    era = era.where(m, drop=True)
    u, v = era["u10"], era["v10"]
    speed = np.sqrt(u**2 + v**2)

    fig, ax = new_axes(f"10 m wind  {tstr.replace('T', ' ')} UTC")
    ax.pcolormesh(speed.longitude.values, speed.latitude.values, speed.values,
                  vmin=WIND_VMIN, vmax=WIND_VMAX, shading="nearest",
                  cmap=plt.colormaps["YlGn_r"], transform=ccrs.PlateCarree())
    thin = 4
    q = ax.quiver(era.longitude.values[::thin], era.latitude.values[::thin],
                  u.values[::thin, ::thin], v.values[::thin, ::thin],
                  transform=ccrs.PlateCarree(), scale=250, width=0.004)
    ax.quiverkey(q, 0.88, 1.03, 10, "10 m/s", labelpos="E", coordinates="axes")

    sw = swot["wind_speed_karin"]
    good = region_mask(sw.latitude, sw.longitude) & (swot["wind_speed_karin_qual"] == 0)
    sw = sw.where(good, drop=True)
    pcm = ax.pcolormesh(sw.longitude.values, sw.latitude.values, sw.values,
                        vmin=WIND_VMIN, vmax=WIND_VMAX, shading="nearest",
                        cmap=plt.colormaps["YlGn_r"], transform=ccrs.PlateCarree())
    ax.add_feature(cfeature.LAND, facecolor="0.85", zorder=10)
    plt.colorbar(pcm, ax=ax).set_label("wind speed [m/s]")
    save(fig, f"event20241008_wind_{stamp}.png")


def plot_wave(era5_swh, swot, tstr, stamp):
    era = era5_swh.sel(valid_time=tstr)
    m = region_mask(era.latitude, era.longitude)
    era = era["swh"].where(m, drop=True)

    fig, ax = new_axes(f"significant wave height  {tstr.replace('T', ' ')} UTC")
    ax.pcolormesh(era.longitude.values, era.latitude.values, era.values,
                  vmin=SWH_VMIN, vmax=SWH_VMAX, shading="nearest",
                  cmap=plt.colormaps["plasma"], transform=ccrs.PlateCarree())

    sw = swot["swh_karin"]
    good = region_mask(sw.latitude, sw.longitude) & (swot["swh_karin_qual"] == 0)
    sw = sw.where(good, drop=True)
    pcm = ax.pcolormesh(sw.longitude.values, sw.latitude.values, sw.values,
                        vmin=SWH_VMIN, vmax=SWH_VMAX, shading="nearest",
                        cmap=plt.colormaps["plasma"], transform=ccrs.PlateCarree())
    ax.add_feature(cfeature.LAND, facecolor="0.85", zorder=10)
    plt.colorbar(pcm, ax=ax).set_label("significant wave height [m]")
    save(fig, f"event20241008_wave_{stamp}.png")


def plot_current(swot, tstr, stamp):
    ssh = (swot["ssha_karin"] + swot["height_cor_xover"]
           + swot["mean_dynamic_topography"])
    qual = ((swot["ssha_karin_qual"] == 0)
            & (swot["height_cor_xover_qual"] == 0)
            & (swot["ancillary_surface_classification_flag"] == 0))
    box = region_mask(swot.latitude, swot.longitude)
    j = np.flatnonzero(box.any("num_pixels").values)
    ssh = ssh.where(qual).isel(num_lines=slice(j[0] - W, j[-1] + 1 + W))
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
            dhdx[i, k] = b
            dhdy[i, k] = c

    la_c = lat.values[W:-W, W:-W]
    lo_c = lon.values[W:-W, W:-W]
    f = 2 * omega * np.sin(np.deg2rad(la_c))
    speed = np.sqrt(((g / f) * dhdy) ** 2 + ((g / f) * dhdx) ** 2)

    fig, ax = new_axes(f"geostrophic current speed  {tstr.replace('T', ' ')} UTC")
    pcm = ax.pcolormesh(lo_c, la_c, speed, vmin=CUR_VMIN, vmax=CUR_VMAX,
                        shading="nearest", cmap=plt.colormaps["viridis"],
                        transform=ccrs.PlateCarree())
    ax.add_feature(cfeature.LAND, facecolor="0.85", zorder=10)
    plt.colorbar(pcm, ax=ax).set_label("current speed [m/s]")
    save(fig, f"event20241008_current_{stamp}.png")


def save(fig, name):
    RESULTS.mkdir(exist_ok=True)
    fig.savefig(RESULTS / name, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("saved", name, flush=True)


def main():
    era5_wind = xr.open_dataset(BASE / "ERA5/wind10m_NP_2023-2025/era5_wind_202410.nc")
    era5_swh = xr.open_dataset(BASE / "ERA5/swh_NP_2023-2025/era5_swh_202410.nc")
    for fname, tstr in PASSES:
        stamp = tstr.replace("-", "").replace(":", "")[:13]
        swot = open_swot(fname)
        print(f"--- {tstr} / {fname.split('_')[6]}_{fname.split('_')[7]} ---", flush=True)
        plot_wind(era5_wind, swot, tstr, stamp)
        plot_wave(era5_swh, swot, tstr, stamp)
        plot_current(swot, tstr, stamp)


if __name__ == "__main__":
    main()
