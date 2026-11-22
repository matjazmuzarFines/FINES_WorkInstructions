#!/usr/bin/env bash
# Celoten poskus 03: STEP -> deli.json + GLB -> spoji.json (+ vijaki) -> koraki.json (+ trki) -> kamere z merjeno vidnostjo -> video.mp4 + predogled.png
# Zagon iz korena repozitorija (Git Bash):  bash trening/modeli/vozicek-delovni-mali/fable/03/skripte/zazeni_vse.sh
# Okolje (enkrat): bash trening/modeli/vozicek-delovni-mali/fable/03/skripte/00_okolje.sh
set -euo pipefail
PY=trening/okolje/fable/venv312/Scripts/python
S=trening/modeli/vozicek-delovni-mali/fable/03/skripte
export PYTHONIOENCODING=utf-8
"$PY" "$S/01_analiza_in_izvoz.py"   # ~25 s  STEP -> deli.json, mreze, GLB
"$PY" "$S/02_spoji.py"              # ~5 s   luknje + stiki -> spoji.json, vijacni material
"$PY" "$S/03_koraki.py"             # ~10 s  koraki + kontrola trkov
"$PY" "$S/04_render.py"             # ~22 min video (potrebuje ffmpeg v PATH); --slicice = samo kontrolne slicice in kontrole (~2,5 min)
