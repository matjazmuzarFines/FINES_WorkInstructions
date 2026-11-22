"""
Korak 3: montazni koraki z NACINOM SPAJANJA + kontrola trkov na poti (B-Rep).

- Zaporedje je PREDLOG (ni potrjen s tehnologom). Delitev na sklope sledi pripombi cloveka v ocene.json
  (cevi/okvir/plocevina se varijo, kolesa se vijacijo, plosca se polozi) in zaznanim spojem v spoji.json.
- Spoji in vijaki se korakom dodelijo SAMODEJNO: spoj pripada koraku, v katerem je namescen drugi od obeh delov.
  Skripta preveri, da je vsak spoj in vsak vijak dodeljen natanko enkrat.
- Pot vsakega dela je lomljenka odmikov od koncnega polozaja; preverjena je na trke z ze namescenimi deli.

Zagon: trening/okolje/fable/venv312/Scripts/python trening/modeli/vozicek-delovni-mali/fable/03/skripte/03_koraki.py
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

sys.path.insert(0, str(Path(__file__).parent))
from common_occ import POSKUS, load_shapes, translated  # noqa: E402

KORAK_POTI_MM = 5.0
ZRAK_MM = 0.05
NEZNANO = "ni znano / zahteva potrditev"
G_ROCAJ = [-260.0, 0.0, 0.0]      # mesto, kjer se zvari podsestav rocaja (ob vozicku), odmik od koncnega polozaja

# poti: "+Z" = del pride iz smeri +Z (od zgoraj); dict = smer po delih; list tock = lomljenka odmikov (zadnja = konec)
KORAKI = [
    dict(sklop="A. Zvarjenec okvirja", naslov="Spodnji okvir", navodilo="Štiri cevi sestavi v pravokotni okvir in jih zvari v vogalih.", deli=["P001", "P002", "P003", "P004"], d=260,
         poti=[{"P001": "-Y", "P002": "+Y", "P003": "+X", "P004": "-X"}, "+Z"], kamera="zgoraj spredaj-desno",
         opis="Štiri cevi 30x30x1,5 sestavi v pravokotni okvir in jih zvari v vogalih."),
    dict(sklop="A. Zvarjenec okvirja", naslov="Plošče koles", navodilo="Plošče koles privari v vogale na spodnjo stran okvirja.", deli=["P013", "P014", "P015", "P016"], d=160,
         poti=["-Z"], kamera="od spodaj",
         opis="Plošče koles 108x88x3 privari v vogale na spodnjo stran okvirja."),
    dict(sklop="A. Zvarjenec okvirja", naslov="Navpične noge", navodilo="Noge postavi v vogale okvirja in jih privari.", deli=["P005", "P006", "P007", "P008"], d=420,
         poti=["+Z"], kamera="spredaj-desno",
         opis="Štiri noge (cev 30x30x1,5 l=730, s šestkotnimi luknjami) postavi v vogale okvirja in privari."),
    dict(sklop="A. Zvarjenec okvirja", naslov="Zgornje povezave", navodilo="Zgornje povezave položi na vrh nog in jih privari.", deli=["P009", "P010", "P011", "P012"], d=300,
         poti=["+Z"], kamera="zgoraj spredaj-desno",
         opis="Zgornje povezave (profil 3 mm) položi na vrh nog, privari na noge in med seboj v vogalih."),
    dict(sklop="B. Končna montaža", naslov="Zakovične matice M6 v noge", navodilo="V označene šestkotne luknje nog vstavi zakovične matice M6.", deli=[], zakovicne=True, kamera="spredaj-desno",
         opis="V šestkotne luknje nog, ki jih uporabljajo vmesni povezavi in ročaj, vstavi šestkotne zakovične matice M6."),
    dict(sklop="B. Končna montaža", naslov="Kolesa", navodilo="Kolesa nastavi na plošče in vsako privijači s 4 vijaki M8.", deli=["P022", "P023", "P024", "P025"], d=220,
         poti=["-Z"], kamera="od spodaj",
         opis="Kolesa fi80 z zavoro nastavi na plošče koles in vsako privijači s 4 vijaki."),
    dict(sklop="B. Končna montaža", naslov="Spodnja polica", navodilo="Polico vstavi na spodnji okvir in jo privijači od spodaj skozi cevi.", deli=["P018"], d=700,
         poti=["-Y", "+Z"], kamera="zgoraj spredaj-desno",
         opis="Polico 930x482x18 vstavi med noge na spodnji okvir in jo od spodaj privijači skozi cevi okvirja."),
    dict(sklop="B. Končna montaža", naslov="Vmesna povezava – zadnja", navodilo="Zadnjo vmesno povezavo privijači na notranjo stran nog.", deli=["P019"], d=260,
         poti=["-Z", "+Z"], kamera="spredaj-desno",
         opis="Vmesno povezavo nastavi na notranjo stran zadnjih nog (utor 6,5x12 na šestkotno luknjo) in privijači."),
    dict(sklop="B. Končna montaža", naslov="Vmesna polica", navodilo="Polico vstavi s sprednje strani in jo privijači od spodaj.", deli=["P021"], d=700,
         poti=["+Z", "-Y", [[0, -700, 20], [0, 0, 20], [0, 0, 0]]], kamera="zgoraj spredaj-desno",
         opis="Polico 930x482x18 vstavi s sprednje strani nad rob povezave, spusti na zadnjo povezavo in privijači od spodaj."),
    dict(sklop="B. Končna montaža", naslov="Vmesna povezava – sprednja", navodilo="Sprednjo povezavo dvigni pod polico, privijači na nogi in v polico.", deli=["P020"], d=260,
         poti=["-Z", "+Z"], kamera="spredaj-desno nizko",
         opis="Sprednjo vmesno povezavo dvigni od spodaj pod polico, privijači na nogi in polico privijači od spodaj."),
    dict(sklop="B. Končna montaža", naslov="Zgornja polica", navodilo="Polico položi na zgornje povezave in jo privijači od spodaj.", deli=["P017"], d=320,
         poti=["+Z"], kamera="zgoraj spredaj-desno",
         opis="Polico 993x493x18 položi na zgornje povezave in jo privijači od spodaj."),
    dict(sklop="C. Podsestav ročaja", naslov="Ročaj – zvarjenec", navodilo="Cev ročaja in oba nosilca zvari v ročaj.", deli=["P027", "P026", "P028"], d=160, konec=G_ROCAJ,
         poti=[{"P027": "+Z", "P026": "+Y", "P028": "-Y"}], kamera="zadaj-levo",
         opis="Cev inox fi30 l=428 in dva nosilca zvari v podsestav MLU124029200 (v STEP označen kot zvarjenec)."),
    dict(sklop="B. Končna montaža", naslov="Montaža ročaja", navodilo="Ročaj nastavi na notranjo stran nog in ga privijači.", deli=["P027", "P026", "P028"], zacetek=G_ROCAJ,
         poti=["skupina"], kamera="zadaj-levo",
         opis="Zvarjeni ročaj nastavi na notranjo stran nog in privijači."),
]

OPIS_NACINA = {
    "varjenje": "VARJENJE",
    "vijacenje": "VIJAČENJE",
    "polaganje + vijacenje": "POLAGANJE + VIJAČENJE",
    "polaganje": "POLAGANJE",
    "zakovicenje": "VSTAVLJANJE ZAKOVIČNIH MATIC",
}


def vol(shape):
    g = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, g)
    return g.Mass()


def common_vol(s1, s2):
    op = BRepAlgoAPI_Common(s1, s2)
    return vol(op.Shape()) if op.IsDone() else None


def bb_overlap(a, b, sa, sb):
    return bool(np.all(a[0] + sa < b[1] + sb - ZRAK_MM) and np.all(b[0] + sb < a[1] + sa - ZRAK_MM))


def dir_vec(s, d):
    v = np.zeros(3)
    v["XYZ".index(s[1])] = d if s[0] == "+" else -d
    return v


def sample_path(pts):
    """Lomljenka odmikov -> gosti vzorci (brez zadnje tocke = koncni polozaj)."""
    out = []
    for a, b in zip(pts[:-1], pts[1:]):
        n = max(1, int(np.ceil(np.linalg.norm(b - a) / KORAK_POTI_MM)))
        out += [a + (b - a) * (i / n) for i in range(n)]
    return out


def main():
    t0 = time.time()
    deli, shapes = load_shapes()
    D = {d["id"]: d for d in deli}
    ids = [d["id"] for d in deli]
    bbs = {p: (np.array(D[p]["bbox_mm"]["min"]), np.array(D[p]["bbox_mm"]["max"])) for p in ids}
    spoji_doc = json.loads((POSKUS / "spoji.json").read_text(encoding="utf-8"))
    spoji = spoji_doc["spoji"]
    vij = {v["id"]: v for v in spoji_doc["vijacni_material"]}
    kos = {k["id"]: (v, k) for v in vij.values() for k in v["kosi"]}

    # staticno prekrivanje (prag trka na par = 1 mm3 + 1,3 x staticni presek v CAD)
    static = {}
    zero = np.zeros(3)
    for a, b in itertools.combinations(ids, 2):
        if bb_overlap(bbs[a], bbs[b], zero, zero):
            cv = common_vol(shapes[a], shapes[b])
            if cv and cv > 0.01:
                static[(a, b)] = static[(b, a)] = cv
    static_bad = sorted({tuple(sorted(k)): round(v, 3) for k, v in static.items() if v > 1.0}.items())
    print("staticna prekrivanja > 1 mm3:", static_bad)

    def collisions(moving_paths, placed_off):
        hits = []
        for pid, pts in moving_paths.items():
            for off in sample_path(pts):
                for q, qo in placed_off.items():
                    if q in moving_paths or not bb_overlap(bbs[pid], bbs[q], off, qo):
                        continue
                    cv = common_vol(translated(shapes[pid], off), translated(shapes[q], qo) if np.any(qo) else shapes[q])
                    prag = 1.0 + 1.3 * static.get((pid, q), 0.0)
                    if cv is None or cv > prag:
                        hits.append({"del": pid, "ovira": q, "odmik_mm": np.round(off, 1).tolist(),
                                     "presek_mm3": None if cv is None else round(cv, 2)})
        return hits

    placed_off = {}            # id -> trenutni odmik (0 = koncni polozaj)
    done_spoji, done_kosi = set(), set()
    koraki, log = [], []
    for i, k in enumerate(KORAKI, 1):
        start = np.array(k.get("zacetek", [0, 0, 0]), float)
        end = np.array(k.get("konec", [0, 0, 0]), float)
        tried, chosen = [], None
        cands = k.get("poti", [])
        for cand in cands:
            if cand == "skupina":
                paths = {p: [start, end] for p in k["deli"]}
                name = "skupina"
            elif isinstance(cand, dict):
                paths = {p: [end + dir_vec(cand[p], k["d"]), end] for p in k["deli"]}
                name = ", ".join(f"{p}:{cand[p]}" for p in k["deli"])
            elif isinstance(cand, list):
                paths = {p: [end + np.array(q, float) for q in cand] for p in k["deli"]}
                name = "lomljenka " + " -> ".join(str(q) for q in cand)
            else:
                paths = {p: [end + dir_vec(cand, k["d"]), end] for p in k["deli"]}
                name = cand
            others = {q: o for q, o in placed_off.items() if q not in k["deli"]}
            hits = collisions(paths, others)
            tried.append({"pot": name, "trkov": len(hits), "primeri": hits[:4]})
            print(f"korak {i} {k['naslov']}: pot {name} -> trkov {len(hits)}")
            if not hits:
                chosen = (name, paths)
                break
        status = "brez trkov (preverjeno)"
        if cands and chosen is None:
            status = "TRK na poti - zahteva popravek"
            chosen = (name, paths)
        if not cands:
            chosen, status = ("-", {}), "ni premika delov iz STEP"
        name, paths = chosen
        for p in k["deli"]:
            placed_off[p] = end.copy()

        # --- spoji tega koraka: oba dela namescena in v medsebojnem koncnem polozaju
        sp_now, kosi_now = [], []
        if k.get("zakovicne"):
            kosi_now = [kid for kid, (v, _) in kos.items() if v["vrsta"].startswith("zakovicna")]
            nacin = "zakovicenje"
        else:
            for s in spoji:
                a, b = s["deli"]
                if s["id"] in done_spoji or a not in placed_off or b not in placed_off:
                    continue
                if not np.allclose(placed_off[a], placed_off[b]):
                    continue
                sp_now.append(s)
                done_spoji.add(s["id"])
            pari = {tuple(sorted(s["deli"])) for s in sp_now}
            kosi_now = [kid for kid, (v, c) in kos.items()
                        if not v["vrsta"].startswith("zakovicna") and tuple(sorted((c["skozi"], c["v"]))) in pari]
            tipi = {s["tip"] for s in sp_now}
            nacin = ("varjenje" if tipi == {"varjenje"} else
                     "polaganje + vijacenje" if "polaganje + vijacenje" in tipi else
                     "vijacenje" if "vijacenje" in tipi else
                     "polaganje" if tipi == {"polaganje"} else NEZNANO)
        assert not (set(kosi_now) & done_kosi)
        done_kosi |= set(kosi_now)
        grupe = {}
        for kid in kosi_now:
            grupe.setdefault(kos[kid][0]["id"], []).append(kid)
        dolz_zvara = round(sum(s["dolzina_oboda_mm"] for s in sp_now if s["tip"] == "varjenje"))
        if nacin == "varjenje":
            sp_opis = (f"Varjenje: {len(sp_now)} stikov jeklo-jeklo brez lukenj za vijake, skupni obod stikov {dolz_zvara} mm. "
                       f"Vrsta, debelina in dolžina zvarov: {NEZNANO}.")
        elif nacin == "zakovicenje":
            sp_opis = (f"{len(kosi_now)}x šestkotna zakovična matica M6 v šestkotne luknje 9,1 mm (predpostavka po meri izreza; "
                       f"matic ni v STEP). Orodje: {NEZNANO}.")
        else:
            deli_v = "; ".join(f"{len(v)}x {vij[g]['ime'].replace(' (predpostavka)', '')}" for g, v in grupe.items())
            sp_opis = f"{OPIS_NACINA.get(nacin, nacin).capitalize()}: {deli_v}. Vijačnega materiala ni v STEP - vrsta in mera sta predpostavka iz lukenj. Moment: {NEZNANO}."
        gib = {"tip": "premik" if paths else "brez", "od_mm": [0, 0, 0], "do_mm": np.round(end, 1).tolist(), "trajanje_s": 2.0,
               "koordinate": "odmik od končnega položaja v sestavu STEP (mm, Z gor)", "pot": name,
               "pot_po_delih_mm": {p: [np.round(q, 1).tolist() for q in pts] for p, pts in paths.items()},
               "kontrola_poti": status}
        if paths:
            gib["od_mm"] = gib["pot_po_delih_mm"][k["deli"][0]][0]
        koraki.append({
            "st": i, "sklop": k["sklop"], "naslov": k["naslov"], "opis": k["opis"],
            "navodilo": k["navodilo"],
            "deli": k["deli"] + sorted(grupe),
            "deli_step": k["deli"],
            "gibanje": gib,
            "spajanje": {"nacin": nacin, "napis": OPIS_NACINA.get(nacin, nacin.upper()), "opis": sp_opis,
                         "spoji": [s["id"] for s in sp_now],
                         "vijacni_material": [{"id": g, "ime": vij[g]["ime"], "kolicina": len(v), "kosi": v} for g, v in grupe.items()],
                         "vir": "geometrija (luknje, stiki) + pripomba človeka v ocene.json", "potrditev": NEZNANO},
            "kamera": {"pogled": k["kamera"], **({"detajl_smer_rocno": k["detajl_smer"]} if "detajl_smer" in k else {})},
            "opozorila": ["Zaporedje in način spajanja sta predlog - zahteva potrditev tehnologa.",
                          "Orodje, momenti, zaščitna oprema, kontrolne točke: " + NEZNANO + "."],
            "potrditev": NEZNANO,
        })
        log.append({"st": i, "naslov": k["naslov"], "preizkusene_poti": tried, "status": status})

    # --- kontrole popolnosti
    assert sorted(placed_off) == sorted(ids), "vsi deli iz STEP morajo biti namesceni"
    assert all(not np.any(o) for o in placed_off.values()), "vsi deli morajo koncati v koncnem polozaju"
    nedodeljeni_spoji = [s["id"] for s in spoji if s["id"] not in done_spoji]
    nedodeljeni_kosi = [kid for kid in kos if kid not in done_kosi]
    print("nedodeljeni spoji:", nedodeljeni_spoji, "| nedodeljeni vijaki:", nedodeljeni_kosi)
    assert not nedodeljeni_spoji and not nedodeljeni_kosi

    (POSKUS / "koraki.json").write_text(json.dumps({
        "opomba": "Zaporedje in način spajanja sta predlog AI iz geometrije in pripomb človeka; ni potrjeno s tehnologom.",
        "koraki": koraki}, ensure_ascii=False, indent=2), encoding="utf-8")
    (POSKUS / "izvoz" / "kontrole_trkov.json").write_text(json.dumps({
        "korak_poti_mm": KORAK_POTI_MM, "prag": "1 mm3 + 1,3 x staticni presek para v CAD",
        "staticna_prekrivanja_mm3": [{"par": list(k_), "presek_mm3": v} for k_, v in static_bad],
        "koraki": log, "vseh_spojev": len(spoji), "dodeljenih_spojev": len(done_spoji),
        "vseh_vijakov": len(kos), "dodeljenih_vijakov": len(done_kosi), "cas_s": round(time.time() - t0, 1)},
        ensure_ascii=False, indent=2), encoding="utf-8")
    for k in koraki:
        print(k["st"], k["naslov"], "|", k["spajanje"]["napis"], "|", len(k["spajanje"]["spoji"]), "spojev |",
              [(v["id"], v["kolicina"]) for v in k["spajanje"]["vijacni_material"]])
    print("cas", round(time.time() - t0, 1), "s")


if __name__ == "__main__":
    main()
