#!/usr/bin/env bash
set -u
cd "$(dirname "$0")/.."
export ELECTRON_MIRROR="https://npmmirror.com/mirrors/electron/"
export ELECTRON_BUILDER_BINARIES_MIRROR="https://npmmirror.com/mirrors/electron-builder-binaries/"
npx electron-builder --win nsis --config electron-builder.yml 2>&1
