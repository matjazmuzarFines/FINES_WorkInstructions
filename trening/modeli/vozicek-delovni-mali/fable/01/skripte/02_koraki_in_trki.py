"""
Korak 2: predlog montaznih korakov + kontrola trkov (B-Rep, OpenCascade).

- Vrstni red korakov je PREDLOG (ni potrjen s tehnologom) - glej ZNANJE.md, PRAVILO o zaporedju.
- Smer vstavljanja vsakega koraka NI izmisljena: za vsak korak se preizkusijo kandidatne smeri
  in izbere prva, pri kateri se premikajoci deli na celotni poti ne prekrivajo z ze
  namescenimi deli (volumen preseka > PRAG_MM3 = trk).
- Dodatno: staticna kontrola prekrivanja vseh parov delov v koncnem polozaju.

Zagon:
  trening/okolje/fable/venv312/Scripts/python trening/modeli/vozicek-delovni-mali/fable/01/skripte/02_koraki_in_trki.py
Izhodi: koraki.json, izvoz/kontrole_trkov.json
"""
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib

sys.path.insert(0, str(Path(__file__).parent))
from common_occ import POSKUS, load_shapes, translated  # noqa: E402

PRAG_MM3 = 1.0        # presek pod tem je dotik / numericni sum
KORAK_POTI_MM = 5.0   # gostota vzorcenja poti
ZRAK_MM = 0.05        # bbox toleranca

NEZNANO = "ni znano / zahteva potrditev"

# Definicija korakov. "smeri" = kandidati po prednosti.
#  "+Z" ... premik iz smeri (del pride od zgoraj -> od_mm = [0,0,+d])
#  "navzven_X"/"navzven_Y" ... vsak del pride s svoje strani (stran od sredisca sestava)
KORAKI = [
    dict(naslov="Spodnji okvir: vzdolžni cevi", deli=["P001", "P002"], smeri=["+Z", "navzven_Y"], d=300,
         opis="Vzdolžni cevi 30x30x1,5 l=993 (MTC324009902) položi vzporedno na razdalji kot v modelu.",
         kamera="izometrija spredaj-desno, zgoraj", spoj=NEZNANO),
    dict(naslov="Spodnji okvir: prečni cevi", deli=["P003", "P004"], smeri=["+Z", "navzven_X"], d=300,
         opis="Prečni cevi l=493 (MTC324010002) namesti med konca vzdolžnih cevi in tvori pravokotni okvir.",
         kamera="izometrija spredaj-desno, zgoraj", spoj=NEZNANO),
    dict(naslov="Plošče koles na spodnji okvir", deli=["P013", "P014", "P015", "P016"], smeri=["-Z", "navzven_X"], d=200,
         opis="Plošče koles (MTC324039900) namesti v vogale pod spodnji okvir.",
         kamera="izometrija od spodaj", spoj=NEZNANO),
    dict(naslov="Navpične noge", deli=["P005", "P006", "P007", "P008"], smeri=["+Z", "navzven_X", "navzven_Y"], d=500,
         opis="Štiri navpične cevi l=730 (MTC324010102) postavi v vogale okvirja.",
         kamera="izometrija spredaj-desno", spoj=NEZNANO),
    dict(naslov="Spodnja lesena polica", deli=["P018"], smeri=["+Z"], d=900,
         opis="Polico 930x482x18 (MTC324011101) spusti med noge na spodnji okvir.",
         kamera="izometrija spredaj-desno, zgoraj", spoj=NEZNANO),
    dict(naslov="Vmesni povezavi", deli=["P019", "P020"], smeri=["+Z", "navzven_Y", "navzven_X"], d=500,
         opis="Vmesni povezavi 1000 (MTC324011201) namesti vzdolžno med noge na višini vmesne police.",
         kamera="izometrija spredaj-desno", spoj=NEZNANO),
    dict(naslov="Vmesna lesena polica", deli=["P021"], smeri=["+Z"], d=500,
         opis="Polico 930x482x18 (MTC324011101) položi na vmesni povezavi.",
         kamera="izometrija spredaj-desno, zgoraj", spoj=NEZNANO),
    dict(naslov="Zgornje povezave", deli=["P009", "P010", "P011", "P012"], smeri=["+Z", "navzven_Y", "navzven_X"], d=400,
         opis="Zgornje povezave 1000 (MTC324010201) in 500 (MTC324010301) namesti na vrh nog.",
         kamera="izometrija spredaj-desno, zgoraj", spoj=NEZNANO),
    dict(naslov="Zgornja lesena polica", deli=["P017"], smeri=["+Z"], d=400,
         opis="Polico 993x493x18 (MTC324010802) položi na zgornje povezave.",
         kamera="izometrija spredaj-desno, zgoraj", spoj=NEZNANO),
    dict(naslov="Kolesa", deli=["P022", "P023", "P024", "P025"], smeri=["-Z"], d=250,
         opis="Štiri gibljiva kolesa fi80 z zavoro (TENTE) namesti pod plošče koles.",
         kamera="izometrija od spodaj", spoj=NEZNANO,
         opozorila_extra=["Pritrdilni material (vijaki, matice) ni v STEP modelu.",
                          "Ali se voziček za montažo koles obrne, ni znano."]),
    dict(naslov="Ročaj (podsestav MLU124029200)", deli=["P026", "P027", "P028"], smeri=["navzven_X", "+Z"], d=300,
         opis="Podsestav ročaja (zvarjenec MLU124029200: 2x nosilec MTC324079400, cev inox MTC324079500) "
              "namesti na stranico pri x = -574 mm.",
         kamera="izometrija zadaj-levo", spoj=NEZNANO,
         opozorila_extra=["Ročaj je v STEP ločen podsestav 'zvarjenec' - prikazan je kot en kos."]),
]


def vol(shape):
    g = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, g)
    return g.Mass()


def bb(shape):
    b = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape, b, False, False)
    p, q = b.CornerMin(), b.CornerMax()
    return np.array([p.X(), p.Y(), p.Z()]), np.array([q.X(), q.Y(), q.Z()])


def bb_overlap(a, b, shift=np.zeros(3)):
    (a0, a1), (b0, b1) = a, b
    return bool(np.all(a0 + shift < b1 - ZRAK_MM) and np.all(b0 < a1 + shift - ZRAK_MM))


def common_vol(s1, s2):
    op = BRepAlgoAPI_Common(s1, s2)
    if not op.IsDone():
        return None
    return vol(op.Shape())


def offsets_for(direction, ids, d, bbs, center):
    out = {}
    for pid in ids:
        c = (bbs[pid][0] + bbs[pid][1]) / 2
        if direction in ("+Z", "-Z", "+X", "-X", "+Y", "-Y"):
            ax = "XYZ".index(direction[1])
            v = np.zeros(3)
            v[ax] = d if direction[0] == "+" else -d
        else:
            ax = "XYZ".index(direction[-1])
            v = np.zeros(3)
            v[ax] = d * (1 if c[ax] >= center[ax] else -1)
        out[pid] = v
    return out


def path_collisions(moving, placed, offs, shapes, bbs):
    """Vrne seznam trkov [(premikajoci, nepremicni, t, volumen)] po vzorcih poti od t=1 (zunaj) do t=0."""
    hits = []
    for pid in moving:
        v = offs[pid]
        n = max(2, int(np.ceil(np.linalg.norm(v) / KORAK_POTI_MM)))
        for k in range(1, n + 1):          # t = k/n ; t=0 (koncni polozaj) se preveri staticno
            t = k / n
            sh = v * t
            for q in placed:
                if not bb_overlap(bbs[pid], bbs[q], sh):
                    continue
                cv = common_vol(translated(shapes[pid], sh), shapes[q])
                if cv is None or cv > PRAG_MM3:
                    hits.append({"del": pid, "ovira": q, "t": round(t, 3), "odmik_mm": sh.round(1).tolist(),
                                 "presek_mm3": None if cv is None else round(cv, 2)})
    return hits


def main():
    t0 = time.time()
    deli, shapes = load_shapes()
    ids = [d["id"] for d in deli]
    bbs = {pid: bb(shapes[pid]) for pid in ids}
    allmin = np.min([b[0] for b in bbs.values()], axis=0)
    allmax = np.max([b[1] for b in bbs.values()], axis=0)
    center = (allmin + allmax) / 2
    ime = {d["id"]: d["ime"] for d in deli}

    # ---------------- staticno prekrivanje v koncnem polozaju
    static = []
    for a, b in itertools.combinations(ids, 2):
        if bb_overlap(bbs[a], bbs[b]):
            cv = common_vol(shapes[a], shapes[b])
            static.append({"a": a, "b": b, "presek_mm3": None if cv is None else round(cv, 3)})
    static_bad = [s for s in static if s["presek_mm3"] is None or s["presek_mm3"] > PRAG_MM3]
    print(f"staticno: {len(static)} parov s prekrivanjem bbox, {len(static_bad)} s presekom > {PRAG_MM3} mm3")
    for s in static_bad:
        print("  PREKRIVANJE", s)

    # vsak del natanko enkrat
    vsi = [p for k in KORAKI for p in k["deli"]]
    assert sorted(vsi) == sorted(ids), "koraki ne pokrijejo vseh delov natanko enkrat"

    placed = []
    koraki = []
    trki_log = []
    for i, k in enumerate(KORAKI, 1):
        chosen = None
        tried = []
        for smer in k["smeri"]:
            offs = offsets_for(smer, k["deli"], k["d"], bbs, center)
            hits = path_collisions(k["deli"], placed, offs, shapes, bbs)
            tried.append({"smer": smer, "trkov": len(hits), "primeri": hits[:5]})
            print(f"korak {i} {k['naslov']}: smer {smer} -> trkov {len(hits)}")
            if not hits:
                chosen = (smer, offs)
                break
        status_poti = "brez trkov (preverjeno)"
        if chosen is None:
            smer = min(tried, key=lambda x: x["trkov"])["smer"]
            chosen = (smer, offsets_for(smer, k["deli"], k["d"], bbs, center))
            status_poti = "TRK na poti - glej izvoz/kontrole_trkov.json"
        smer, offs = chosen
        trki_log.append({"st": i, "naslov": k["naslov"], "preizkusene_smeri": tried, "izbrana": smer, "status": status_poti})
        first = offs[k["deli"][0]]
        opozorila = [f"Način spajanja ({'varjenje, vijačenje ...'}): {k['spoj']}.",
                     "Orodje, momenti in kontrolne točke: " + NEZNANO + "."]
        opozorila += k.get("opozorila_extra", [])
        if status_poti != "brez trkov (preverjeno)":
            opozorila.append("Pot vstavljanja ima trk z že nameščenimi deli - zaporedje ali smer je treba popraviti.")
        koraki.append({
            "st": i,
            "naslov": k["naslov"],
            "opis": k["opis"] + " Deli: " + ", ".join(f"{p} ({ime[p]})" for p in k["deli"]) + ".",
            "deli": k["deli"],
            "gibanje": {
                "tip": "premik",
                "od_mm": first.round(1).tolist(),
                "do_mm": [0, 0, 0],
                "trajanje_s": 2.5,
                "koordinate": "odmik od končnega položaja, koordinate sestava STEP (mm, Z gor)",
                "smer": smer,
                "po_delih_od_mm": {p: offs[p].round(1).tolist() for p in k["deli"]},
                "kontrola_poti": status_poti,
            },
            "kamera": {"pogled": k["kamera"]},
            "opozorila": opozorila,
            "potrditev": NEZNANO,
            "vir_zaporedja": "predlog AI (fable) iz geometrije - ni potrjeno",
        })
        placed += k["deli"]

    (POSKUS / "koraki.json").write_text(json.dumps({"opomba": "Zaporedje je predlog AI, ni potrjeno s tehnologom. "
                                                    "Smeri vstavljanja so preverjene na trke z B-Rep geometrijo.",
                                                    "koraki": koraki}, ensure_ascii=False, indent=2), encoding="utf-8")
    (POSKUS / "izvoz" / "kontrole_trkov.json").write_text(json.dumps({
        "prag_mm3": PRAG_MM3, "korak_poti_mm": KORAK_POTI_MM,
        "staticno_pari_bbox": static, "staticno_prekrivanja": static_bad, "koraki": trki_log,
        "cas_s": round(time.time() - t0, 1)}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("cas", round(time.time() - t0, 1), "s")


if __name__ == "__main__":
    main()
