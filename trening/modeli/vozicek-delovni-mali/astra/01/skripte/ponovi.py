"""Ponovni uvoz iz STEP, izvoz, render, pregled videa in poročilo."""
from datetime import datetime
import argparse
from osnova import EXPORT
from izvoz import build
from film import run
from preveri import verify
from zapis import publish


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--zacetek",type=datetime.fromisoformat,help="Začetek že potekajočega poskusa s časovnim pasom.")
    args=parser.parse_args()
    started=args.zacetek or datetime.now().astimezone()
    assert started.utcoffset() is not None
    EXPORT.mkdir(exist_ok=True)
    build()
    run()
    verify()
    publish(started)

