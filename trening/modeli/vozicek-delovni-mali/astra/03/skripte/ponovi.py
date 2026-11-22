"""Celotna ponovitev iz STEP v isti mapi poskusa. Začni z nameščenimi requirements.txt."""
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import argparse

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--zacetek",type=datetime.fromisoformat,help="Začetek izdelave poskusa s časovnim pasom.")
    start=parser.parse_args().zacetek or datetime.now().astimezone()
    assert start.utcoffset() is not None
    out=Path(__file__).resolve().parents[1]
    (out/"izvoz").mkdir(exist_ok=True)
    with TemporaryDirectory(prefix=".izdelava-",dir=out) as cache:
        os.environ["FINES_ASTRA03_CACHE"]=cache
        from priprava import collect
        from dostop import wheel_access
        from model import build
        from studio import Renderer
        from kamera import make_plan
        from film import Film
        from preveri import verify
        from zapis import publish
        collect()
        wheel_access()
        build()
        renderer=Renderer()
        make_plan(renderer)
        film=Film(renderer)
        film.proof()
        film.encode()
        verify(film)
        publish(start)
if __name__=="__main__":main()
