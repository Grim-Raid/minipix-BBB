#!/bin/bash

# End-to-end software test for BeagleBone: dummy → example_interface → gatherer.
# Uses socat virtual serial port pairs — no hardware required.
#
# Usage:
#   ./test.sh [data_folder]

set -e

MY_PATH=$(dirname "$0")
MY_PATH=$(cd "$MY_PATH" && pwd)
SOFTWARE_PATH=$(cd "$MY_PATH/../.." && pwd)
BUILD_PATH="$SOFTWARE_PATH/build"

BAUD_RATE=921600
FRAME_TIME=250    # ms per acquisition
FRAME_COUNT=10
DEFAULT_DATA="$MY_PATH/../../vzlusat1-timepix-data/data/raw/above_europe"
DATA_FOLDER="${1:-$DEFAULT_DATA}"
OUT_DIR="$MY_PATH/out/test"
OUT_FILE="$OUT_DIR/data.txt"

TTY0=/tmp/ttyBBtest0
TTY1=/tmp/ttyBBtest1
TTY2=/tmp/ttyBBtest2
TTY3=/tmp/ttyBBtest3

DUMMY_BIN="$BUILD_PATH/dummy/beaglebone/minipix_dummy_bbb"
IFACE_BIN="$BUILD_PATH/example_interface/linux/example_interface_linux"
GATHERER_BIN="$BUILD_PATH/gatherer/gatherer_tot_toa"

# ---------------------------------------------------------------------------
# Cleanup on exit
# ---------------------------------------------------------------------------

cleanup() {
  echo ""
  echo "Cleaning up..."
  kill "${SOCAT1_PID}" "${SOCAT2_PID}" "${DUMMY_PID}" "${IFACE_PID}" 2>/dev/null || true
  rm -f "$TTY0" "$TTY1" "$TTY2" "$TTY3"
}
trap cleanup EXIT

# ---------------------------------------------------------------------------
# 1. Check prerequisites
# ---------------------------------------------------------------------------

for bin in "$DUMMY_BIN" "$IFACE_BIN" "$GATHERER_BIN"; do
  if [ ! -x "$bin" ]; then
    echo "ERROR: Binary not found: $bin"
    echo "Run './compile.sh' from $SOFTWARE_PATH first."
    exit 1
  fi
done

if ! command -v socat &>/dev/null; then
  echo "ERROR: socat not found. Install with: sudo apt-get install socat"
  exit 1
fi

if [ ! -d "$DATA_FOLDER" ]; then
  echo "ERROR: Data folder not found: $DATA_FOLDER"
  echo "Initialize the submodule with: git submodule update --init --recursive"
  exit 1
fi

mkdir -p "$OUT_DIR"
rm -f "$OUT_FILE"

# ---------------------------------------------------------------------------
# 2. Create virtual serial port pairs
# ---------------------------------------------------------------------------

echo "Creating virtual serial ports..."
socat -d -d PTY,link="$TTY0",rawer,echo=0 PTY,link="$TTY1",rawer,echo=0 &
SOCAT1_PID=$!
socat -d -d PTY,link="$TTY2",rawer,echo=0 PTY,link="$TTY3",rawer,echo=0 &
SOCAT2_PID=$!

sleep 0.5

# ---------------------------------------------------------------------------
# 3. Start dummy emulator
# ---------------------------------------------------------------------------

echo "Starting MiniPIX dummy on $TTY0..."
"$DUMMY_BIN" "$TTY0" "$BAUD_RATE" 1 "$DATA_FOLDER" &
DUMMY_PID=$!

# ---------------------------------------------------------------------------
# 4. Start example interface (MUI bridge)
# ---------------------------------------------------------------------------

sleep 0.5
echo "Starting example interface ($TTY1 <-> $TTY2)..."
"$IFACE_BIN" "$TTY1" "$BAUD_RATE" 1 "$TTY2" "$BAUD_RATE" 1 &
IFACE_PID=$!

# ---------------------------------------------------------------------------
# 5. Run gatherer (exits after FRAME_COUNT frames)
# ---------------------------------------------------------------------------

sleep 1.0
echo "Starting gatherer on $TTY3 — collecting $FRAME_COUNT frames..."
"$GATHERER_BIN" "$TTY3" "$BAUD_RATE" 1 "$OUT_FILE" "$FRAME_TIME" "$FRAME_COUNT" 1

# ---------------------------------------------------------------------------
# 6. Validate output
# ---------------------------------------------------------------------------

echo ""
if [ ! -f "$OUT_FILE" ]; then
  echo "FAIL: Output file not created: $OUT_FILE"
  exit 1
fi

LINE_COUNT=$(wc -l < "$OUT_FILE")
if [ "$LINE_COUNT" -lt 1 ]; then
  echo "FAIL: Output file is empty."
  exit 1
fi

echo "PASS: $LINE_COUNT lines written to $OUT_FILE"
echo "Test complete."
