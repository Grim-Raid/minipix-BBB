#!/usr/bin/python2.7

import csv
import os
import json
import re
import numpy as np

from data_processing.utils import Pixel, Cluster, Metadata

METADATA_SUFFIX = '.metadata.txt'
CLUSTERS_SUFFIX = '.clusters.txt'
STATISTICS_SUFFIX = '.statistics.txt'
DEFAULT_DATA_DIRECTORY = 'data/labelled/above_europe'

class DataLoader:

    # #{ init
    def __init__(self, data_dir=None, filename=None, batch_size=1, filter=None, all=False):

        if data_dir is not None:
            if not os.path.isdir(data_dir):
                raise Exception('Path \'' + data_dir + '\' does not point to a valid directory')

            self.data_dir = data_dir
            self.verify_data_dir()

        else:
            self.data_dir = DEFAULT_DATA_DIRECTORY

        self.filenames = self.get_sorted_filenames()
        self.batch_size = batch_size
        self.filter = filter

        if filename is not None:
            fpath = self.data_dir + os.sep + filename + CLUSTERS_SUFFIX
            if os.path.isfile(fpath):
                self.current_filename = filename
            elif os.path.isfile(filename + CLUSTERS_SUFFIX):
                self.current_filename = filename
            else:
                raise Exception('File \'' + filename + '\' does not exist in the current working directory, neither in \'' + str(self.data_dir) + '\'')
        else:
            self.current_filename = self.filenames[0]

        if all:
            self.batch_size = self.get_file_count()
    # #}

    # #{ get_sorted_filenames
    def get_sorted_filenames(self):
        indices = set()
        got_name = False
        name = ''
        for fname in os.listdir(self.data_dir):
            index = ''
            got_number = False
            for letter in fname:
                if letter.isdigit():
                    got_number = True
                    index += letter
                elif not got_name:
                    if letter != '.':
                        name += letter
                    else:
                        got_name = True
                if got_number:
                    indices.add(int(index))
        filenames = list(indices)
        filenames.sort()

        if len(filenames) < 1:
            raise Exception('No file found in directory \'' + str(self.data_dir) + '\' !')

        for i in range(len(filenames)):
            filenames[i] = str(filenames[i]) + name
        return tuple(filenames)
    # #}

    # #{ get_filenames_by_index
    def get_filenames_by_index(self, index, filtered_indices=None):
        ret = []

        if filtered_indices is not None and len(filtered_indices) > 0:
            for i in filtered_indices:
                ret.append(self.filenames[i])
            return ret

        for i in range(index, index + self.batch_size):
            i = i % self.get_file_count()
            ret.append(self.filenames[i])
        return ret
    # #}

    # #{ get_index_by_filename
    def get_index_by_filename(self, filename):
        for i in range(len(self.filenames)):
            if self.filenames[i] == filename:
                return i
    # #}

    # #{ load_metadata
    def load_metadata(self, index, filtered_indices=None):
        accumulated_metadata = None

        filenames = self.get_filenames_by_index(index, filtered_indices=filtered_indices)
        for fname in filenames:
            raw_metadata = {}
            metadata_filepath = os.path.join(self.data_dir, fname + METADATA_SUFFIX)
            if not os.path.isfile(metadata_filepath):
                raise Exception('Path to metadata \'' + metadata_filepath + '\' is not valid')
            with open(metadata_filepath, 'r') as f:
                metadata_lines = f.readlines()
                for line in metadata_lines:
                    line = re.sub('[\r\n]', '', line)
                    segments = line.split(': ')
                    if len(segments) > 1:
                        raw_metadata[segments[0]] = segments[1]
            metadata = Metadata(raw_metadata)
            if accumulated_metadata is not None:
                accumulated_metadata += metadata
            else:
                accumulated_metadata = metadata
        return accumulated_metadata
    # #}

    # #{ load_clusters
    def load_clusters(self, index, filtered_indices=None):
        clusters = []
        filenames = self.get_filenames_by_index(index, filtered_indices=filtered_indices)
        for fname in filenames:
            clusters_filepath = os.path.join(self.data_dir, fname + CLUSTERS_SUFFIX)
            if not os.path.isfile(clusters_filepath):
                raise Exception('Path to cluster data \'' + clusters_filepath + '\' is not valid')
            with open(clusters_filepath, 'r') as f:
                clusters_raw = f.read()
                clusters_unparsed = json.loads(clusters_raw)
                for cu in clusters_unparsed:
                    pixels = []
                    for pu in cu['pixels']:
                        p = Pixel(pu['x'], pu['y'], pu['value'])
                        pixels.append(p)

                    c = Cluster(cu['pos_x'], cu['pos_y'], pixels, cu['cluster_class']['name'], cu['cluster_class']['cluster_class'])
                    clusters.append(c)
        return clusters
    # #}

    # #{ load_statistics
    def load_statistics(self, index):
        accumulated_statistics = {}
        filtered_indices = []
        filenames = self.get_filenames_by_index(index)
        for fname in filenames:
            statistics_filepath = os.path.join(self.data_dir, fname + STATISTICS_SUFFIX)
            if not os.path.isfile(statistics_filepath):
                raise Exception('Path to image statistics \'' + statistics_filepath + '\' is not valid')
            with open(statistics_filepath, 'r') as f:
                statistics_raw = f.read()
                statistics = json.loads(statistics_raw)
                if self.filter is not None:
                    if statistics[self.filter] > 0:
                        filtered_indices.append(self.get_index_by_filename(fname))
                for key, val in statistics.items():
                    if key in accumulated_statistics.keys():
                        accumulated_statistics[key] += val
                    else:
                        accumulated_statistics[key] = val

        if len(filtered_indices) < 1:
            filtered_indices = None
        return accumulated_statistics, filtered_indices
    # #}

    # #{ fetch_data
    def fetch_data(self, index, index_shift):
        img_name = 'Unknown'
        metadata = None
        clusters = None
        statistics = None

        index = (index + index_shift) % self.get_file_count()
        statistics, filtered_indices = self.load_statistics(index)

        if self.filter is not None and filtered_indices is None:
            if(index_shift not in [1,2]):
                index_shift = 1
            return self.fetch_data(index, index_shift)

        img_name = self.get_filenames_by_index(index, filtered_indices=filtered_indices)
        metadata = self.load_metadata(index, filtered_indices=filtered_indices)
        clusters = self.load_clusters(index, filtered_indices=filtered_indices)
        return index, img_name, metadata, clusters, statistics
    # #}

    # #{ get_file_count
    def get_file_count(self):
        return len(self.filenames)
    # #}

    # #{ verify_data_dir
    def verify_data_dir(self):
        filenames = self.get_sorted_filenames()

        if filenames is not None and len(filenames) > 1:
            for fname in filenames:
                f_clusters = fname + CLUSTERS_SUFFIX
                f_metadata = fname + METADATA_SUFFIX
                f_statistics = fname + STATISTICS_SUFFIX
                data_dir = os.listdir(self.data_dir)
                if f_clusters not in data_dir:
                    raise Exception('File \'' + f_clusters + '\' not found!')
                if f_metadata not in data_dir:
                    raise Exception('File \'' + f_metadata + '\' not found!')
                if f_statistics not in data_dir:
                    raise Exception('File \'' + f_statistics + '\' not found!')
    # #}

if __name__ == '__main__':
    dl = DataLoader('../../data/labelled/01_2019-09-25')
    metadata, clusters, statistics = dl.get_data(10)
