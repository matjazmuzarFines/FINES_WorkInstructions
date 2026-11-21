from pathlib import Path
import json
import sys
import os

OUT = Path(__file__).resolve().parents[1]
if (OUT / ".orodja").exists():
    sys.path.insert(0, str(OUT / ".orodja"))
EXPORT = OUT / "izvoz"
CACHE = Path(os.environ.get("FINES_ASTRA02_CACHE",OUT/".priprava"))
SOURCE, = sorted((OUT.parents[1] / "vhod").glob("*.stp"))


def save(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))

