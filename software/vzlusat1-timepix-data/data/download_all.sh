#!/bin/bash

# get the path to this script
MY_PATH=`dirname "$0"`
MY_PATH=`( cd "$MY_PATH" && pwd )`

cd $MY_PATH

echo "Downloading all VZLUSAT-1 data"
wget https://github.com/vzlusat/vzlusat1-timepix-data/raw/data_all/all.tar.gz

echo "Unpacking all VZLUSAT-1 data"
tar -xvzf all.tar.gz
