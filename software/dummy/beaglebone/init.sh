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

UART_DEV="/dev/ttyO1"
BAUD_RATE=921600
DEFAULT_DATA="${MY_PATH}/../../vzlusat1-timepix-data/data/raw/above_europe"
DATA_FOLDER="${1:-$DEFAULT_DATA}"

# ---------------------------------------------------------------------------
# 1. Configure UART1 pin mux
# ---------------------------------------------------------------------------

if ! command -v config-pin &>/dev/null; then
  echo "ERROR: config-pin not found. Install it with:"
  echo "  sudo apt-get install bb-cape-overlays"
  exit 1
fi

echo "Configuring UART1 pins (P9_24 TX, P9_26 RX)..."
config-pin P9_24 uart
config-pin P9_26 uart

echo "Pin mux set. Verifying device ${UART_DEV}..."
if [ ! -c "${UART_DEV}" ]; then
  echo "ERROR: ${UART_DEV} not found after pin configuration."
  echo "Make sure the UART1 overlay is enabled. On older images try:"
  echo "  echo BB-UART1 | sudo tee /sys/devices/platform/bone_capemgr/slots"
  exit 1
fi
echo "${UART_DEV} is present."

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
