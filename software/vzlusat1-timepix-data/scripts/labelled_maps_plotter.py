#!/usr/bin/python3

# fullres_dosimetry.py se poziva aktualne k plotovani

import os
from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import griddata, Rbf
from pykrige.ok import OrdinaryKriging
import matplotlib.ticker as ticker # for colorbar
from matplotlib.colors import ListedColormap
import matplotlib
import matplotlib.colors as colors
from scipy.spatial.distance import pdist, squareform, cdist
from geopy.distance import great_circle
from scipy.optimize import curve_fit

import sys
import argparse
import os

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import SymLogNorm

from data_processing.data_loader import DataLoader, DEFAULT_DATA_DIRECTORY
from data_processing.utils import fullres_from_clusters
from data_processing.map_tools import create_background_map, add_points_to_map

PARTICLE_CLASSES = ['track_curly', 'track_lowres', 'drop', 'blob_branched', 'blob_small', 'track_straight', 'blob_big', 'other', 'dot']

# #{ energykEv2J()

def energykEv2J(kev):
  return (1000.0 * kev) / (6.242e18);

# #} end of energykEv2J()

# #{ transparent colormap

# for modifying existing colormap to be transparent
import matplotlib.pylab as pl
from matplotlib.colors import ListedColormap

def colormapToTransparent(original):

    # mutate the colormap of a choice to be transparent at the low end
    cmap = original
    # get the original colormap colors
    my_cmap = cmap(np.arange(cmap.N))
    # set alpha
    my_cmap[:,-1] = np.linspace(0.1, 1, cmap.N)
    # create the new colormap
    my_cmap = ListedColormap(my_cmap)

    return my_cmap

# prepare a transparent colormap
my_cm = colormapToTransparent(pl.cm.jet)

# #} end of colormap

# #{ formatting log scale lables

# formatting log scale lables
def log_fmt(x, pos):
    if x == 0:
        return '0'
    else:
        return '{}e{}'.format(int(np.power(10, x) / (np.power(10, np.floor(x)))), int(np.floor(x)))

# #} end of formatting log scale lables

# #{ createMap()

def createMap(projection, lat=0, lon=0):

    m = []

    if projection == 'ortho':
        m = Basemap(projection=projection, lat_0=lat, lon_0=lon, resolution='l', suppress_ticks=True)
    else:
        m = Basemap(projection=projection, suppress_ticks=True)

    # draw continents
    # m.drawparallels(np.arange(-90, 91, 30))
    # m.drawmeridians(np.arange(-180, 181, 60))
    m.drawcoastlines(linewidth=1.25, zorder=2)
    m.drawmapboundary(fill_color='white')

    return m

# #} end of createMap()

# #{ cart2latlong()

def cart2latlong(pts):
    lats = np.arcsin(pts[:,-1])*180/3.141592653
    longs = np.arctan2(pts[:,0], pts[:,1])*180/3.14141592653
    return lats, longs

# #} end of cart2latlong()

# #{ class Sphere Face

class Face():

    def __init__(self, init_verts):
        self.vertices = np.zeros((3,3))
        self.vertices = init_verts

    def get_center(self):
        c = np.mean(self.vertices, axis=0)
        return c/np.linalg.norm(c)

    def subdivide_once(self):
        e01 = np.mean(self.vertices[(0,1),:], axis=0)
        e12 = np.mean(self.vertices[(1,2),:], axis=0)
        e20 = np.mean(self.vertices[(0,2),:], axis=0)
        f1 = Face(np.vstack((self.vertices[0,:], e01, e20)))
        f2 = Face(np.vstack((self.vertices[1,:], e01, e12)))
        f3 = Face(np.vstack((self.vertices[2,:], e20, e12)))
        f4 = Face(np.vstack((e01, e12, e20)))
        new_faces = [f1, f2, f3, f4]
        for f in new_faces:
            f.normalize()
        return new_faces

    def normalize(self):
        vertNorm = np.linalg.norm(self.vertices, axis=1)
        vertNorm= np.repeat(np.atleast_2d(vertNorm).transpose(),
                            repeats=3, axis=1)
        self.vertices = self.vertices/vertNorm

# #} end of class Face

# #{ class Sphere

class Sphere():

    def __init__(self, n_subdivs=3):

        v = np.array([[1,1,1],
                      [-1,-1,1],
                      [-1,1,-1],
                      [1,-1,-1]])
        f1 = Face(v[(0,1,2),:]);
        f2 = Face(v[(1,2,3),:]);
        f3 = Face(v[(0,2,3),:]);
        f4 = Face(v[(0,1,3),:]);
        self.faces = [f1,f2,f3,f4]
        v = np.array([[ 1, 0, 0],
                      [ 0, 1, 0],
                      [-1, 0, 0],
                      [ 0,-1, 0],
                      [ 0, 0, 1],
                      [ 0, 0,-1]])
        self.faces = list()
        self.faces.append(Face(v[(0,3,4),:]))
        self.faces.append(Face(v[(0,1,4),:]))
        self.faces.append(Face(v[(1,2,4),:]))
        self.faces.append(Face(v[(2,3,4),:]))
        self.faces.append(Face(v[(0,3,5),:]))
        self.faces.append(Face(v[(0,5,1),:]))
        self.faces.append(Face(v[(5,1,2),:]))
        self.faces.append(Face(v[(5,2,3),:]))

        for f in self.faces:
            f.normalize()

        for i in range(0, n_subdivs):
            self.subdivide()

    def subdivide(self):
        new_faces = list()
        for f in self.faces:
            res = f.subdivide_once()
            new_faces.extend(res)
        self.faces = new_faces

    def get_points(self):
        pts = np.zeros((len(self.faces), 3))
        for i,f in enumerate(self.faces):
            pts[i, :] = f.get_center()
        return pts

    def show(self):
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        pts = self.get_points()
        ax.scatter(pts[:,0], pts[:,1], pts[:,2], marker='.')
        ax.set_xlim([-1,1])
        ax.set_ylim([-1,1])
        ax.set_zlim([-1,1])
        plt.show()

# #} end of Sphere

# #{ class Display
class Display:

    # #{ class Kriging_Interpolator

    class Kriging_Interpolator:

        def semivar_model(xdata, *params):
            return params[0]+params[1]*(1-np.exp(-xdata/params[2]))

        def __init__(self):
            self.model_points = []
            self.model_values = []
            self.model = []

        def fit(self, coordinates, values):
            self.model_points = np.fliplr(coordinates)
            self.model_points[:,0] = self.model_points[:,0]+180
            self.model_values = np.log(values+0.00001).astype(dtype=np.float16)
            self.model = OrdinaryKriging(self.model_points[:,0], self.model_points[:,1], self.model_values, coordinates_type='geographic', verbose=True, enable_plotting=False, variogram_model='spherical', nlags=6)

        def predict(self, coordinates):
            coordinates = np.fliplr(coordinates)
            self.model_points = np.fliplr(coordinates)
            coordinates[:,0] = coordinates[:,0]+180
            z, s = self.model.execute(style='points', xpoints=coordinates[:,0], backend='loop',
                                      ypoints=coordinates[:,1], n_closest_points=3)
            return np.exp(z), np.array([i for i in range(0,z.shape[0])]), -np.ones(z.shape[0])

    # #} end of Kriging_Interpolator

    # #{ __init__

    def __init__(self, data_loader, filter):

        self.data_loader = data_loader

        self.filter = filter

        self.iterator_idx = data_loader.get_index_by_filename(data_loader.current_filename)

        filecount = data_loader.get_file_count()

        self.lats = np.zeros(filecount)
        self.longs = np.zeros(filecount)
        self.data = np.zeros(filecount)

        filenames = self.data_loader.get_sorted_filenames()

        detector_mass = 5850.0 * (0.0003 * 0.014 * 0.014);

        for filename in filenames:
            idx = self.data_loader.get_index_by_filename(filename)

            next_idx, img_names, metadata, clusters, statistics = self.data_loader.fetch_data(idx, index_shift=1)
            self.lats[idx] = metadata.latitude[0]
            self.longs[idx] = metadata.longitude[0]

            dose_kev = 0.0

            for cluster in clusters:

                if (self.filter is not None) and (cluster.class_name not in self.filter):
                    continue

                for pixel in cluster.pixels:

                    dose_kev += pixel.value

            # uGy / min
            self.data[idx] = 60.0*1e6*((energykEv2J(dose_kev) / detector_mass) / metadata.exposure[0]);

        interpolator = self.Kriging_Interpolator()
        coords = np.vstack((self.lats, self.longs)).transpose()

        self.data = np.array(self.data)

        print("Fitting interpolator")
        interpolator.fit(coordinates=coords, values=self.data)
        print("Interpolator fit done")

        print("Building the sphere")
        s = Sphere(n_subdivs=6)
        print("Sphere finished")

        lat_int, long_int = cart2latlong(s.get_points())
        #add borders to interp full area
        add_long = np.linspace(-180, 180, 1000, endpoint=True);
        add_lat = np.linspace(-90, 90, 500, endpoint=True);

        long_int = np.append(long_int, add_long)
        long_int = np.append(long_int, 180*np.ones(len(add_lat)))
        long_int = np.append(long_int, add_long)
        long_int = np.append(long_int, -180*np.ones(len(add_lat)))
        lat_int = np.append(lat_int, 90*np.ones(len(add_long)))
        lat_int = np.append(lat_int, add_lat)
        lat_int = np.append(lat_int, -90*np.ones(len(add_long)))
        lat_int = np.append(lat_int, add_lat)

        map = Basemap(projection='cyl', lon_0=0, resolution='c', ax=None)
        map.drawcoastlines(linewidth=0.25)
        map.drawcountries(linewidth=0.25)
        map.drawmeridians(np.arange(0, 360, 30))
        map.drawparallels(np.arange(-90, 90, 30))

        self.x, self.y = map(long_int, lat_int)

        lat_int = lat_int.flatten();
        long_int = long_int.flatten();

        print("Interpolator prediction")
        output, ok_coords, errors = interpolator.predict(coordinates=np.vstack((lat_int, long_int)).transpose())

        #interpolated log data
        output_log = np.where(output > 0, np.log10(output), output)
        # output_log = output

        self.x_interp, self.y_interp = np.meshgrid(np.linspace(map.llcrnrx, map.urcrnrx, 500), np.linspace(map.llcrnry, map.urcrnry, 500))
        self.data_interp_log = griddata((self.x, self.y), output_log, (self.x_interp, self.y_interp), method='linear')
        self.data_interp = griddata((self.x, self.y), output, (self.x_interp, self.y_interp), method='linear')

        self.display_data()
    # #}

    # #{ display_data
    def display_data(self):

        fig = plt.figure(1)

        x = self.x.flatten();
        y = self.y.flatten()

        filecount = self.data_loader.get_file_count()
        date_from = self.data_loader.load_metadata(0).readable_time[0]
        date_to = self.data_loader.load_metadata(filecount-1).readable_time[0]
        plt.suptitle('VZLUSAT-1 Timepix radiation dose, {} to {}'.format(date_from, date_to), fontsize=13)

        ax1 = plt.subplot2grid((1, 2), (0, 0))
        m = createMap('cyl')
        x_m, y_m = m(self.longs, self.lats)
        data_log = np.where(self.data > 0, np.log10(self.data), self.data)
        CS = m.scatter(x_m, y_m, c=data_log, cmap=my_cm, zorder=10, vmin=0, vmax=2)
        cb = m.colorbar(location="bottom", label="Z", format=ticker.FuncFormatter(log_fmt)) # draw colorbar
        plt.title('Original data', fontsize=13)
        cb.set_label('Total radiation dose [uGy/min]')

        ax2 = plt.subplot2grid((1, 2), (0, 1))
        m = createMap('cyl')
        m.pcolor(self.x_interp, self.y_interp, self.data_interp_log, cmap=my_cm, vmin=0, vmax=2)
        cb = m.colorbar(location="bottom", label="Z", format=ticker.FuncFormatter(log_fmt)) # draw colorbar
        plt.title('Interpolated data', fontsize=13)
        cb.set_label('Total radiation dose [uGy/min]')

        fig.set_size_inches(15, 5.5)
        plt.tight_layout()

        plt.show()

    # #}

# #}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='VZLUSAT-1 map plotter, use \'-d [path_to_data]\' to select a directory with data to plot a map', formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('-d', metavar='[data_directory]', dest='data_directory', type=str, nargs=1, help='specify a data directory to visualize')
    parser.add_argument('-f', metavar='[filename]', dest='file', type=str, nargs=1, help='specify a file to open')
    parser.add_argument('--filter', metavar='[particle_class]', dest='filter', type=str, nargs=1, help='only display images with a desired particle class')

    args = parser.parse_args()
    user_speficied_directory = False

    if args.data_directory is not None and len(args.data_directory) > 0:
        data_directory = args.data_directory[0]
    else:
        data_directory = None

    if args.file is not None and len(args.file) > 0:
        filename = args.file[0]
    else:
        filename = None

    filter = None
    if args.filter is not None and len(args.filter) > 0:
        filter = args.filter[0].split(' ')
        for filter_class in filter:
            if filter_class not in PARTICLE_CLASSES:
                print('Unknonwn particle class \'' + str(filter_class) + '\', no filter will be used!')
                exit()

    data_loader = DataLoader(data_directory, filename, batch_size=1, all=False)
    disp = Display(data_loader, filter)
