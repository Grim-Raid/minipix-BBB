# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MiniPIX UART Interface is a C99 library for controlling the MiniPIX TPX3 radiation detector over UART. The repo provides the core library, a low-level communications protocol, reference implementations for Linux and STM32F4, a software emulator (dummy), a data gatherer, and a Python decoder/visualizer.

## Build & Development Commands

**Install dependencies (Linux):**
```sh
cd software && ./install_dep.sh
# Installs: libopencv-dev, tmux, tmuxinator, socat
# Python: pip install -r decoder/requirements.txt
```

**Build all software:**
```sh
cd software && ./compile.sh
# Creates build/ directory, runs cmake .. && make
```

**Run tests:**
```sh
cd software && ./test.sh
# Compiles, runs functional tests, then runs Python analysis
```

**CI build (Ubuntu):**
```sh
.ci/build.sh
```

**Generate API docs:**
```sh
.ci/docs.sh   # Doxygen → deployed to GitHub Pages
```

**Build with CMake directly:**
```sh
cd software && mkdir -p build && cd build && cmake .. && make
```

## Architecture

```
MiniPIX Hardware
       │ UART
       ▼
  LLCP (llcp/)          ← Low-level binary/HEX packet framing (C99)
       │
  MUI (mui/)            ← Main C99 library: commands, callbacks, state machine
       │
  Example Interface     ← User-implemented HW callbacks (linux/, stm32f411/)
       │
  ┌────┴────────┐
  │             │
Dummy/      Gatherer/   ← SW emulator (testing) | Remote data receiver (C++)
Emulator     (C++)
                │
            Decoder/    ← Python: deserialize pixel data, GUI visualizer
```

### Key Components

- **`software/mui/`** — The primary integration target. Users link against this static C99 library and implement the callback interface declared in `mui/include/mui.h`. Controls MiniPIX: acquisition, thresholds, configuration, frame retrieval.
- **`software/llcp/`** — UART protocol layer used internally by MUI. Handles packet framing, CRC, binary vs. HEX modes. Generally not touched by integrators.
- **`software/example_interface/linux/`** — Reference Linux implementation showing how to wire MUI callbacks to a real serial port.
- **`software/example_interface/stm32f411/`** — Reference microcontroller implementation (STM32F4 HAL).
- **`software/dummy/`** — Software-only MiniPIX emulator. Allows testing the full stack without hardware. Linux variant and OneWeb satellite variant.
- **`software/gatherer/`** — C++ application that receives data over UART, optionally displays via OpenCV GUI, and writes raw output files.
- **`software/decoder/`** — Python tool (`decoder.py`) that deserializes raw pixel data into frames and provides a matplotlib/tk visualizer.
- **`software/serial_port/`** — Serial port abstraction shared between components.
- **`software/tmux/`** — Pre-configured tmuxinator sessions for common test setups (with and without hardware).

### MUI Callback Pattern

Integrators must implement these callbacks and pass them to MUI at init:
- `send_char` / `send_string` — write bytes to UART (select one via compile flag)
- `received_measurement_data` — called when a frame arrives
- `received_ack` / `received_nack` — handshake callbacks (or set `MUI_USER_HANDSHAKES`)

### Important Compile Flags

| Flag | Effect |
|---|---|
| `MUI_SEND_STRING=1` | Use `send_string` callback (batch UART writes) |
| `MUI_SEND_CHAR=1` | Use `send_char` callback (byte-by-byte UART writes) |
| `MUI_USER_HANDSHAKES` | Manual ACK/NACK control |
| `LLCP_DEBUG_PRINT` | Enable protocol-level debug output |
| `LLCP_LITTLE_ENDIAN` | Required for most platforms (set in CMake) |

Exactly one of `MUI_SEND_STRING` or `MUI_SEND_CHAR` must be defined.

### Git Submodule

`software/vzlusat1-timepix-data/` contains real Timepix data from the VZLUSAT-1 satellite and is used by the decoder for validation. Initialize with:
```sh
git submodule update --init --recursive
```

## API Documentation

Generated Doxygen docs are deployed at: https://klaxalk.github.io/minipix_uart_interface/
