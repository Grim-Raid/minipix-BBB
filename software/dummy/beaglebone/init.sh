#!/bin/bash

# BeagleBone Black init script for the MiniPIX dummy emulator on UART1.
#
# UART1 pinout:
#   P9_24  →  UART1 TX
#   P9_26  →  UART1 RX
#
# Usage:
#   ./init.sh [data_folder]
#
# If data_folder is not given, defaults to the bundled VZLUSAT-1 dataset.

set -e

MY_PATH=`dirname "$0"`
MY_PATH=`( cd "$MY_PATH" && pwd )`

UART_DEV="/dev/ttyS1"
BAUD_RATE=921600
DEFAULT_DATA="${MY_PATH}/../../vzlusat1-timepix-data/data/raw/above_europe"
DATA_FOLDER="${1:-$DEFAULT_DATA}"

# ---------------------------------------------------------------------------
# 1. Check UART1 device and dialout group membership
# ---------------------------------------------------------------------------

# On kernel 6.x the BB-UART1 overlay loaded via /boot/uEnv.txt handles pin
# mux at boot — no config-pin needed.
if [ ! -c "${UART_DEV}" ]; then
  echo "ERROR: ${UART_DEV} not found."
  echo "Make sure BB-UART1-00A0.dtbo is enabled in /boot/uEnv.txt and reboot."
  exit 1
fi
echo "${UART_DEV} is present."

if ! id -nG "$USER" | grep -qw dialout; then
  echo "WARNING: $USER is not in the dialout group. Adding now (requires sudo)..."
  sudo usermod -a -G dialout "$USER"
  echo "Group added. You may need to log out and back in, or run: newgrp dialout"
  echo "Re-run this script after rejoining the group."
  exit 0
fi

# ---------------------------------------------------------------------------
# 2. Build the dummy if the binary is not already up to date
# ---------------------------------------------------------------------------

BINARY="${MY_PATH}/build/minipix_dummy_bbb"

echo "Building MiniPIX dummy..."
cd "$MY_PATH"
[ ! -e build ] && mkdir build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
cd "$MY_PATH"

# ---------------------------------------------------------------------------
# 3. Start the dummy emulator
# ---------------------------------------------------------------------------

echo "Starting MiniPIX dummy on ${UART_DEV} at ${BAUD_RATE} baud"
echo "  Data folder: ${DATA_FOLDER}"

exec "${BINARY}" "${UART_DEV}" "${BAUD_RATE}" 0 "${DATA_FOLDER}"
