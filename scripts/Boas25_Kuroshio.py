import os
from pathlib import Path

import xarray as xr 
import numpy as np 
from matplotlib import pyplot as plt 
import cartopy.crs as ccrs 
from matplotlib.colors import BoundaryNorm
from matplotlib.ticker import MaxNLocator
import cartopy.feature as cfeature

#wind speed

#ERA5
wind_era5=xr.open_dataset(str(Path(os.environ["RESEARCH_DATA"]) / "ERA5/wind10m_NP_2023-2025/era5_wind_202309.nc")).sel(valid_time='2023-09-07T16:00')

lat=wind_era5.latitude
lon=wind_era5.longitude
mask=(lat>20)&(lat<50)&(lon>120)&(lon<150)
wind_era5=wind_era5.where(mask,drop=True)
u_era5=wind_era5['u10']
v_era5=wind_era5['v10']
wind_abs_era5=np.sqrt(u_era5**2+v_era5**2)

#SWOT
data=xr.open_dataset(str(Path(os.environ["RESEARCH_DATA"]) / "SWOT/L2_LR_SSH_Expert/SWOT_L2_LR_SSH_Expert_003_185_20230907T125013_20230907T134141_PGC0_01.nc"))
data = data.assign_coords(longitude=((data.longitude + 180) % 360) - 180)
wind=data['wind_speed_karin']
lat=wind.latitude
lon=wind.longitude
mask=(lat>20)&(lat<50)&(lon>120)&(lon<150)&(data['wind_speed_karin_qual']==0)
wind=wind.where(mask,drop=True)

#plot
level=np.arange(2.0,13.0,0.5) 
cmap=plt.colormaps['YlGn_r']
ax=plt.axes(projection=ccrs.PlateCarree())
ax.coastlines()
ax.set_extent([135,150,35,45])
ax.pcolormesh(wind_abs_era5.longitude.values,wind_abs_era5.latitude.values,wind_abs_era5.values,vmin=2,vmax=13,shading='nearest',cmap=cmap,transform=ccrs.PlateCarree())
thin = 4
ax.quiver(wind_era5.longitude.values[::thin], wind_era5.latitude.values[::thin],
                  u_era5.values[::thin, ::thin], v_era5.values[::thin, ::thin],
                  transform=ccrs.PlateCarree(), scale=150, width=0.004)
pcm=ax.pcolormesh(wind.longitude.values,wind.latitude.values,wind.values,vmin=2.0,vmax=13.0,shading='nearest',cmap=cmap,transform=ccrs.PlateCarree())
ax.add_feature(cfeature.LAND, facecolor='0.85', zorder=10)
cbar=plt.colorbar(pcm,ax=ax)
cbar.set_label('wins speed [m/s]')
plt.show()
plt.savefig('../results/event20230907/wind_20230907T1600.png',dpi=600)
plt.close()


#significant wave hights

#ERA5
swh_era5=xr.open_dataset(str(Path(os.environ["RESEARCH_DATA"]) / "ERA5/swh_NP_2023-2025/era5_swh_202309.nc")).sel(valid_time='2023-09-07T16:00')
mask=(swh_era5.latitude>19)&(swh_era5.latitude<51)&(swh_era5.longitude>119)&(swh_era5.longitude<151)
swh_era5=swh_era5['swh'].where(mask)

#SWOT
wave=data['swh_karin']
lat=wave.latitude
lon=wave.longitude
mask=(lat>20)&(lat<50)&(lon>120)&(lon<150)&(data['swh_karin_qual']==0)
wave=wave.where(mask,drop=True)

#plot
level=np.arange(1.0,3.0,0.25)
cmap=plt.colormaps['plasma']
ax=plt.axes(projection=ccrs.PlateCarree())
ax.coastlines()
ax.set_extent([135,150,35,45])
ax.pcolormesh(swh_era5.longitude.values, swh_era5.latitude.values, swh_era5.values,vmin=1.0,vmax=3.0,shading='nearest',cmap=cmap,transform=ccrs.PlateCarree())
pcm=ax.pcolormesh(wave.longitude.values,wave.latitude.values,wave.values,vmin=1.0,vmax=3.0,shading='nearest',cmap=cmap,transform=ccrs.PlateCarree())
cbar=plt.colorbar(pcm,ax=ax)
ax.add_feature(cfeature.LAND, facecolor='0.85', zorder=10)
cbar.set_label('significant wave height [m]')
plt.show()
plt.savefig('../results/event20230907/wave_20230907T1600.png',dpi=600)
plt.close()

