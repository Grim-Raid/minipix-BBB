#!/bin/bash

# End-to-end hardware test: example_interface (UART1) -> gatherer.
# Connects to a real MiniPIX on /dev/ttyS1 via the BeagleBone UART1.
#
# Wiring (BeagleBone P9 header):
#   P9_24 -> MiniPIX RX
#   P9_26 -> MiniPIX TX
#   GND   -> MiniPIX GND
#
# Usage:
#   ./test_hw.sh [frame_count] [acq_time_ms]

set -e

MY_PATH=$(dirname "$0")
MY_PATH=$(cd "$MY_PATH" && pwd)
SOFTWARE_PATH=$(cd "$MY_PATH/../.." && pwd)
BUILD_PATH="$SOFTWARE_PATH/build"

UART_DEV="/dev/ttyS1"
BAUD_RATE=921600
FRAME_COUNT="${1:-10}"
FRAME_TIME="${2:-250}"
OUT_DIR="$MY_PATH/out/hw_test"
OUT_FILE="$OUT_DIR/data.txt"

# Virtual port pair between example_interface and gatherer
TTY_IFACE=/tmp/ttyHW_iface
TTY_GATH=/tmp/ttyHW_gath

IFACE_BIN="$BUILD_PATH/example_interface/linux/example_interface"
GATHERER_BIN="$BUILD_PATH/gatherer/gatherer"

# ---------------------------------------------------------------------------
# Cleanup on exit
# ---------------------------------------------------------------------------

cleanup() {
  echo ""
  echo "Cleaning up..."
  kill "${SOCAT_PID}" "${IFACE_PID}" 2>/dev/null || true
  rm -f "$TTY_IFACE" "$TTY_GATH"
}
trap cleanup EXIT

# ---------------------------------------------------------------------------
# 1. Prerequisites
# ---------------------------------------------------------------------------

for bin in "$IFACE_BIN" "$GATHERER_BIN"; do
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

if [ ! -c "$UART_DEV" ]; then
  echo "ERROR: $UART_DEV not found."
  echo "Make sure BB-UART1-00A0.dtbo is enabled in /boot/uEnv.txt and reboot."
  exit 1
fi

if ! id -nG "$USER" | grep -qw dialout; then
  echo "ERROR: $USER is not in the dialout group."
  echo "Run: sudo usermod -a -G dialout $USER  (then log out and back in)"
  exit 1
fi

mkdir -p "$OUT_DIR"
rm -f "$OUT_FILE"

# ---------------------------------------------------------------------------
# 2. Virtual port between example_interface and gatherer
# ---------------------------------------------------------------------------

echo "Creating virtual serial port pair for example_interface <-> gatherer..."
socat -d -d PTY,link="$TTY_IFACE",rawer,echo=0 PTY,link="$TTY_GATH",rawer,echo=0 &
SOCAT_PID=$!

sleep 0.5

# ---------------------------------------------------------------------------
# 3. Start example_interface: real UART1 to MiniPIX, virtual port to gatherer
# ---------------------------------------------------------------------------

echo "Starting example_interface (MiniPIX on $UART_DEV, gatherer on $TTY_IFACE)..."
"$IFACE_BIN" "$UART_DEV" "$BAUD_RATE" 0 "$TTY_IFACE" "$BAUD_RATE" 1 &
IFACE_PID=$!

# ---------------------------------------------------------------------------
# 4. Run gatherer
# ---------------------------------------------------------------------------

sleep 1.0
echo "Starting gatherer on $TTY_GATH — collecting $FRAME_COUNT frames at ${FRAME_TIME}ms each..."
"$GATHERER_BIN" "$TTY_GATH" "$BAUD_RATE" 1 "$OUT_FILE" "$FRAME_COUNT" "$FRAME_TIME"

# ---------------------------------------------------------------------------
# 5. Validate output
# ---------------------------------------------------------------------------

echo ""
if [ ! -f "$OUT_FILE" ]; then
  echo "FAIL: Output file not created: $OUT_FILE"
  exit 1
fi

LINE_COUNT=$(wc -l < "$OUT_FILE")
if [ "$LINE_COUNT" -lt 1 ]; then
  echo "FAIL: Output file is empty — MiniPIX may not have responded."
  exit 1
fi

echo "PASS: $LINE_COUNT lines written to $OUT_FILE"
echo "Test complete."
