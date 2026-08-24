#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
echo "Place libDepthVistaSDK.so and deps in: $(pwd)"
if [ ! -d venv ]; then python3 -m venv venv; fi
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python depthvista_camera_live.py
