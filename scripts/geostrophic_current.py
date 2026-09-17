import os
from pathlib import Path

import xarray as xr
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from matplotlib import pyplot as plt 
import cartopy.crs as ccrs 
from matplotlib.colors import BoundaryNorm
from matplotlib.ticker import MaxNLocator
import cartopy.feature as cfeature

data=xr.open_dataset(str(Path(os.environ["RESEARCH_DATA"]) / "SWOT/L2_LR_SSH_Expert/SWOT_L2_LR_SSH_Expert_003_185_20230907T125013_20230907T134141_PGC0_01.nc"))
data = data.assign_coords(longitude=((data.longitude + 180) % 360) - 180)
ssh=data['ssha_karin']+data['height_cor_xover']+data['mean_dynamic_topography']
lat,lon=data.latitude,data.longitude
qual=(data['ssha_karin_qual']==0)&(data['height_cor_xover_qual']==0)&(data['ancillary_surface_classification_flag']==0)
box=(lat>20)&(lat<50)&(lon>120)&(lon<150)
w=4
j=np.flatnonzero(box.any('num_pixels').values)
ssh=ssh.where(qual).isel(num_lines=slice(j[0]-w,j[-1]+1+w))
lat,lon=ssh.latitude,ssh.longitude
"""
ax=plt.axes(projection=ccrs.PlateCarree())
ax.coastlines()
ax.set_extent([135,150,35,45])
ax=plt.pcolormesh(ssh.longitude.values,ssh.latitude.values,ssh.values,shading='nearest',transform=ccrs.PlateCarree())
plt.show()
#plt.savefig('../results/event20230907/adt_20230907T1600.png',dpi=600)
"""
R=6371e3
omega=2*np.pi/(23*60*60+56*60+4)
g=9.8
plane=(9,9)
Z=sliding_window_view(ssh.values,plane)
LAT=sliding_window_view(lat.values,plane)
LON=sliding_window_view(lon.values,plane)
lat0=LAT[:,:,w,w][:,:,None,None]
lon0=LON[:,:,w,w][:,:,None,None]
dlon=LON-lon0
dlat=LAT-lat0
x=R*np.cos(np.deg2rad(lat0))*np.deg2rad(dlon)
y=R*np.deg2rad(dlat)
ok=np.isfinite(Z)&np.isfinite(x)&np.isfinite(y)
n,m=Z.shape[:2]
dhdx=np.full((n,m),np.nan)
dhdy=np.full((n,m),np.nan)
for i in range(n):
    for j in range(m):
        k=ok[i,j]
        if k.sum()<40:
            continue
        A=np.column_stack([np.ones(k.sum()),x[i,j][k],y[i,j][k]])
        a,b,c=np.linalg.lstsq(A,Z[i,j][k],rcond=None)[0]
        dhdx[i,j]=b
        dhdy[i,j]=c

la_c = ssh.latitude.values[w:-w, w:-w]
lo_c = ssh.longitude.values[w:-w, w:-w]
f = 2*omega*np.sin(np.deg2rad(la_c))
u = -(g/f)*dhdy
v =  (g/f)*dhdx
cp=np.sqrt(u**2+v**2)

#plot
level=np.arange(0,1.5,0.25)
cmap=plt.colormaps['viridis']
ax=plt.axes(projection=ccrs.PlateCarree())
ax.coastlines()
ax.set_extent([135,150,35,45])
pcm=ax.pcolormesh(lo_c,la_c,cp,vmin=0,vmax=1.5,shading='nearest',cmap=cmap,transform=ccrs.PlateCarree())
ax.add_feature(cfeature.LAND, facecolor='0.85', zorder=10)
cbar=plt.colorbar(pcm,ax=ax)
cbar.set_label('Current speed [m]')
plt.show()
plt.savefig('../results/event20230907/current_20230907T1600.png',dpi=600)
plt.close()
