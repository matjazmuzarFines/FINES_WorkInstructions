"""
Korak 2: zaznava NACINA SPAJANJA iz B-Rep geometrije (luknje + stiki) in generiranje vijacnega materiala.

Ideja (odgovor na oceno poskusa 01: "pri vsaki animaciji mora biti zraven nacin, kako se to zmontira"):
  1. LUKNJE: vsaka luknja v plocevini/cevi je notranja zanka (inner wire) na ravni ploskvi. Preberem
     obliko (krog / sestkotnik / utor), mero, sredisce in os. Dve ustji iste stene zdruzim v "luknjo v steni".
  2. PARI: luknja dela A, ki je soosna z luknjo dela B tik ob njej -> vijacni spoj skozi obe.
     Sestkotna luknja 9,1 mm -> sestkotna zakovicna matica M6 (predpostavka po standardni meri izreza).
     Luknja dela A, za katero je poln material dela B (brez luknje) -> vijak v B (les -> lesni vijak).
  3. STIKI: ravne ploskve dveh delov, ki lezijo v isti ravnini z nasprotnima normalama in se prekrivajo
     -> stikna ploskev; njen zunanji obod je predlagana linija zvara. Stik jeklo-jeklo BREZ vijakov -> varjenje
     (skladno s pripombo cloveka v ocene.json: "cevi, okvirji in ostala plocevina se vari skupaj").
  4. VIJACNI MATERIAL, ki ga v STEP ni, se generira parametricno (poenostavljena geometrija) in je povsod
     oznacen kot PREDPOSTAVKA.

Zagon: trening/okolje/fable/venv312/Scripts/python trening/modeli/vozicek-delovni-mali/fable/03/skripte/02_spoji.py
Izhodi: spoji.json, izvoz/vijaki.npz, dopolnjen deli.json (vijacni material V..), izvoz/vozicek.glb (z vijaki)
"""
import collections
import itertools
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import trimesh
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Section
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.BRepGProp import BRepGProp
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCone, BRepPrimAPI_MakeCylinder, BRepPrimAPI_MakePrism
from OCP.BRepTools import BRepTools, BRepTools_WireExplorer
from OCP.BRep import BRep_Tool
from OCP.Bnd import Bnd_Box
from OCP.GeomAbs import GeomAbs_Line, GeomAbs_Plane
from OCP.GProp import GProp_GProps
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_IN, TopAbs_REVERSED, TopAbs_SOLID, TopAbs_WIRE
from OCP.TopExp import TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt, gp_Vec

sys.path.insert(0, str(Path(__file__).parent))
from common_occ import POSKUS, load_shapes  # noqa: E402

IZVOZ = POSKUS / "izvoz"
OSNI_ODMIK_MM = 0.8       # dovoljen odmik osi soosnih lukenj
BLIZINA_MM = 2.0          # reza med deloma, ki se se steje za sosednja (rocaj-noga v CAD: 0,6 mm in 1,4 mm)
MAX_LUKNJA_MM = 14.0     # vecje notranje zanke niso luknje za vijake (npr. odprtina profila)
NEZNANO = "ni znano / zahteva potrditev"

# Standardne mere (vir: splosno strojnisko znanje; PREDPOSTAVKA, dokler ni kosovnice)
HEX_ZAKOVICNA = {6.0: "M4", 7.0: "M5", 9.0: "M6", 11.0: "M8"}        # izrez za sestkotno zakovicno matico
PREHODNA = [(3.4, "M3"), (4.5, "M4"), (5.5, "M5"), (6.6, "M6"), (9.0, "M8"), (11.0, "M10")]  # ISO 273 srednja


def vec(p):
    return np.array([p.X(), p.Y(), p.Z()])


def bbox(shape, optimal=True):
    b = Bnd_Box()
    if optimal:
        BRepBndLib.AddOptimal_s(shape, b, False, False)
    else:
        BRepBndLib.Add_s(shape, b)
    return vec(b.CornerMin()), vec(b.CornerMax())


def solids_of(shape):
    out = []
    e = TopExp_Explorer(shape, TopAbs_SOLID)
    while e.More():
        out.append(e.Current())
        e.Next()
    return out


def inside(solids, p, tol=1e-3):
    for s in solids:
        if BRepClass3d_SolidClassifier(s, gp_Pnt(*p), tol).State() == TopAbs_IN:
            return True
    return False


def wire_polyline(wire, face=None, n_curve=16):
    pts = []
    ex = BRepTools_WireExplorer(wire) if face is None else BRepTools_WireExplorer(wire, face)
    while ex.More():
        edge = ex.Current()
        c = BRepAdaptor_Curve(edge)
        n = 2 if c.GetType() == GeomAbs_Line else n_curve
        ts = np.linspace(c.FirstParameter(), c.LastParameter(), n)
        seg = [vec(c.Value(t)) for t in ts]
        if edge.Orientation() == TopAbs_REVERSED:
            seg = seg[::-1]
        pts += seg if not pts else seg[1:]
        ex.Next()
    return np.array(pts)


def edge_polyline(edge, n_curve=16):
    c = BRepAdaptor_Curve(edge)
    n = 2 if c.GetType() == GeomAbs_Line else n_curve
    return np.array([vec(c.Value(t)) for t in np.linspace(c.FirstParameter(), c.LastParameter(), n)])


def poly_len(p):
    return float(np.linalg.norm(np.diff(p, axis=0), axis=1).sum()) if len(p) > 1 else 0.0


# ------------------------------------------------------------------ ravne ploskve + ustja lukenj
def planar_faces(shape):
    out = []
    e = TopExp_Explorer(shape, TopAbs_FACE)
    while e.More():
        f = TopoDS.Face(e.Current())
        s = BRepAdaptor_Surface(f)
        if s.GetType() == GeomAbs_Plane:
            pl = s.Plane()
            n = vec(pl.Axis().Direction())
            if f.Orientation() == TopAbs_REVERSED:
                n = -n
            p0 = vec(pl.Location())
            out.append({"face": f, "n": n, "d": float(n @ p0), "bb": bbox(f)})
        e.Next()
    return out


def hole_mouths(pfaces):
    mouths = []
    for pf in pfaces:
        f = pf["face"]
        ow = BRepTools.OuterWire_s(f)
        w = TopExp_Explorer(f, TopAbs_WIRE)
        while w.More():
            wi = w.Current()
            if not wi.IsSame(ow):
                mn, mx = bbox(wi)
                ext = mx - mn
                inplane = np.sort(ext)[1:]          # dve meri v ravnini
                if inplane[1] <= MAX_LUKNJA_MM:
                    kinds = collections.Counter()
                    ee = TopExp_Explorer(wi, TopAbs_EDGE)
                    while ee.More():
                        kinds[str(BRepAdaptor_Curve(TopoDS.Edge(ee.Current())).GetType()).split("_")[-1]] += 1
                        ee.Next()
                    if set(kinds) == {"Circle"} and abs(inplane[0] - inplane[1]) < 0.05:
                        oblika = "krog"
                    elif set(kinds) == {"Line"} and kinds["Line"] == 6:
                        oblika = "sestkotnik"
                    elif "Line" in kinds and len(kinds) > 1:
                        oblika = "utor"
                    else:
                        oblika = "drugo"
                    long_axis = int(np.argmax(ext))
                    mouths.append({"c": (mn + mx) / 2, "n": pf["n"], "mera": [round(float(inplane[0]), 2), round(float(inplane[1]), 2)],
                                   "oblika": oblika, "os_utora": long_axis})
            w.Next()
    return mouths


def wall_holes(mouths):
    """Zdruzi dve ustji iste stene (nasprotni normali, soosni, razmik <= 6,5 mm)."""
    used, out = set(), []
    for i, a in enumerate(mouths):
        if i in used:
            continue
        best = None
        for j, b in enumerate(mouths):
            if j <= i or j in used or a["oblika"] != b["oblika"] or a["mera"] != b["mera"]:
                continue
            if a["n"] @ b["n"] > -0.999:
                continue
            dv = b["c"] - a["c"]
            along = dv @ a["n"]
            perp = np.linalg.norm(dv - along * a["n"])
            if perp < 0.05 and -6.5 <= along < -0.3 and (best is None or -along < best[1]):
                best = (j, -along)
        if best:
            j, t = best
            used |= {i, j}
            b = mouths[j]
            out.append({"oblika": a["oblika"], "mera": a["mera"], "debelina": round(float(t), 2), "os_utora": a["os_utora"],
                        "ustja": [(a["c"], a["n"]), (b["c"], b["n"])], "c": (a["c"] + b["c"]) / 2})
    return out


def premer(h):
    return h["mera"][0]          # krog: premer; utor: sirina; sestkotnik: zev (AF)


def metric_from_clearance(d):
    cands = [(abs(d - c), m) for c, m in PREHODNA if -0.35 <= d - c <= 0.8]
    return min(cands)[1] if cands else None


# ------------------------------------------------------------------ geometrija vijakov (lokalno: sedez glave v 0, steblo +Z)
def _hex_prism(af, h, z0):
    r = af / math.sqrt(3)
    poly = BRepBuilderAPI_MakePolygon()
    for k in range(6):
        a = math.radians(60 * k)
        poly.Add(gp_Pnt(r * math.cos(a), r * math.sin(a), z0))
    poly.Close()
    face = BRepBuilderAPI_MakeFace(poly.Wire()).Face()
    return BRepPrimAPI_MakePrism(face, gp_Vec(0, 0, h)).Shape()


def _cyl(r, h, z0):
    return BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(0, 0, z0), gp_Dir(0, 0, 1)), r, h).Shape()


def _mesh(shapes_):
    V, F, off = [], [], 0
    for sh in shapes_:
        BRepMesh_IncrementalMesh(sh, 0.02, False, 0.15, True)
        e = TopExp_Explorer(sh, TopAbs_FACE)
        while e.More():
            face = TopoDS.Face(e.Current())
            loc = TopLoc_Location()
            tri = BRep_Tool.Triangulation_s(face, loc)
            if tri is not None:
                tr = loc.Transformation()
                n = tri.NbNodes()
                pts = np.array([vec(tri.Node(i).Transformed(tr)) for i in range(1, n + 1)])
                rev = face.Orientation() == TopAbs_REVERSED
                tris = []
                for i in range(1, tri.NbTriangles() + 1):
                    a, b, c = tri.Triangle(i).Get()
                    tris.append((a, c, b) if rev else (a, b, c))
                V.append(pts)
                F.append(np.array(tris) - 1 + off)
                off += n
            e.Next()
    return np.vstack(V).astype(np.float32), np.vstack(F).astype(np.int32)


def make_fastener(kind):
    """Poenostavljena geometrija (brez navoja). Vrne (V, F, opis mer)."""
    if kind == "vijak_M8":      # sestroba glava ISO 4017 M8: zev 13, visina 5,3; + podlozka 16x1,6
        parts = [_cyl(8.0, 1.6, -1.6), _hex_prism(13.0, 5.3, -6.9), _cyl(4.0, 14.0, 0.0)]
        return (*_mesh(parts), {"d": 8, "L": 14, "glava": "sestroba, zev 13", "podlozka": "16x1,6"})
    if kind == "vijak_M6":      # sestroba glava M6: zev 10, visina 4; + podlozka 12x1,6
        parts = [_cyl(6.0, 1.6, -1.6), _hex_prism(10.0, 4.0, -5.6), _cyl(3.0, 14.0, 0.0)]
        return (*_mesh(parts), {"d": 6, "L": 14, "glava": "sestroba, zev 10", "podlozka": "12x1,6"})
    if kind == "lesni_vijak_4":  # lecasta glava 8 mm, steblo 4x14 + konica
        parts = [_cyl(4.0, 2.4, -2.4), _cyl(2.0, 11.0, 0.0),
                 BRepPrimAPI_MakeCone(gp_Ax2(gp_Pnt(0, 0, 11.0), gp_Dir(0, 0, 1)), 2.0, 0.2, 4.0).Shape()]
        return (*_mesh(parts), {"d": 4, "L": 15, "glava": "lecasta 8 mm"})
    if kind == "zakovicna_matica_M6":   # prirobnica 13x0,5 (tanka), sestkotno telo zev 9 x 13
        parts = [_cyl(6.5, 0.5, -0.5), _hex_prism(8.9, 13.0, 0.0)]
        return (*_mesh(parts), {"d": 6, "L": 13, "prirobnica": "13x0,5", "telo": "sestkotno, zev 9"})
    raise ValueError(kind)


def frame_from_dir(d):
    """Matrika 4x4: lokalni +Z -> smer d."""
    d = np.asarray(d, float)
    d /= np.linalg.norm(d)
    a = np.array([1.0, 0, 0]) if abs(d[0]) < 0.9 else np.array([0, 1.0, 0])
    x = np.cross(a, d)
    x /= np.linalg.norm(x)
    y = np.cross(d, x)
    M = np.eye(4)
    M[:3, 0], M[:3, 1], M[:3, 2] = x, y, d
    return M


# ------------------------------------------------------------------ glavni del
def main():
    t0 = time.time()
    deli_doc = json.loads((POSKUS / "deli.json").read_text(encoding="utf-8"))
    deli = [d for d in deli_doc["deli"] if not d["id"].startswith("V")]
    _, shapes = load_shapes()
    D = {d["id"]: d for d in deli}
    ids = [d["id"] for d in deli]
    sol = {p: solids_of(shapes[p]) for p in ids}
    bbs = {p: (np.array(D[p]["bbox_mm"]["min"]), np.array(D[p]["bbox_mm"]["max"])) for p in ids}
    pf = {p: planar_faces(shapes[p]) for p in ids}
    holes = {p: wall_holes(hole_mouths(pf[p])) for p in ids}

    def razred(p):
        return D[p]["material_razred_step"] or D[p]["material_razred_geometrija"]

    def je_les(p):
        return razred(p).startswith("les")

    def kupljen(p):
        return D[p]["stevilo_teles"] > 1

    def near(a, b, tol=BLIZINA_MM):
        return bool(np.all(bbs[a][0] - tol < bbs[b][1]) and np.all(bbs[b][0] - tol < bbs[a][1]))

    # ---------------- 1) vijacni spoji iz lukenj
    fasteners = []          # posamezni vijaki
    used_holes = set()      # (part, index)
    pair_fast = collections.defaultdict(list)   # (A,B) -> indeksi vijakov

    def add(kind, pos, direction, a, b, dokaz, velikost, access_mm=0.0):
        fasteners.append({"vrsta": kind, "pos": np.asarray(pos, float), "dir": np.asarray(direction, float), "a": a, "b": b,
                          "dokaz": dokaz, "velikost": velikost, "dostop_mm": access_mm})
        pair_fast[tuple(sorted((a, b)))].append(len(fasteners) - 1)

    for a in ids:
        for ia, h in enumerate(holes[a]):
            if h["oblika"] == "sestkotnik":
                continue                    # sestkotna luknja je "sprejemna" stran (matica), obravnavana od para
            for k in (0, 1):
                e_k, n_k = h["ustja"][k]
                e_o, _ = h["ustja"][1 - k]
                done = False
                # (i) soosna luknja drugega dela tik za ustjem
                for b in ids:
                    if b == a or not near(a, b):
                        continue
                    for ib, g in enumerate(holes[b]):
                        for (ge, gn) in g["ustja"]:
                            if gn @ n_k > -0.999:
                                continue
                            dv = ge - e_k
                            along = dv @ n_k
                            perp = np.linalg.norm(dv - along * n_k)
                            if perp < OSNI_ODMIK_MM and -0.05 <= along <= 3.0:
                                if g["oblika"] == "sestkotnik":
                                    m = HEX_ZAKOVICNA.get(round(premer(g)), None)
                                    mc = metric_from_clearance(premer(h))
                                    dok = (f"{a}: {h['oblika']} {h['mera'][0]}x{h['mera'][1]} mm soosno s sestkotno luknjo zev "
                                           f"{premer(g)} mm v {b} (reza {along:.1f} mm, odmik osi {perp:.2f} mm). Sestkotni izrez {premer(g):.1f} -> zakovicna matica {m}; "
                                           f"prehodna luknja {premer(h)} -> {mc}.")
                                    add("zakovicna_matica_" + (m or "M?"), ge, n_k, b, a, dok, m)
                                    add("vijak_" + (m or mc or "M?"), e_o, n_k, a, b, dok, m or mc)
                                else:
                                    mc = metric_from_clearance(min(premer(h), premer(g)))
                                    dok = f"{a} in {b}: soosni luknji {premer(h)} / {premer(g)} mm -> vijak {mc} z matico ({NEZNANO})."
                                    add("vijak_" + (mc or "M?"), e_o, n_k, a, b, dok, mc)
                                used_holes |= {(a, ia), (b, ib)}
                                done = True
                                break
                        if done:
                            break
                    if done:
                        break
                if done:
                    break
                # (ii) poln material drugega dela za ustjem
                probe = e_k + n_k * 1.2
                for b in ids:
                    if b == a or not near(a, b):
                        continue
                    if not (np.all(probe > bbs[b][0] - 0.01) and np.all(probe < bbs[b][1] + 0.01)):
                        continue
                    if inside(sol[b], probe):
                        # dostopna luknja v istem delu (vecja, soosna, na nasprotni steni)?
                        acc = 0.0
                        for ig, g in enumerate(holes[a]):
                            if g is h or premer(g) <= premer(h):
                                continue
                            dv = g["c"] - h["c"]
                            along = dv @ n_k
                            if np.linalg.norm(dv - along * n_k) < 0.3 and -45 < along < 0:
                                acc = -along
                                used_holes.add((a, ig))
                        if je_les(b):
                            dok = (f"{a}: luknja {premer(h)} mm, za njo poln les {b} brez luknje -> lesni vijak ~4 mm od strani {a}."
                                   + (f" Soosna dostopna luknja v nasprotni steni ({acc:.0f} mm) -> vijak se vstavi skozi profil." if acc else ""))
                            add("lesni_vijak_4", e_o, n_k, a, b, dok, "4 x 16 (dolzina " + NEZNANO + ")", acc)
                        elif kupljen(a) or kupljen(b):
                            mc = metric_from_clearance(premer(h))
                            dok = (f"{a} (kupljen del): pritrdilni {h['oblika']} {h['mera'][0]}x{h['mera'][1]} mm, za njim plosca {b} BREZ modelirane luknje. "
                                   f"Pravilo cloveka (ocene.json): kolesa se vedno vijacijo -> vijak {mc}; navoj / matica v {b}: {NEZNANO}.")
                            add("vijak_" + (mc or "M?"), e_o, n_k, a, b, dok, mc)
                        else:
                            continue
                        used_holes.add((a, ia))
                        done = True
                        break
                if done:
                    break

    # ---------------- 2) stiki (ravne ploskve) + zvari
    spoji = []
    static_overlap = {}
    for a, b in itertools.combinations(ids, 2):
        if not near(a, b, 0.3):
            continue
        key = (a, b)
        area = 0.0
        seams = []
        for fa in pf[a]:
            for fb in pf[b]:
                if fa["n"] @ fb["n"] > -0.999 or abs(fa["d"] + fb["d"]) > 0.05:
                    continue
                if not (np.all(fa["bb"][0] < fb["bb"][1] + 0.01) and np.all(fb["bb"][0] < fa["bb"][1] + 0.01)):
                    continue
                op = BRepAlgoAPI_Common(fa["face"], fb["face"])
                if not op.IsDone():
                    continue
                e = TopExp_Explorer(op.Shape(), TopAbs_FACE)
                while e.More():
                    cf = TopoDS.Face(e.Current())
                    g = GProp_GProps()
                    BRepGProp.SurfaceProperties_s(cf, g)
                    if g.Mass() > 0.5:
                        area += g.Mass()
                        seams.append(wire_polyline(BRepTools.OuterWire_s(cf), cf))
                    e.Next()
        nacin_stika = "ravna stikna ploskev"
        if area < 0.5:
            # rezervna pot: presek ploskev (npr. cev v polkroznem izrezu nosilca)
            sec = BRepAlgoAPI_Section(shapes[a], shapes[b])
            if sec.IsDone():
                e = TopExp_Explorer(sec.Shape(), TopAbs_EDGE)
                while e.More():
                    pl = edge_polyline(TopoDS.Edge(e.Current()))
                    if poly_len(pl) > 1.0:
                        seams.append(pl)
                    e.Next()
            nacin_stika = "presek ploskev (ni ravne stikne ploskve)"
            if not seams:
                continue
        vij = pair_fast.get(tuple(sorted(key)), [])
        les = je_les(a) or je_les(b)
        if vij:
            tip = "polaganje + vijacenje" if les else "vijacenje"
        elif les:
            tip = "polaganje"
        elif kupljen(a) or kupljen(b):
            tip = NEZNANO
        else:
            tip = "varjenje"
        spoji.append({"deli": [a, b], "tip": tip, "stik": nacin_stika, "stikna_povrsina_mm2": round(area, 1),
                      "obod_mm": [np.round(s, 2).tolist() for s in seams],
                      "dolzina_oboda_mm": round(sum(poly_len(s) for s in seams), 1), "vijaki_idx": vij})
    # vijacni pari brez zaznanega stika (reza 0,5 mm zaradi prirobnice matice)
    have = {tuple(sorted(s["deli"])) for s in spoji}
    for key, vij in pair_fast.items():
        if key not in have:
            spoji.append({"deli": list(key), "tip": "vijacenje", "stik": "brez dotika (reza - prirobnica zakovicne matice)",
                          "stikna_povrsina_mm2": 0.0, "obod_mm": [], "dolzina_oboda_mm": 0.0, "vijaki_idx": vij})
    spoji.sort(key=lambda s: s["deli"])
    for i, s in enumerate(spoji, 1):
        s["id"] = f"S{i:02d}"

    # ---------------- 3) zdruzi vijake v pozicije kosovnice (V01..)
    groups = collections.OrderedDict()
    for i, f in enumerate(fasteners):
        sif = {D[f["a"]]["sifra"], D[f["b"]]["sifra"]}
        groups.setdefault((f["vrsta"], tuple(sorted(sif))), []).append(i)
    meshes, vij_out, deli_v = {}, [], []
    IME = {"vijak_M8": "Vijak M8 s šestrobo glavo + podložka", "vijak_M6": "Vijak M6 s šestrobo glavo + podložka",
           "lesni_vijak_4": "Lesni vijak 4 mm", "zakovicna_matica_M6": "Šestkotna zakovična matica M6"}
    for n, ((kind, sif), idxs) in enumerate(groups.items(), 1):
        vid = f"V{n:02d}"
        if kind not in meshes:
            V, F, mere = make_fastener(kind)
            meshes[kind] = (V, F, mere)
        inst = []
        for j, i in enumerate(idxs, 1):
            f = fasteners[i]
            f["id"] = f"{vid}_{j:02d}"
            f["skupina"] = vid
            M = frame_from_dir(f["dir"])
            M[:3, 3] = f["pos"]
            inst.append({"id": f["id"], "pos_mm": np.round(f["pos"], 3).tolist(), "smer": np.round(f["dir"], 4).tolist(),
                         "skozi": f["a"], "v": f["b"], "dostop_skozi_profil_mm": round(f["dostop_mm"], 1),
                         "matrika_mm": np.round(M, 5).tolist()})
        f0 = fasteners[idxs[0]]
        vij_out.append({"id": vid, "vrsta": kind, "ime": IME.get(kind, kind) + " (predpostavka)", "velikost": f0["velikost"],
                        "kolicina": len(idxs), "med_sifre": list(sif), "dokaz": f0["dokaz"],
                        "geometrija": meshes[kind][2], "v_step": False, "potrditev": NEZNANO, "kosi": inst})
        deli_v.append({"id": vid, "ime": IME.get(kind, kind) + " (predlog)", "sifra": "", "pojavitev": "",
                       "tip": "vijačni material - NI v STEP (predpostavka iz lukenj)", "stars": deli_doc["deli"][0]["stars"],
                       "kolicina": len(idxs), "bbox_mm": {"min": np.round(np.min([fasteners[i]["pos"] for i in idxs], 0) - 8, 1).tolist(),
                                                          "max": np.round(np.max([fasteners[i]["pos"] for i in idxs], 0) + 8, 1).tolist()},
                       "volumen_mm3": None, "material": None, "material_razred_step": None,
                       "material_razred_geometrija": "vijačni material (pocinkano jeklo - predpostavka)",
                       "stevilo_teles": 0, "barva_rgb": [0.78, 0.80, 0.84],
                       "opomba": "Ni v STEP in ni v kosovnici (kosovnice ni). Vrsta in mera sklepana iz lukenj: " + f0["dokaz"]})
    for s in spoji:
        s["vijaki"] = sorted({fasteners[i]["skupina"] for i in s.pop("vijaki_idx")})

    # ---------------- 4) neuporabljene luknje
    unused = collections.Counter()
    for p in ids:
        if kupljen(p):
            continue
        for i, h in enumerate(holes[p]):
            if (p, i) not in used_holes:
                os_ = "XYZ"[int(np.argmax(np.abs(h["ustja"][0][1])))]
                unused[(D[p]["sifra"], h["oblika"], f"{h['mera'][0]}x{h['mera'][1]}", os_)] += 1
    unused_out = [{"sifra": k[0], "oblika": k[1], "mera_mm": k[2], "os": k[3], "stevilo": v} for k, v in sorted(unused.items())]

    # ---------------- izpis
    stat = collections.Counter(s["tip"] for s in spoji)
    out = {
        "opomba": "Nacin spajanja je SKLEPAN iz geometrije (luknje, stiki) in iz pripomb cloveka v ocene.json. "
                  "Vrsta/mera vijakov, vrsta in dolzina zvarov, momenti: " + NEZNANO + ".",
        "pravila": [
            "soosni luknji dveh delov -> vijacni spoj",
            "sestkotni izrez 9,1 mm -> sestkotna zakovicna matica M6 (standardna mera izreza 9,0)",
            "luknja + poln les za njo -> lesni vijak",
            "kupljeno kolo s pritrdilnimi utori -> vijaki (pravilo cloveka: kolesa se vedno vijacijo)",
            "stik jeklo-jeklo brez vijakov -> varjenje (pripomba cloveka: cevi, okvirji, plocevina se varijo)",
            "les na jeklu brez vijakov -> polaganje",
        ],
        "statistika": dict(stat),
        "spoji": spoji,
        "vijacni_material": vij_out,
        "neuporabljene_luknje": unused_out,
    }
    (POSKUS / "spoji.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    np.savez_compressed(IZVOZ / "vijaki.npz", **{k + "_V": v[0] for k, v in meshes.items()}, **{k + "_F": v[1] for k, v in meshes.items()})
    deli_doc["deli"] = deli + deli_v
    (POSKUS / "deli.json").write_text(json.dumps(deli_doc, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---------------- GLB: dodaj vijake kot vozlisca (ime = ID kosa)
    scene = trimesh.load(IZVOZ / "vozicek.glb", force="scene")
    root = [n for n in scene.graph.nodes if n.startswith("MLU")][0]
    for v in vij_out:
        V, F, _ = meshes[v["vrsta"]]
        g = trimesh.Trimesh(V, F, process=False)
        g.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
            name="vijacni_material", baseColorFactor=[0.78, 0.80, 0.84, 1.0], metallicFactor=1.0, roughnessFactor=0.35))
        for k in v["kosi"]:
            if k["id"] in scene.graph.nodes:
                continue
            scene.add_geometry(g, geom_name=v["vrsta"], node_name=k["id"], parent_node_name=root, transform=np.array(k["matrika_mm"]))
    (IZVOZ / "vozicek.glb").write_bytes(scene.export(file_type="glb"))

    print("spoji:", dict(stat))
    for s in spoji:
        print(" ", s["id"], s["deli"], s["tip"], "| povrsina", s["stikna_povrsina_mm2"], "| obod", s["dolzina_oboda_mm"], "|", s["vijaki"], "|", s["stik"][:12])
    for v in vij_out:
        print(" ", v["id"], v["vrsta"], "x", v["kolicina"], v["med_sifre"])
    print("neuporabljene luknje:")
    for u in unused_out:
        print("  ", u)
    print("cas", round(time.time() - t0, 1), "s")


if __name__ == "__main__":
    main()
