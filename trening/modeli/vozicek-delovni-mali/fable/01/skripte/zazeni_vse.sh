#!/usr/bin/env bash
# Celoten poskus: STEP -> deli.json + GLB -> koraki.json (+ kontrola trkov) -> video.mp4 + predogled.png
# Zagon iz korena repozitorija (Git Bash):  bash trening/modeli/vozicek-delovni-mali/fable/01/skripte/zazeni_vse.sh
set -euo pipefail
PY=trening/okolje/fable/venv312/Scripts/python
S=trening/modeli/vozicek-delovni-mali/fable/01/skripte
export PYTHONIOENCODING=utf-8
"$PY" "$S/01_analiza_in_izvoz.py"   # ~15 s
"$PY" "$S/02_koraki_in_trki.py"     # ~17 s
"$PY" "$S/03_render.py"             # ~90 s (potrebuje ffmpeg v PATH)
