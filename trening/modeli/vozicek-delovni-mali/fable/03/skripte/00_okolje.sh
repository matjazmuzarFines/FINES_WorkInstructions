#!/usr/bin/env bash
# Pripravi okolje v trening/okolje/fable/ (Git Bash na Windows). Zagon iz korena repozitorija.
# Python 3.15 nima izdaje cadquery-ocp (preverjeno 21. 11. 2026) -> uv namesti Python 3.12.
set -euo pipefail
OK=trening/okolje/fable
mkdir -p "$OK"
python -m venv "$OK/venv315"
"$OK/venv315/Scripts/python" -m pip install -q --upgrade pip uv
export UV_PYTHON_INSTALL_DIR="$PWD/$OK/python" UV_CACHE_DIR="$PWD/$OK/uvcache"
"$OK/venv315/Scripts/uv" venv --python 3.12 "$OK/venv312"
# preverjene verzije: cadquery-ocp 8.0.1.1.0 (OCCT 8.0), vtk 9.6.2, trimesh 5.2.1, numpy 2.5.5, pillow 13.0.0
"$OK/venv315/Scripts/uv" pip install --python "$OK/venv312/Scripts/python.exe" \
  "cadquery-ocp==8.0.1.1.0" "vtk==9.6.2" "trimesh==5.2.1" "numpy==2.5.5" "pillow==13.0.0"
# pisava Inter (odprtokodna, SIL OFL; ista kot v aplikaciji FINES) za glavo, nogo in napise v videu.
# Ce je ni, 04_render.py uporabi Segoe UI in to zapise v izvoz/video_casovnica.json.
if [ ! -f "$OK/pisave/Inter-Bold.ttf" ]; then
  mkdir -p "$OK/pisave"
  curl -sL -o "$OK/pisave/inter.zip" https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip
  unzip -o -j -q "$OK/pisave/inter.zip" "extras/ttf/Inter-Bold.ttf" "extras/ttf/Inter-Regular.ttf" "extras/ttf/Inter-SemiBold.ttf" -d "$OK/pisave"
  rm "$OK/pisave/inter.zip"
fi
