"""
Korak 1: analiza STEP (OpenCascade XCAF) + inventura delov + tesselacija + izvoz GLB.

Zagon (iz korena repozitorija):
  trening/okolje/fable/venv312/Scripts/python trening/modeli/vozicek-delovni-mali/fable/03/skripte/01_analiza_in_izvoz.py

Izhodi (v mapi poskusa):
  deli.json                   inventura (ena vrstica = ena pojavitev dela v sestavu)
  izvoz/struktura.json        drevo sestava + surovi STEP podatki + kontrole
  izvoz/vozicek.glb           glTF 2.0: vozlišča = ID delov, enote m, Y-gor (glTF standard)
  izvoz/mreze.npz             mreže v mm, koordinate sestava (Z-gor), za render
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import trimesh

from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ShapeTool, XCAFDoc_ColorType
from OCP.TDF import TDF_Label
from OCP.collections import Sequence_TDF_Label as TDF_LabelSequence
from OCP.TDataStd import TDataStd_Name
from OCP.IFSelect import IFSelect_RetDone
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE, TopAbs_SOLID, TopAbs_REVERSED
from OCP.TopoDS import TopoDS
from OCP.BRep import BRep_Tool
from OCP.TopLoc import TopLoc_Location
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.Quantity import Quantity_Color
from OCP.Interface import Interface_Static

POSKUS = Path(__file__).resolve().parents[1]
MODEL = POSKUS.parents[1]
STEP_FILES = sorted((MODEL / "vhod").glob("*.st*p"))
assert len(STEP_FILES) == 1, STEP_FILES
STEP = STEP_FILES[0]
IZVOZ = POSKUS / "izvoz"
IZVOZ.mkdir(exist_ok=True)

# Nastavitve tesselacije (mm / rad). Glej porocilo.md - odlocitev "mreza".
LIN_DEFL_MM = 0.03
ANG_DEFL_RAD = 0.12


# ---------------------------------------------------------------- surovi STEP
def decode_step_str(s):
    """Dekodira STEP \\X2\\....\\X0\\ (UTF-16 hex) v unicode."""
    def x2(m):
        h = m.group(1)
        return "".join(chr(int(h[i:i + 4], 16)) for i in range(0, len(h), 4))
    return re.sub(r"\\X2\\([0-9A-Fa-f]+)\\X0\\", x2, s)


def parse_step_entities(path):
    # ISO 10303-21: prelomi vrstic niso pomembni (tudi znotraj nizov) -> odstrani jih,
    # NE zamenjaj s presledkom (sicer "kol\nesa" -> "kol esa").
    txt = path.read_text(encoding="latin-1").replace("\r", "").replace("\n", "")
    txt = re.sub(r"/\*.*?\*/", "", txt)  # komentarji v glavi
    header = txt[: txt.index("DATA;")]
    data = txt[txt.index("DATA;") + 5:]
    ents = {}
    for m in re.finditer(r"#(\d+)\s*=\s*(.*?);\s*(?=#\d+\s*=|ENDSEC)", data, re.S):
        ents[int(m.group(1))] = m.group(2).strip()
    return header, ents


def step_strings(arg):
    return [decode_step_str(x) for x in re.findall(r"'((?:[^']|'')*)'", arg)]


def step_refs(arg):
    return [int(x) for x in re.findall(r"#(\d+)", arg)]


def raw_analysis(path):
    header, ents = parse_step_entities(path)
    types = {}
    for k, v in ents.items():
        t = v.split("(")[0].strip() or "(complex)"
        types[t] = types.get(t, 0) + 1
    products = {}       # id -> {naziv, opis}
    pd_to_prod = {}     # product_definition# -> product id
    pdf_to_prod = {}
    for k, v in ents.items():
        if v.startswith("PRODUCT("):
            s = step_strings(v)
            products[k] = {"id": s[0], "naziv": s[1], "opis": s[2] if len(s) > 2 else ""}
    for k, v in ents.items():
        if v.startswith("PRODUCT_DEFINITION_FORMATION"):
            r = step_refs(v)
            pdf_to_prod[k] = products[r[-1]]["id"]
    for k, v in ents.items():
        if v.startswith("PRODUCT_DEFINITION("):
            r = step_refs(v)
            pd_to_prod[k] = pdf_to_prod[r[0]]
    nauo = []
    for k, v in ents.items():
        if v.startswith("NEXT_ASSEMBLY_USAGE_OCCURRENCE"):
            s = step_strings(v)
            r = step_refs(v)
            nauo.append({"ime": s[0], "stars": pd_to_prod[r[0]], "otrok": pd_to_prod[r[1]]})
    # materiali: PROPERTY_DEFINITION('material property','material name'|'density of part', #PD)
    mat = {}
    propdef = {}
    for k, v in ents.items():
        if v.startswith("PROPERTY_DEFINITION(") and "material property" in v:
            s = step_strings(v)
            propdef[k] = (s[1], pd_to_prod.get(step_refs(v)[-1]))
    for k, v in ents.items():
        if v.startswith("PROPERTY_DEFINITION_REPRESENTATION("):
            r = step_refs(v)
            if r[0] in propdef:
                kind, prod = propdef[r[0]]
                rep = ents[r[1]]
                items = step_refs(rep.split("(", 1)[1].split(")", 1)[0])
                for it in items:
                    e = ents.get(it, "")
                    if e.startswith("DESCRIPTIVE_REPRESENTATION_ITEM"):
                        mat.setdefault(prod, {})["material"] = step_strings(e)[0]
                    elif e.startswith("MEASURE_REPRESENTATION_ITEM"):
                        num = re.search(r"MEASURE\(([-0-9.Ee+]+)\)", e)
                        if num:
                            mat.setdefault(prod, {})["gostota_g_cm3"] = float(num.group(1))
    hdr = {
        "opis": " ".join(step_strings(re.search(r"FILE_DESCRIPTION\((.*?)\);", header, re.S).group(1))[:1]),
        "file_name": step_strings(re.search(r"FILE_NAME\((.*?)\);", header, re.S).group(1)),
        "schema": re.search(r"FILE_SCHEMA\s*\(\(\s*'([^']*)'", header).group(1),
    }
    units = [v for v in ents.values() if "LENGTH_UNIT" in v]
    return {
        "glava": hdr,
        "enote_dolzine": units,
        "stevilo_entitet": len(ents),
        "tipi": dict(sorted(types.items(), key=lambda kv: -kv[1])),
        "produkti": {p["id"]: p for p in products.values()},
        "pojavitve_nauo": nauo,
        "materiali": mat,
    }


# ---------------------------------------------------------------- XCAF
def label_name(lab):
    attr = TDataStd_Name()
    if lab.FindAttribute(TDataStd_Name.GetID_s(), attr):
        return attr.Get().ToExtString()
    return ""


def get_color(ctool, lab, shape):
    c = Quantity_Color()
    for t in (XCAFDoc_ColorType.XCAFDoc_ColorSurf, XCAFDoc_ColorType.XCAFDoc_ColorGen):
        if ctool.GetColor(shape, t, c):
            return [round(c.Red(), 4), round(c.Green(), 4), round(c.Blue(), 4)]
    return None


def face_colors_majority(ctool, shape):
    """Barva, ki je najpogostejša na ploskvah (STEP ima STYLED_ITEM na ploskvah)."""
    cnt = {}
    exp = TopExp_Explorer(shape, TopAbs_FACE)
    c = Quantity_Color()
    while exp.More():
        f = exp.Current()
        if ctool.GetColor(f, XCAFDoc_ColorType.XCAFDoc_ColorSurf, c) or ctool.GetColor(f, XCAFDoc_ColorType.XCAFDoc_ColorGen, c):
            key = (round(c.Red(), 3), round(c.Green(), 3), round(c.Blue(), 3))
            cnt[key] = cnt.get(key, 0) + 1
        exp.Next()
    if not cnt:
        return None, {}
    best = max(cnt.items(), key=lambda kv: kv[1])[0]
    return list(best), {str(k): v for k, v in cnt.items()}


def trsf_to_matrix(loc: TopLoc_Location):
    t = loc.Transformation()
    m = np.eye(4)
    for i in range(3):
        for j in range(4):
            m[i, j] = t.Value(i + 1, j + 1)
    return m


def tessellate(shape, ctool=None):
    """Vrne (V, F, n_faces, n_faces_brez_mreze) v lokalnih koordinatah oblike."""
    BRepMesh_IncrementalMesh(shape, LIN_DEFL_MM, False, ANG_DEFL_RAD, True)
    verts, faces, cols = [], [], []
    qc = Quantity_Color()
    off = 0
    nf = nmiss = 0
    exp = TopExp_Explorer(shape, TopAbs_FACE)
    while exp.More():
        face = TopoDS.Face(exp.Current())
        nf += 1
        loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(face, loc)
        if tri is None:
            nmiss += 1
            exp.Next()
            continue
        tr = loc.Transformation()
        n = tri.NbNodes()
        pts = np.empty((n, 3))
        for i in range(1, n + 1):
            p = tri.Node(i).Transformed(tr)
            pts[i - 1] = (p.X(), p.Y(), p.Z())
        tris = np.empty((tri.NbTriangles(), 3), dtype=np.int64)
        rev = face.Orientation() == TopAbs_REVERSED
        for i in range(1, tri.NbTriangles() + 1):
            a, b, c = tri.Triangle(i).Get()
            tris[i - 1] = (a, c, b) if rev else (a, b, c)
        verts.append(pts)
        faces.append(tris - 1 + off)
        rgb = (-1.0, -1.0, -1.0)
        if ctool is not None and (ctool.GetColor(face, XCAFDoc_ColorType.XCAFDoc_ColorSurf, qc)
                                  or ctool.GetColor(face, XCAFDoc_ColorType.XCAFDoc_ColorGen, qc)):
            rgb = (qc.Red(), qc.Green(), qc.Blue())
        cols.append(np.tile(np.array(rgb, dtype=np.float32), (len(tris), 1)))
        off += n
        exp.Next()
    V = np.vstack(verts) if verts else np.zeros((0, 3))
    F = np.vstack(faces) if faces else np.zeros((0, 3), dtype=np.int64)
    C = np.vstack(cols) if cols else np.zeros((0, 3), dtype=np.float32)
    return V, F, C, nf, nmiss


def area_mm2(shape):
    g = GProp_GProps()
    BRepGProp.SurfaceProperties_s(shape, g)
    return g.Mass()


# Razred materiala za prikaz. Dva neodvisna vira: (a) ime materiala v STEP, (b) geometrija.
STEP_MATERIAL_RAZRED = [("stainless", "inox"), ("inox", "inox"), ("iveral", "les / iverna plosca"), ("wood", "les / iverna plosca"),
                        ("steel", "jeklo"), ("generic", None)]


def razred_iz_step(mat):
    if not mat:
        return None
    for key, r in STEP_MATERIAL_RAZRED:
        if key in mat.lower():
            return r
    return None


def razred_iz_geometrije(n_teles, n_ploskev, tipi_ploskev, vol, area, size):
    """Groba ocena brez imena materiala. Vrne (razred, razlaga)."""
    if n_teles > 1:
        return "kupljen sestavni del (vec teles)", f"{n_teles} teles v enem produktu"
    t = 2 * vol / area if area else 0          # ekvivalentna debelina stene (plosca/plocevina/cev)
    s = sorted(size)
    if n_ploskev == 6 and set(tipi_ploskev) == {"Plane"} and 8 <= s[0] <= 45 and s[1] > 10 * s[0]:
        return "les / iverna plosca", f"poln kvader debeline {s[0]:.0f} mm brez lukenj in zaokrozitev"
    if t <= 4.0:
        return "jeklo (plocevina / cev)", f"tankostenski del, ekvivalentna debelina stene {t:.1f} mm"
    return "neznano", f"ekvivalentna debelina {t:.1f} mm"


def face_types(shape):
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    out = {}
    exp = TopExp_Explorer(shape, TopAbs_FACE)
    while exp.More():
        k = str(BRepAdaptor_Surface(TopoDS.Face(exp.Current())).GetType()).split("_")[-1]
        out[k] = out.get(k, 0) + 1
        exp.Next()
    return out


def count_solids(shape):
    n = 0
    exp = TopExp_Explorer(shape, TopAbs_SOLID)
    while exp.More():
        n += 1
        exp.Next()
    return n


def volume_mm3(shape):
    g = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, g)
    return g.Mass(), g.CentreOfMass()


def bbox(shape):
    b = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape, b, False, False)
    p0, p1 = b.CornerMin(), b.CornerMax()
    x0, y0, z0, x1, y1, z1 = p0.X(), p0.Y(), p0.Z(), p1.X(), p1.Y(), p1.Z()
    return [x0, y0, z0], [x1, y1, z1]


def main():
    raw = raw_analysis(STEP)

    Interface_Static.SetCVal_s("xstep.cascade.unit", "MM")
    doc = TDocStd_Document(TCollection_ExtendedString("XmlOcaf"))
    rdr = STEPCAFControl_Reader()
    rdr.SetNameMode(True)
    rdr.SetColorMode(True)
    rdr.SetLayerMode(True)
    st = rdr.ReadFile(str(STEP))
    assert st == IFSelect_RetDone, f"STEP branje ni uspelo: {st}"
    assert rdr.Transfer(doc), "Transfer ni uspel"
    stool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    ctool = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())

    roots = TDF_LabelSequence()
    stool.GetFreeShapes(roots)
    assert roots.Length() == 1, f"pricakoval en koren, dobil {roots.Length()}"
    root = roots.Value(1)

    prod_cache = {}   # ime produkta -> dict z mrezo in lastnostmi (lokalne koordinate)
    deli = []
    tree = []

    def product_info(ref_lab, name):
        if name in prod_cache:
            return prod_cache[name]
        shape = XCAFDoc_ShapeTool.GetShape_s(ref_lab)
        V, F, C, nf, nmiss = tessellate(shape, ctool)
        vol, _ = volume_mm3(shape)
        col = get_color(ctool, ref_lab, shape)
        fcol, fcnt = face_colors_majority(ctool, shape)
        ft = face_types(shape)
        ar = area_mm2(shape)
        bmn, bmx = bbox(shape)
        geo_r, geo_why = razred_iz_geometrije(count_solids(shape), nf, ft, vol, ar, [b - a for a, b in zip(bmn, bmx)])
        info = dict(shape=shape, V=V, F=F, C=C, geo_razred=geo_r, geo_razlaga=geo_why, tipi_ploskev=ft, povrsina=ar, n_ploskev=nf, n_ploskev_brez_mreze=nmiss,
                    n_teles=count_solids(shape), volumen=vol,
                    barva=col or fcol, barve_ploskev=fcnt)
        prod_cache[name] = info
        return info

    counter = [0]

    def walk(lab, parent_mat, parent_name, path, depth):
        """lab je referencni label (produkt). Rekurzija po komponentah."""
        comps = TDF_LabelSequence()
        XCAFDoc_ShapeTool.GetComponents_s(lab, comps, False)
        for i in range(1, comps.Length() + 1):
            comp = comps.Value(i)
            inst_name = label_name(comp)
            ref = TDF_Label()
            XCAFDoc_ShapeTool.GetReferredShape_s(comp, ref)
            prod_name = label_name(ref)
            loc = XCAFDoc_ShapeTool.GetLocation_s(comp)
            M = parent_mat @ trsf_to_matrix(loc)
            is_asm = XCAFDoc_ShapeTool.IsAssembly_s(ref)
            node = {"pojavitev": inst_name, "produkt": prod_name, "stars": parent_name,
                    "pot": path + [inst_name], "globina": depth, "sestav": bool(is_asm),
                    "matrika_mm": np.round(M, 6).tolist()}
            tree.append(node)
            if is_asm:
                walk(ref, M, inst_name, path + [inst_name], depth + 1)
                continue
            counter[0] += 1
            pid = f"P{counter[0]:03d}"
            node["id"] = pid
            info = product_info(ref, prod_name)
            # globalni bbox iz B-Rep oblike z lokacijo (natancno), ne iz mreze
            gl_shape = info["shape"].Moved(TopLoc_Location(_np_to_trsf(M)))
            bmin, bmax = bbox(gl_shape)
            vol_gl, com = volume_mm3(gl_shape)
            meta = raw["produkti"].get(prod_name, {})
            matr = raw["materiali"].get(prod_name, {})
            deli.append({
                "id": pid,
                "ime": meta.get("opis", ""),
                "sifra": prod_name,
                "pojavitev": inst_name,
                "tip": "solid" if info["n_teles"] == 1 else f"produkt z {info['n_teles']} telesi",
                "stars": parent_name,
                "pot": "/".join(path + [inst_name]),
                "kolicina": 1,
                "bbox_mm": {"min": [round(v, 3) for v in bmin], "max": [round(v, 3) for v in bmax]},
                "velikost_mm": [round(b - a, 2) for a, b in zip(bmin, bmax)],
                "teziste_mm": [round(com.X(), 3), round(com.Y(), 3), round(com.Z(), 3)],
                "volumen_mm3": round(vol_gl, 1),
                "material": matr.get("material"),
                "material_razred_step": razred_iz_step(matr.get("material")),
                "material_razred_geometrija": info["geo_razred"],
                "material_geometrija_razlaga": info["geo_razlaga"],
                "gostota_g_cm3": matr.get("gostota_g_cm3"),
                "masa_kg_izracun": round(vol_gl * 1e-3 * matr["gostota_g_cm3"] / 1000, 3) if matr.get("gostota_g_cm3") else None,
                "stevilo_teles": info["n_teles"],
                "barva_rgb": info["barva"],
                "transformacija_mm": np.round(M, 6).tolist(),
                "opomba": "Ime (opis) in sifra iz STEP PRODUCT; pojavitev iz NEXT_ASSEMBLY_USAGE_OCCURRENCE.",
            })

    walk(root, np.eye(4), label_name(root), [label_name(root)], 1)

    # ------------------------------------------------ kontrole mreze
    mesh_checks = {}
    for name, info in prod_cache.items():
        tm = trimesh.Trimesh(info["V"], info["F"], process=True)
        mvol = float(tm.volume) if len(tm.faces) else 0.0
        mesh_checks[name] = {
            "trikotnikov": int(len(info["F"])),
            "ploskev_brep": info["n_ploskev"],
            "ploskev_brez_mreze": info["n_ploskev_brez_mreze"],
            "vodotesna": bool(tm.is_watertight),
            "volumen_brep_mm3": round(info["volumen"], 1),
            "volumen_mreza_mm3": round(mvol, 1),
            "odstopanje_volumna_pct": round(100 * (mvol - info["volumen"]) / info["volumen"], 3) if info["volumen"] else None,
            "stevilo_teles": info["n_teles"],
            "barve_ploskev": info["barve_ploskev"],
        }

    # ------------------------------------------------ GLB (m, Y-gor)
    scene = trimesh.Scene()
    root_name = label_name(root)
    # STEP: mm, Z gor  ->  glTF: m, Y gor  (x, y, z) -> (x, z, -y) * 0.001
    R = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]], float)
    S = np.diag([0.001, 0.001, 0.001, 1.0])
    scene.graph.update(frame_from=scene.graph.base_frame, frame_to=root_name, matrix=S @ R)
    geoms = {}
    for d in deli:
        info = prod_cache[d["sifra"]]
        if d["sifra"] not in geoms:
            g = trimesh.Trimesh(info["V"], info["F"], process=False)
            rgb = d["barva_rgb"] or [0.7, 0.7, 0.7]
            mat = trimesh.visual.material.PBRMaterial(
                name=d["sifra"], baseColorFactor=[*rgb, 1.0], metallicFactor=0.2, roughnessFactor=0.6)
            g.visual = trimesh.visual.TextureVisuals(material=mat)
            g.metadata["name"] = d["sifra"]
            geoms[d["sifra"]] = g
        scene.add_geometry(geoms[d["sifra"]], geom_name=d["sifra"], node_name=d["id"],
                           parent_node_name=root_name, transform=np.array(d["transformacija_mm"]))
    glb = scene.export(file_type="glb")
    (IZVOZ / "vozicek.glb").write_bytes(glb)

    # ------------------------------------------------ npz za render (mm, Z gor, globalno)
    arrs = {}
    for d in deli:
        info = prod_cache[d["sifra"]]
        M = np.array(d["transformacija_mm"])
        V = info["V"] @ M[:3, :3].T + M[:3, 3]
        arrs[d["id"] + "_V"] = V.astype(np.float32)
        arrs[d["id"] + "_F"] = info["F"].astype(np.int32)
        if len(info["barve_ploskev"]) > 1:      # vec barv v produktu (kupljen del) -> barva po trikotniku
            arrs[d["id"] + "_C"] = info["C"]
    np.savez_compressed(IZVOZ / "mreze.npz", **arrs)

    # ------------------------------------------------ kontrola GLB: ponovno nalozi
    re_scene = trimesh.load(IZVOZ / "vozicek.glb", force="scene")
    glb_nodes = sorted(n for n in re_scene.graph.nodes_geometry)
    allb = np.array([[*d["bbox_mm"]["min"], *d["bbox_mm"]["max"]] for d in deli])
    sestav_bbox = {"min": allb[:, :3].min(0).round(3).tolist(), "max": allb[:, 3:].max(0).round(3).tolist()}
    glb_bounds_m = re_scene.bounds.tolist()

    leaf_nauo = [n for n in raw["pojavitve_nauo"] if n["otrok"] not in {x["stars"] for x in raw["pojavitve_nauo"]}]
    kontrole = {
        "stevilo_produktov_step": len(raw["produkti"]),
        "stevilo_nauo_step": len(raw["pojavitve_nauo"]),
        "stevilo_listnih_nauo_step": len(leaf_nauo),
        "stevilo_delov_xcaf": len(deli),
        "stevilo_manifold_solid_brep_step": raw["tipi"].get("MANIFOLD_SOLID_BREP", 0),
        "vsota_teles_po_produktih_unikatno": sum(p["n_teles"] for p in prod_cache.values()),
        "glb_vozlisca_z_geometrijo": len(glb_nodes),
        "glb_id_ujemanje": glb_nodes == sorted(d["id"] for d in deli),
        "sestav_bbox_mm": sestav_bbox,
        "glb_bounds_m_Ygor": glb_bounds_m,
        "nastavitve_mreze": {"lin_defl_mm": LIN_DEFL_MM, "ang_defl_rad": ANG_DEFL_RAD},
        "mreze": mesh_checks,
    }
    (POSKUS / "deli.json").write_text(json.dumps({"vir": STEP.name, "enote": "mm", "koordinate": "STEP sestav, Z gor", "deli": deli}, ensure_ascii=False, indent=2), encoding="utf-8")
    (IZVOZ / "struktura.json").write_text(json.dumps({"surovi_step": raw, "drevo_xcaf": tree, "kontrole": kontrole}, ensure_ascii=False, indent=2), encoding="utf-8")

    print("produktov", kontrole["stevilo_produktov_step"], "nauo", kontrole["stevilo_nauo_step"],
          "listnih", kontrole["stevilo_listnih_nauo_step"], "delov", len(deli), "glb", len(glb_nodes), kontrole["glb_id_ujemanje"])
    print("bbox sestava", sestav_bbox)
    for d in deli:
        print(d["id"], d["pojavitev"], "|", d["ime"], "|", d["velikost_mm"], d["bbox_mm"]["min"], d["stevilo_teles"], d["barva_rgb"])
    for k, v in mesh_checks.items():
        print(k, v["trikotnikov"], v["vodotesna"], v["odstopanje_volumna_pct"], v["ploskev_brez_mreze"])


def _np_to_trsf(M):
    from OCP.gp import gp_Trsf
    t = gp_Trsf()
    t.SetValues(M[0, 0], M[0, 1], M[0, 2], M[0, 3],
                M[1, 0], M[1, 1], M[1, 2], M[1, 3],
                M[2, 0], M[2, 1], M[2, 2], M[2, 3])
    return t


if __name__ == "__main__":
    main()
