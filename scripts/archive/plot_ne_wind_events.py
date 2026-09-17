import xarray as xr
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import os

# ---------------------------------------------------------------------------
# Step 1: identify hours where the Kuroshio-region-averaged 10 m wind blows
# from the northeast (direction 22.5-67.5 deg, "from" convention) with
# speed >= 3 m/s, then group consecutive hours into events.
# ---------------------------------------------------------------------------
wind_era5 = xr.open_dataset('/home/takamio/Data/ERA5/data_stream-oper_stepType-instant.nc')

lat = wind_era5.latitude
lon = wind_era5.longitude
region_mask = (lat > 35) & (lat < 45) & (lon > 135) & (lon < 150)

u_region = wind_era5['u10'].where(region_mask)
v_region = wind_era5['v10'].where(region_mask)
u_mean = u_region.mean(dim=['latitude', 'longitude'], skipna=True)
v_mean = v_region.mean(dim=['latitude', 'longitude'], skipna=True)

speed_mean = np.sqrt(u_mean**2 + v_mean**2)
dir_from = (np.degrees(np.arctan2(u_mean, v_mean)) + 180) % 360

df = pd.DataFrame({
    'time': wind_era5.valid_time.values,
    'speed': speed_mean.values,
    'dir_from': dir_from.values,
})
df['time'] = pd.to_datetime(df['time'])

ne_mask = (df['dir_from'] >= 22.5) & (df['dir_from'] <= 67.5) & (df['speed'] >= 3.0)
ne_events = df[ne_mask].sort_values('time').reset_index(drop=True)
gaps = ne_events['time'].diff() > pd.Timedelta(hours=1)
ne_events['episode'] = gaps.cumsum()

print(ne_events.groupby('episode')['time'].agg(['min', 'max', 'count']))

# ---------------------------------------------------------------------------
# Step 2: for every hour in every identified NE-wind event, make a figure
# (wind speed + vectors) following the style of the reference script.
# ---------------------------------------------------------------------------
outdir = '/home/takamio/Projects/pj1/output/ne_events'
os.makedirs(outdir, exist_ok=True)

plot_mask = (wind_era5.latitude > 20) & (wind_era5.latitude < 50) & \
            (wind_era5.longitude > 120) & (wind_era5.longitude < 150)

level_min, level_max = 2.0, 13.0
cmap = plt.colormaps['YlGn_r']

for t in ne_events['time']:
    wind_t = wind_era5.sel(valid_time=t).where(plot_mask, drop=True)
    u_t = wind_t['u10']
    v_t = wind_t['v10']
    wind_abs_t = np.sqrt(u_t**2 + v_t**2)

    fig = plt.figure()
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.coastlines()
    ax.set_extent([135, 150, 35, 45])
    pcm = ax.pcolormesh(wind_abs_t.longitude.values, wind_abs_t.latitude.values,
                         wind_abs_t.values, vmin=level_min, vmax=level_max,
                         shading='nearest', cmap=cmap, transform=ccrs.PlateCarree())

    # thin out the 0.25-deg grid for the quiver so arrows are legible
    thin = 4
    q = ax.quiver(wind_t.longitude.values[::thin], wind_t.latitude.values[::thin],
                  u_t.values[::thin, ::thin], v_t.values[::thin, ::thin],
                  transform=ccrs.PlateCarree(), scale=150, width=0.004)
    ax.quiverkey(q, 0.88, 1.03, 10, '10 m/s', labelpos='E', coordinates='axes')
    ax.add_feature(cfeature.LAND, facecolor='0.85', zorder=10)
    cbar = plt.colorbar(pcm, ax=ax)
    cbar.set_label('wind speed [m/s]')
    ts = pd.Timestamp(t)
    ax.set_title(ts.strftime('%Y-%m-%d %H:%M UTC') + '  (NE wind event)')

    fname = os.path.join(outdir, f"era5_wind_{ts.strftime('%Y%m%dT%H%M')}.png")
    plt.savefig(fname, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print('saved', fname)

print(f"Done. {len(ne_events)} figures saved to {outdir}")
