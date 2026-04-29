#!/usr/bin/env python2

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
from itertools import chain

# #{ create_background_map
def create_background_map(ax):
    m = Basemap(projection='cyl', resolution='l', lat_0=0, lon_0=0, ax=ax)

    m.drawcoastlines(linewidth=0.3)
    m.drawcountries(linewidth=0.3)

    m.drawmeridians(np.arange(0,360,30), linewidth=0.25)
    m.drawparallels(np.arange(-90,90,30), linewidth=0.25)

    return m
# #}

# #{ add_points_to_map
def add_points_to_map(map, points):
    for p in points:
        lat = float(p[0])
        lon = float(p[1])
        x,y = map(lon, lat)
        map.scatter(x, y, 8, marker = 'o', color='r', zorder=5)
    return map
# #}

if __name__ == '__main__':
    fig = plt.figure(figsize=(5, 3), dpi=150)
    map = create_background_map();
    points = [[10,3]]
    map = add_points_to_map(map, points)

    plt.show()
