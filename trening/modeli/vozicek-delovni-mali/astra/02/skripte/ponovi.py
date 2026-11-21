"""Ponovi celoten poskus iz vhodne datoteke STEP."""
import argparse
import os
from pathlib import Path
from datetime import datetime
from tempfile import TemporaryDirectory

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--zacetek",type=datetime.fromisoformat,help="Začetek tekočega poskusa s časovnim pasom.")
    start=parser.parse_args().zacetek or datetime.now().astimezone()
    assert start.utcoffset() is not None
    out=Path(__file__).resolve().parents[1]
    (out/"izvoz").mkdir(exist_ok=True)
    with TemporaryDirectory(prefix=".izdelava-",dir=out) as cache:
        os.environ["FINES_ASTRA02_CACHE"]=cache
        from priprava import collect
        from model import build
        from film import Film
        from preveri import verify
        from zapis import publish
        collect()
        build()
        film=Film()
        film.proof()
        film.encode()
        verify(film)
        publish(start)

