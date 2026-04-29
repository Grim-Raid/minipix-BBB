#!/bin/bash

MY_PATH=`dirname "$0"`
MY_PATH=`( cd "$MY_PATH" && pwd )`

cd $MY_PATH

[ ! -e build ] && mkdir build
cd build
cmake ..
make
