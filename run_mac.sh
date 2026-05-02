#!/bin/bash
# Launch the robot on macOS using Python 3.11 + Kokoro TTS.
# DYLD_LIBRARY_PATH is required because Homebrew Python 3.11 links against
# a newer libexpat than the one bundled with this macOS version.
cd "$(dirname "$0")"
export DYLD_LIBRARY_PATH="/opt/homebrew/opt/expat/lib:$DYLD_LIBRARY_PATH"
exec python3.11 scripts/main_mac.py "$@"
