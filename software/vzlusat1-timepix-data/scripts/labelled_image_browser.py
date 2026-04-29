#!/usr/bin/python3

import sys
import argparse
import os

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import SymLogNorm

from data_processing.data_loader import DataLoader, DEFAULT_DATA_DIRECTORY
from data_processing.utils import fullres_from_clusters
from data_processing.map_tools import create_background_map, add_points_to_map

# #{ gui imports
import tkinter as tk
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import FuncFormatter
from PIL import Image, ImageTk
# #}

SMALL_SIZE = 7
MEDIUM_SIZE = 9
TEXT_DATA_SIZE = 10
TICK_DIST_THRESHOLD = 10

COLORMAPS = ['viridis', 'plasma', 'magma', 'Greys', 'Blues', 'YlOrRd', 'bone']
PARTICLE_CLASSES = ['track_curly', 'track_lowres', 'drop', 'blob_branched', 'blob_small', 'track_straight', 'blob_big', 'other', 'dot']

# #{ build_ticks
def build_ticks(end, num=5):
    xvalues = np.linspace(-4, 0, num=num, endpoint=True)
    ticks = [0]
    for x in xvalues:
        ticks.append(np.exp(x) * end)
    return ticks
# #}

# #{ class Display
class Display:

    # #{ init
    def __init__(self, data_loader):
        self.window = tk.Tk()
        self.data_loader = data_loader

        self.iterator_idx = data_loader.get_index_by_filename(data_loader.current_filename)
        self.colormap_idx = 0

        self.img_names = ''
        self.metadata = None
        self.clusters = None
        self.statistics = None
        self.fullres_image = None

        plt.rc('font', size=SMALL_SIZE)          # controls default text sizes
        plt.rc('axes', titlesize=SMALL_SIZE)     # fontsize of the axes title
        plt.rc('axes', labelsize=MEDIUM_SIZE)    # fontsize of the x and y labels
        plt.rc('xtick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
        plt.rc('ytick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
        plt.rc('legend', fontsize=SMALL_SIZE)    # legend fontsize
        plt.rc('figure', titlesize=MEDIUM_SIZE)  # fontsize of the figure title

        self.load_next_image(index_shift=0)
        self.display_data()
        self.window.geometry("+550+150")
        self.window.mainloop()
    # #}

    # #{ display_data
    def display_data(self):
        if self.window is None:
            self.window = tk.Tk()
        else:
            content = self.window.winfo_children()
            for c in content:
                c.destroy()

        # #{ draw map
        map_frame = tk.Frame(self.window, bg='grey')
        map_frame.grid(row=0,column=0,columnspan=2, sticky='wens')

        fig_map = plt.Figure(figsize=(5,2.5), dpi=150)
        ax_map = fig_map.gca()
        pos = ax_map.get_position()
        pos.x0 = 0.03
        pos.y0 = 0.0
        pos.x1 = 0.97
        pos.y1 = 1.0
        ax_map.set_position(pos)
        m = create_background_map(ax_map);
        measurement_positions = self.metadata.get_gps_coordinates()
        m = add_points_to_map(m, measurement_positions)
        map_canvas = FigureCanvasTkAgg(fig_map, map_frame)
        map_canvas.get_tk_widget().pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)
        # #}

        # #{ draw fullres image
        fig_img = plt.Figure(figsize=(3,2.5), dpi=150)

        image_frame = tk.Frame(self.window, bg='grey')
        image_frame.grid(row=1, column=0, sticky='wens')

        ax = fig_img.gca()
        im = ax.imshow(self.fullres_image.T, cmap=COLORMAPS[self.colormap_idx], norm=SymLogNorm(1), zorder=5)

        divider = make_axes_locatable(ax)
        cax = divider.append_axes('right', size='5%', pad=0.12)

        # TODO do not use exp notation for labels
        cbar = fig_img.colorbar(im,ax=ax, extend='neither', cax=cax)

        ax.set_xlabel('X [-]', fontsize=SMALL_SIZE, labelpad=0)
        ax.set_ylabel('Y [-]', fontsize=SMALL_SIZE, labelpad=3)
        if len(self.img_names) > 1:
            ax.set_title('\'' + self.img_names[0] + '-' + self.img_names[-1] + '\'', fontsize=SMALL_SIZE)
        else:
            ax.set_title('\'' + self.img_names[0] + '\'', fontsize=MEDIUM_SIZE)

        cbar.ax.set_ylabel('Energy [keV]', fontsize=SMALL_SIZE, labelpad=3)
        ticks = build_ticks(end=np.amax(self.fullres_image))
        cbar.set_ticks(ticks)
        formatter = FuncFormatter(self.format_energy_ticks)
        cbar.ax.yaxis.set_major_formatter(formatter)
        pos = ax.get_position()
        pos.y0 = 0.12
        pos.x0 = 0.03
        pos.y1 = 0.91
        pos.x1 = 0.95
        ax.set_position(pos)

        img_canvas = FigureCanvasTkAgg(fig_img, image_frame)
        img_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        # #}

        # #{ show metadata
        text_frame = tk.Frame(self.window, bg='grey')
        text_frame.grid(row=1, column=1, sticky='wens')
        text_widget = tk.Text(text_frame, state='normal', width=20, height=5, borderwidth=0, relief='flat')
        text_widget.usetex = True
        text_data = self.get_printable_data()
        text_widget.insert(1.0, text_data)
        text_widget.configure(state='disabled', font=("DejaVu Sans", TEXT_DATA_SIZE))
        text_widget.pack(fill=tk.BOTH, expand=True)
        # #}

        # #{ button panel
        button_frame = tk.Frame(self.window, relief=tk.RAISED, borderwidth=1)
        button_frame.grid(row=2, column=0, columnspan=2, sticky='wens')

        next_button = tk.Button(button_frame, text='Next', command=self.on_next_button_click)
        next_button.pack(side=tk.RIGHT)

        previous_button = tk.Button(button_frame, text='Previous', command=self.on_previous_button_click)
        previous_button.pack(side=tk.LEFT)

        change_color_button = tk.Button(button_frame, text='Change color', command=self.on_change_color_button_click)
        change_color_button.pack(side=tk.BOTTOM)
        # #}

    # #}

    # #{ get_total_energy
    def get_total_energy(self):
        e = 0.0
        for c in self.clusters:
            for p in c.pixels:
                e += p.value
        return e
    # #}

    # #{ get_printable_data
    def get_printable_data(self):
        data = 'Image statistics:\n'
        data += '    track_curly: ' + str(self.statistics['track_curly']) + '\n'
        data += '    track_lowres: ' + str(self.statistics['track_lowres']) + '\n'
        data += '    drop: ' + str(self.statistics['drop']) + '\n'
        data += '    blob_branched: ' + str(self.statistics['blob_branched']) + '\n'
        data += '    blob_small: ' + str(self.statistics['blob_small']) + '\n'
        data += '    track_straight: ' + str(self.statistics['track_straight']) + '\n'
        data += '    blob_big: ' + str(self.statistics['blob_big']) + '\n'
        data += '    other: ' + str(self.statistics['other']) + '\n'
        data += '    dot: ' + str(self.statistics['dot']) + '\n'

        if self.data_loader.filter is not None:
            data += 'Filter:\n'
            data += '    ' + str(self.data_loader.filter) + ' only\n\n'

        data += 'Sensor metadata:\n'
        data += '    Pixels hit: ' + str(self.metadata.pixel_count) + '\n'
        data += '    Total energy: ' + str(self.get_total_energy()) + ' keV\n'
        if len(self.metadata.exposure) > 1:
            data += '    Acquisition time: ' + str(min(self.metadata.exposure)) + ' to ' + str(max(self.metadata.exposure)) + ' s\n'
        else:
            data += '    Acquisition time: ' + str(self.metadata.exposure[0]) + ' s\n'
        if len(self.metadata.temperature) > 1:
            data += '    Temperature: ' + str(min(self.metadata.temperature)) + ' to ' + str(max(self.metadata.temperature)) + u'\u2103' + '\n\n'
        else:
            data += '    Temperature: ' + str(self.metadata.temperature[0]) + u'\u2103' + '\n\n'
        if len(self.metadata.readable_time) > 1:
            data += 'Timestamp:\n   ' + str(self.metadata.readable_time[0]) + ' to\n' + str(self.metadata.readable_time[-1]) + '\n'
        else:
            data += 'Timestamp:\n   ' + str(self.metadata.readable_time[0]) + '\n'
        return data
    # #}

    # #{ on_next_button_click
    def on_next_button_click(self):
        self.load_next_image()
        self.display_data()
    # #}

    # #{ on_previous_button_click
    def on_previous_button_click(self):
        self.load_next_image(index_shift=-1)
        self.display_data()
    # #}

    # #{ on_change_color_button_click
    def on_change_color_button_click(self):
        self.colormap_idx = (self.colormap_idx + 1) % len(COLORMAPS)
        self.display_data()
    # #}

    # #{ load_next_image
    def load_next_image(self, index_shift=1):
        self.iterator_idx, self.img_names, self.metadata, self.clusters, self.statistics = self.data_loader.fetch_data(self.iterator_idx, index_shift)
        self.fullres_image = fullres_from_clusters(self.clusters, filter=self.data_loader.filter)
    # #}

    # #{ format_energy_ticks
    def format_energy_ticks(self, value, tick_pos):
        max_energy = np.amax(self.fullres_image)
        return '%2.2f' % (max_energy * value)
    # #}

# #}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='VZLUSAT data displayer\nThis tool visualizes the radiation measurements taken by the VZLUSAT-1 satellite.\nBefore use, make sure to have access to a directory with labelled data.\n--------------------------------------------------------------------------\nThe default data directory is \'' + DEFAULT_DATA_DIRECTORY + '\'\nTo load data from a different directory, use \'-d [path_to_data]\' or \'--data [path_to_data]\'\n--------------------------------------------------------------------------', formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('-d', metavar='[data_directory]', dest='data_directory', type=str, nargs=1, help='specify a data directory to visualize')
    parser.add_argument('-f', metavar='[filename]', dest='file', type=str, nargs=1, help='specify a file to open')
    parser.add_argument('-b', metavar='[batch_size]', dest='batch_size', type=int, nargs=1, help='specify num of files in a batch')
    parser.add_argument('-a', '--all', action='store_true', help='load all files in a directory as a batch')
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

    if args.batch_size is not None and len(args.batch_size) > 0:
        batch_size = int(args.batch_size[0])
    else:
        batch_size = 1

    filter = None
    if args.filter is not None and len(args.filter) > 0:
        if args.filter[0] in PARTICLE_CLASSES:
            filter = args.filter[0]
        else:
            print('Unknonwn particle class \'' + str(args.filter[0]) + '\', no filter will be used!')

    data_loader = DataLoader(data_directory, filename, batch_size=batch_size, filter=filter, all=args.all)
    disp = Display(data_loader)
