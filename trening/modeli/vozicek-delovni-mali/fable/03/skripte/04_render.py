"""
Korak 4: izbira kamere z merjeno vidnostjo, postavitev napisov brez prekrivanja, render videa (VTK + PIL + ffmpeg).

Novo v poskusu 03 (glej porocilo.md, diagnoza):
  1. MASKIRNA SCENA: drugo (majhno, neosvetljeno) okno VTK, v katerem ima vsak del / vijak / zvar svojo barvo = ID.
     Iz nje se IZMERI, koliko vijaka ali zvara kamera dejansko vidi (vidni piksli / piksli brez zakrivanja).
  2. KAMERA SPOJA se izbere z iskanjem po smereh (az x el) - zmaga smer z najvecjo izmerjeno vidnostjo s strani dostopa.
     Ce privit vijak ostane zakrit (npr. v cevi), se zakrivajoci del za cas vijacenja naredi prosojen.
  3. NAPISI se postavijo tja, kjer maska pove, da ne prekrivajo gibajocih delov, vijakov ali zvarov (prekrivanje = 0 px).
  4. Glava / noga / napisi so izrisani s PIL v slogu FINES (logo, oranzna #ca5010, sive ink, pisava Inter), samo za operaterja.

Zagon:
  trening/okolje/fable/venv312/Scripts/python trening/modeli/vozicek-delovni-mali/fable/03/skripte/04_render.py
  ... 04_render.py --slicice     samo kontrolne slicice, predogled in kontrole (hitro, brez videa)
Izhodi: video.mp4, predogled.png, izvoz/slicice/*.png, izvoz/video_casovnica.json,
        izvoz/kontrola_vidnosti.json, izvoz/kontrola_napisov.json; koraki.json dobi izbrane kamere (kamera.pregled_spojev, kamera.detajli)
"""
import json
import math
import subprocess
import sys
import textwrap
from pathlib import Path

import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray, vtk_to_numpy
from PIL import Image, ImageDraw, ImageFilter, ImageFont

POSKUS = Path(__file__).resolve().parents[1]
IZVOZ = POSKUS / "izvoz"
SLICICE = IZVOZ / "slicice"
SLICICE.mkdir(parents=True, exist_ok=True)
SAMO_SLICICE = "--slicice" in sys.argv
REPO = POSKUS.parents[4]

OUT_W, OUT_H, FPS = 1920, 1080, 30
SS = 1.5                               # nadvzorcenje (render 2880x1620 -> lanczos na 1920x1080)
W, H = int(OUT_W * SS), int(OUT_H * SS)
POUDAREK = np.array([1.0, 0.45, 0.05])
BARVA_NACINA = {"varjenje": (0.86, 0.33, 0.05), "vijacenje": (0.10, 0.40, 0.80), "polaganje + vijacenje": (0.10, 0.40, 0.80),
                "polaganje": (0.12, 0.55, 0.30), "zakovicenje": (0.45, 0.25, 0.70)}

POGLEDI = {   # smer od sredisca proti kameri (Z gor); "spredaj" = stran -Y, "desno" = +X (dogovor)
    "zgoraj spredaj-desno": (1.0, -1.25, 0.95),
    "spredaj-desno": (1.0, -1.3, 0.55),
    "spredaj-desno nizko": (1.0, -1.4, 0.12),
    "od spodaj": (1.0, -1.3, -0.6),
    "zadaj-levo": (-1.3, 1.0, 0.5),
    "celota": (1.0, -1.35, 0.6),
}

deli_all = json.loads((POSKUS / "deli.json").read_text(encoding="utf-8"))["deli"]
deli = [d for d in deli_all if not d["id"].startswith("V")]
koraki = json.loads((POSKUS / "koraki.json").read_text(encoding="utf-8"))["koraki"]
spoji_doc = json.loads((POSKUS / "spoji.json").read_text(encoding="utf-8"))
SPOJ = {s["id"]: s for s in spoji_doc["spoji"]}
VIJ = {v["id"]: v for v in spoji_doc["vijacni_material"]}
KOS = {k["id"]: (v, k) for v in VIJ.values() for k in v["kosi"]}
meshes = np.load(IZVOZ / "mreze.npz")
vmesh = np.load(IZVOZ / "vijaki.npz")
DEL = {d["id"]: d for d in deli}
IDS = [d["id"] for d in deli]


def px(v):
    return int(round(v * SS))


def ease(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ materiali (razred -> PBR)
def razred(d):
    return d["material_razred_step"] or d["material_razred_geometrija"]


MATERIALI = {   # barva, kovinskost, hrapavost
    "jeklo": ((0.52, 0.53, 0.55), 1.0, 0.48),
    "jeklo (plocevina / cev)": ((0.52, 0.53, 0.55), 1.0, 0.48),
    "inox": ((0.86, 0.87, 0.88), 1.0, 0.22),
    "les / iverna plosca": ((1.0, 1.0, 1.0), 0.0, 0.62),       # barvo da tekstura
    "vijak": ((0.80, 0.82, 0.86), 1.0, 0.30),
    "zvar": ((0.33, 0.34, 0.38), 1.0, 0.65),
}


def wood_texture(n=1024, seed=7):
    """Proceduralna tekstura lesa (letnice vzdolz U). Deterministicna (seed)."""
    rng = np.random.default_rng(seed)
    y = np.linspace(0, 1, n)[:, None]
    x = np.linspace(0, 1, n)[None, :]
    low = rng.random((9, 5))
    yi, xi = np.linspace(0, 8, n), np.linspace(0, 4, n)
    y0, x0 = np.clip(yi.astype(int), 0, 7), np.clip(xi.astype(int), 0, 3)
    fy, fx = (yi - y0)[:, None], (xi - x0)[None, :]
    warp = (low[y0][:, x0] * (1 - fy) * (1 - fx) + low[y0 + 1][:, x0] * fy * (1 - fx)
            + low[y0][:, x0 + 1] * (1 - fy) * fx + low[y0 + 1][:, x0 + 1] * fy * fx)
    rings = np.sin((y * 26 + warp * 3.2 + 0.25 * np.sin(x * 7)) * 2 * np.pi)
    streak = rng.random((n, 1))
    k = np.ones(5) / 5
    streak = np.convolve(streak[:, 0], k, mode="same")[:, None]
    fine = rng.random((n, n // 16)).repeat(16, axis=1)
    val = 0.80 + 0.10 * rings + 0.10 * (streak - 0.5) * 2 + 0.05 * (fine - 0.5)
    base = np.array([0.80, 0.60, 0.38])
    dark = np.array([0.52, 0.34, 0.18])
    t = np.clip((val - 0.6) / 0.4, 0, 1)[..., None]
    img = dark * (1 - t) + base * t
    return (np.clip(img, 0, 1) * 255).astype(np.uint8)


def np_texture(img, srgb=True, repeat=True):
    h, w = img.shape[:2]
    im = vtk.vtkImageData()
    im.SetDimensions(w, h, 1)
    arr = numpy_to_vtk(img.reshape(-1, img.shape[2]), deep=True)
    im.GetPointData().SetScalars(arr)
    t = vtk.vtkTexture()
    t.SetInputData(im)
    t.InterpolateOn()
    t.MipmapOn()
    t.SetRepeat(repeat)
    if srgb:
        t.UseSRGBColorSpaceOn()
    return t


def environment():
    """Studijsko okolje (equirect, float): svetel strop, mehka okna za odseve na kovini."""
    h, w = 256, 512
    v = np.linspace(1, -1, h)[:, None]              # +1 zenit ... -1 tla
    u = np.linspace(0, 2 * np.pi, w)[None, :]
    lum = (0.55 + 0.45 * np.clip(v, 0, 1)) * np.where(v < 0, 0.55 + 0.25 * (1 + v), 1.0)
    img = np.ones((h, w, 3), np.float32) * lum[..., None].astype(np.float32)
    for (u0, du, v0, dv, I) in [(0.9, 0.5, 0.55, 0.25, 5.0), (2.9, 0.7, 0.45, 0.2, 3.5), (4.6, 0.5, 0.6, 0.2, 4.0), (0.0, 6.3, 0.97, 0.03, 3.0)]:
        m = (np.abs(((u - u0 + np.pi) % (2 * np.pi)) - np.pi) < du / 2) & (np.abs(v - v0) < dv / 2)
        img[np.broadcast_to(m, (h, w))] = I
    return img


def make_polydata(V, F, uv=None, cell_rgb=None):
    pts = vtk.vtkPoints()
    pts.SetData(numpy_to_vtk(np.ascontiguousarray(V, dtype=np.float64), deep=True))
    cells = np.hstack([np.full((len(F), 1), 3, dtype=np.int64), F.astype(np.int64)]).ravel()
    ca = vtk.vtkCellArray()
    ca.ImportLegacyFormat(numpy_to_vtkIdTypeArray(cells, deep=True))
    pd = vtk.vtkPolyData()
    pd.SetPoints(pts)
    pd.SetPolys(ca)
    if cell_rgb is not None:
        a = numpy_to_vtk((np.clip(cell_rgb, 0, 1) * 255).astype(np.uint8), deep=True)
        a.SetName("rgb")
        pd.GetCellData().SetScalars(a)
    n = vtk.vtkPolyDataNormals()
    n.SetInputData(pd)
    n.SplittingOn()
    n.SetFeatureAngle(35)
    n.ConsistencyOff()
    n.AutoOrientNormalsOff()
    n.Update()
    out = n.GetOutput()
    if uv is not None:
        P = vtk_to_numpy(out.GetPoints().GetData())
        N = vtk_to_numpy(out.GetPointData().GetNormals())
        ax = np.argmax(np.abs(N), axis=1)
        tc = np.empty((len(P), 2), np.float32)
        for a_, (i, j) in {0: (1, 2), 1: (0, 2), 2: (0, 1)}.items():
            m = ax == a_
            tc[m, 0] = P[m, i] / uv
            tc[m, 1] = P[m, j] / (uv * 0.45)
        t = numpy_to_vtk(tc, deep=True)
        t.SetName("uv")
        out.GetPointData().SetTCoords(t)
    return out


def edges_actor(pd, angle=38):
    fe = vtk.vtkFeatureEdges()
    fe.SetInputData(pd)
    fe.BoundaryEdgesOff()
    fe.NonManifoldEdgesOff()
    fe.ManifoldEdgesOff()
    fe.FeatureEdgesOn()
    fe.SetFeatureAngle(angle)
    fe.ColoringOff()
    fe.Update()
    m = vtk.vtkPolyDataMapper()
    m.SetInputData(fe.GetOutput())
    m.ScalarVisibilityOff()
    m.SetResolveCoincidentTopologyToPolygonOffset()
    m.SetRelativeCoincidentTopologyLineOffsetParameters(0, -4)
    a = vtk.vtkActor()
    a.SetMapper(m)
    p = a.GetProperty()
    p.SetColor(0.08, 0.08, 0.10)
    p.SetLineWidth(max(1.0, 1.1 * SS))
    p.SetOpacity(0.55)
    p.LightingOff()
    return a


def pbr(actor, color, metallic, rough):
    p = actor.GetProperty()
    p.SetInterpolationToPBR()
    p.SetColor(*color)
    p.SetMetallic(metallic)
    p.SetRoughness(rough)
    p.SetOcclusionStrength(1.0)


# ------------------------------------------------------------------ scena
rw = vtk.vtkRenderWindow()
rw.SetOffScreenRendering(1)
rw.SetSize(W, H)
rw.SetMultiSamples(0)
ren = vtk.vtkRenderer()
ren.SetBackground(0.80, 0.83, 0.87)
ren.SetBackground2(0.95, 0.96, 0.97)
ren.GradientBackgroundOn()
ren.UseFXAAOn()
rw.AddRenderer(ren)

env = environment()
env_tex = np_texture(env, srgb=False, repeat=False)
env_tex.SetColorModeToDirectScalars()
ren.UseImageBasedLightingOn()
ren.SetEnvironmentTexture(env_tex)
ren.SetEnvironmentUp(0, 0, 1)
ren.SetEnvironmentRight(1, 0, 0)
ren.AutomaticLightCreationOff()
key = vtk.vtkLight()
key.SetLightTypeToCameraLight()
key.SetPosition(-0.5, 0.9, 1.0)
key.SetFocalPoint(0, 0, 0)
key.SetIntensity(1.6)
ren.AddLight(key)
ren.UseSSAOOn()
ren.SetSSAORadius(45.0)
ren.SetSSAOBias(1.5)
ren.SetSSAOKernelSize(64)
ren.SetSSAOBlur(True)

wood = np_texture(wood_texture())

PART = {}       # pid -> {"actors": [...], "edges": [...], "mat": [(color, metal, rough, tex, scalars)], "center": c}
for pid in IDS:
    d = DEL[pid]
    V, F = meshes[pid + "_V"], meshes[pid + "_F"]
    r = razred(d)
    entry = {"actors": [], "edges": [], "mat": []}
    subsets = []
    if pid + "_C" in meshes.files:          # kupljen del z barvami po ploskvah (kolo)
        C = meshes[pid + "_C"].copy()
        blue = (C[:, 2] > 0.9) & (C[:, 0] < 0.7) & (C[:, 0] > 0.5)   # privzeta modra dobavitelja -> pocinkano jeklo (predpostavka)
        grey = (np.abs(C[:, 0] - C[:, 1]) < 0.01) & (np.abs(C[:, 1] - C[:, 2]) < 0.01) & (C[:, 0] > 0.5)
        metal = blue | grey
        Cm = C.copy()
        Cm[blue] = (0.74, 0.76, 0.80)
        Cm[C[:, 0] < 0] = (0.5, 0.5, 0.5)
        subsets.append((F[metal], Cm[metal], 1.0, 0.35))
        subsets.append((F[~metal], Cm[~metal], 0.0, 0.55))
    for sub in (subsets or [None]):
        if sub is None:
            color, metal_, rough = MATERIALI.get(r, ((0.7, 0.7, 0.7), 0.0, 0.6))
            is_wood = r.startswith("les")
            pd = make_polydata(V, F, uv=600.0 if is_wood else None)
        else:
            Fs, Cs, metal_, rough = sub
            color, is_wood = (1.0, 1.0, 1.0), False
            pd = make_polydata(V, Fs, cell_rgb=Cs)
        m = vtk.vtkPolyDataMapper()
        m.SetInputData(pd)
        if sub is None:
            m.ScalarVisibilityOff()
        else:
            m.SetScalarModeToUseCellData()
            m.SetColorModeToDirectScalars()
        a = vtk.vtkActor()
        a.SetMapper(m)
        pbr(a, color, metal_, rough)
        if is_wood:
            a.GetProperty().SetBaseColorTexture(wood)
        ren.AddActor(a)
        entry["actors"].append(a)
        entry["mat"].append((np.array(color), metal_, rough, sub is not None))
        e = edges_actor(pd, 50 if sub is not None else 38)
        ren.AddActor(e)
        entry["edges"].append(e)
    b = d["bbox_mm"]
    entry["center"] = (np.array(b["min"]) + np.array(b["max"])) / 2
    PART[pid] = entry

# vijacni material: en aktor na kos
FAST = {}
for kid, (v, k) in KOS.items():
    pd = make_polydata(vmesh[v["vrsta"] + "_V"], vmesh[v["vrsta"] + "_F"])
    m = vtk.vtkPolyDataMapper()
    m.SetInputData(pd)
    m.ScalarVisibilityOff()
    a = vtk.vtkActor()
    a.SetMapper(m)
    pbr(a, *MATERIALI["vijak"])
    a.VisibilityOff()
    ren.AddActor(a)
    FAST[kid] = {"actor": a, "M": np.array(k["matrika_mm"]), "pos": np.array(k["pos_mm"]), "dir": np.array(k["smer"]),
                 "dostop": k["dostop_skozi_profil_mm"], "owner": k["skozi"]}

zmin = min(DEL[p]["bbox_mm"]["min"][2] for p in IDS)
# tla: brez ravnine (velika ravnina + SSAO da pasove); samo mehka kontaktna senca pod vozickom
_n = 256
_yy, _xx = np.mgrid[-1:1:_n * 1j, -1:1:_n * 1j]
_r = np.sqrt(np.abs(_xx) ** 2.6 + np.abs(_yy) ** 2.6)
_alpha = np.clip(1 - _r, 0, 1) ** 1.6 * 0.42
_img = np.zeros((_n, _n, 4), np.uint8)
_img[..., :3] = 30
_img[..., 3] = (_alpha * 255).astype(np.uint8)
shadow_tex = np_texture(_img, srgb=False, repeat=False)
plane = vtk.vtkPlaneSource()
plane.SetOrigin(-950, -620, zmin - 0.5)
plane.SetPoint1(950, -620, zmin - 0.5)
plane.SetPoint2(-950, 620, zmin - 0.5)
pm = vtk.vtkPolyDataMapper()
pm.SetInputConnection(plane.GetOutputPort())
floor = vtk.vtkActor()
floor.SetMapper(pm)
floor.SetTexture(shadow_tex)
floor.GetProperty().LightingOff()
floor.ForceTranslucentOn()
ren.AddActor(floor)

cam = ren.GetActiveCamera()
cam.SetViewAngle(28)


# ------------------------------------------------------------------ zvari (svetleca sled + trajna gosenica)
def resample(poly, step=3.0):
    poly = np.asarray(poly, float)
    seg = np.linalg.norm(np.diff(poly, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    if s[-1] < 1e-6:
        return poly[:1]
    n = max(2, int(s[-1] / step) + 1)
    t = np.linspace(0, s[-1], n)
    return np.stack([np.interp(t, s, poly[:, i]) for i in range(3)], axis=1)


SEAMS = {sid: [resample(p) for p in s["obod_mm"]] for sid, s in SPOJ.items() if s["tip"] == "varjenje"}


def tube_actor(radius, color, lighting=True, opacity=1.0, metallic=None):
    pd = vtk.vtkPolyData()
    tf = vtk.vtkTubeFilter()
    tf.SetInputData(pd)
    tf.SetRadius(radius)
    tf.SetNumberOfSides(10)
    tf.CappingOn()
    m = vtk.vtkPolyDataMapper()
    m.SetInputConnection(tf.GetOutputPort())
    a = vtk.vtkActor()
    a.SetMapper(m)
    if metallic is not None:
        pbr(a, color, metallic, 0.65)
    else:
        a.GetProperty().SetColor(*color)
    if not lighting:
        a.GetProperty().LightingOff()
    a.GetProperty().SetOpacity(opacity)
    a.VisibilityOff()
    ren.AddActor(a)
    return a, pd


def set_lines(pd, polylines):
    pts = vtk.vtkPoints()
    lines = vtk.vtkCellArray()
    i = 0
    for pl in polylines:
        if len(pl) < 2:
            continue
        lines.InsertNextCell(len(pl))
        for p in pl:
            pts.InsertNextPoint(*p)
            lines.InsertCellPoint(i)
            i += 1
    pd.SetPoints(pts)
    pd.SetLines(lines)
    pd.Modified()


glow_a, glow_pd = tube_actor(2.6, (1.0, 0.80, 0.35), lighting=False)
halo_a, halo_pd = tube_actor(7.0, (1.0, 0.55, 0.10), lighting=False, opacity=0.28)
arc_src = vtk.vtkSphereSource()
arc_src.SetRadius(6.0)
arc_src.SetThetaResolution(16)
arc_src.SetPhiResolution(16)
arc_pd = vtk.vtkPolyData()
arc_gl = vtk.vtkGlyph3D()
arc_gl.SetInputData(arc_pd)
arc_gl.SetSourceConnection(arc_src.GetOutputPort())
arc_m = vtk.vtkPolyDataMapper()
arc_m.SetInputConnection(arc_gl.GetOutputPort())
arc_a = vtk.vtkActor()
arc_a.SetMapper(arc_m)
arc_a.GetProperty().LightingOff()
arc_a.GetProperty().SetColor(1.0, 0.97, 0.85)
arc_a.VisibilityOff()
ren.AddActor(arc_a)
BEADS = {}      # sid -> (actor, owner pid) trajna gosenica zvara


def add_bead(sid):
    a, pd = tube_actor(1.7, MATERIALI["zvar"][0], metallic=1.0)
    set_lines(pd, SEAMS[sid])
    a.VisibilityOn()
    BEADS[sid] = (a, SPOJ[sid]["deli"][0])


def weld_progress(sids, t, offset):
    """t 0..1: sled raste po obodu; t>=1: skrij sled."""
    if t >= 1.0:
        for a in (glow_a, halo_a, arc_a):
            a.VisibilityOff()
        return
    lines, heads = [], []
    for sid in sids:
        for pl in SEAMS[sid]:
            n = max(2, int(round(len(pl) * t)) + 1)
            seg = pl[:n] + offset
            lines.append(seg)
            heads.append(seg[-1])
    set_lines(glow_pd, lines)
    set_lines(halo_pd, lines)
    pts = vtk.vtkPoints()
    for h in heads:
        pts.InsertNextPoint(*h)
    arc_pd.SetPoints(pts)
    arc_pd.Modified()
    flick = 0.8 + 0.4 * math.sin(t * 90.0)
    arc_src.SetRadius(5.0 * flick)
    for a in (glow_a, halo_a, arc_a):
        a.VisibilityOn()



# ------------------------------------------------------------------ stanje delov
STATE = {pid: {"off": np.zeros(3), "tint": 0.0, "vis": False, "op": 1.0} for pid in IDS}


def apply_part(pid):
    s, e = STATE[pid], PART[pid]
    for a, ed, (color, metal_, rough, scal) in zip(e["actors"], e["edges"], e["mat"]):
        a.SetVisibility(int(s["vis"]))
        ed.SetVisibility(int(s["vis"] and s["op"] > 0.6))
        a.SetPosition(*s["off"])
        ed.SetPosition(*s["off"])
        pr = a.GetProperty()
        t = s["tint"]
        if scal:
            a.GetMapper().SetScalarVisibility(int(t < 0.5))
            pr.SetColor(*(POUDAREK if t >= 0.5 else color))
        else:
            pr.SetColor(*(color * (1 - t) + POUDAREK * t))
        pr.SetMetallic(metal_ * (1 - 0.7 * t))
        pr.SetOpacity(s["op"])
    for sid, (a, owner) in BEADS.items():
        if owner == pid:
            a.SetPosition(*s["off"])
            a.GetProperty().SetOpacity(s["op"])


def fast_matrix(kid, back=0.0, angle=0.0):
    T = np.eye(4)
    T[2, 3] = -back
    c, s_ = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    R = np.eye(4)
    R[:2, :2] = [[c, -s_], [s_, c]]
    return FAST[kid]["M"] @ T @ R


def vtk_matrix(M):
    m = vtk.vtkMatrix4x4()
    for i in range(4):
        for j in range(4):
            m.SetElement(i, j, float(M[i, j]))
    return m


def set_fastener(kid, vis, back=0.0, angle=0.0, tint=1.0):
    a = FAST[kid]["actor"]
    a.SetVisibility(int(vis))
    a.SetUserMatrix(vtk_matrix(fast_matrix(kid, back, angle)))
    col = np.array(MATERIALI["vijak"][0]) * (1 - tint) + POUDAREK * tint
    a.GetProperty().SetColor(*col)
    a.GetProperty().SetMetallic(1.0 - 0.6 * tint)


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def frame_cam(pts, view, margin=1.12, fx=0.80, fy=0.76):
    """Kamera v smeri `view` (od sredisca proti kameri), ki zajame vse tocke v koristnem delu slike (fx, fy)."""
    pts = np.asarray(pts)
    c = (pts.min(0) + pts.max(0)) / 2
    d = unit(view)
    up = np.array([0, 0, 1.0])
    right = unit(np.cross(d, up))
    upv = np.cross(right, d)
    rel = pts - c
    half_v = math.tan(math.radians(cam.GetViewAngle() / 2))
    half_h = half_v * W / H
    dist = 0
    for p in rel:
        x, y, z = p @ right, p @ upv, p @ d
        dist = max(dist, abs(x) / (half_h * fx) + z, abs(y) / (half_v * fy) + z)
    dist *= margin
    return c, c + d * dist


def cam_decomp(c):
    f, p = np.array(c[0], float), np.array(c[1], float)
    v = p - f
    dist = np.linalg.norm(v)
    v /= dist
    return f, math.atan2(v[1], v[0]), math.asin(max(-1.0, min(1.0, v[2]))), dist


def cam_interp(a, b, t):
    """Prehod kamere po krogli okoli gledisca (azimut / elevacija / razdalja), da kamera ne leti skozi izdelek."""
    fa, aza, ela, da = cam_decomp(a)
    fb, azb, elb, db = cam_decomp(b)
    daz = (azb - aza + math.pi) % (2 * math.pi) - math.pi
    az, el, d = aza + daz * t, ela + (elb - ela) * t, da + (db - da) * t
    f = fa + (fb - fa) * t
    return f, f + np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)]) * d


CAM_NOW = [None]


def set_cam(focal, pos):
    cam.SetFocalPoint(*focal)
    cam.SetPosition(*pos)
    cam.SetViewUp(0, 0, 1)
    floor.SetVisibility(int(pos[2] > zmin + 1.0))
    ren.ResetCameraClippingRange()
    CAM_NOW[0] = (np.array(focal, float), np.array(pos, float))


def bbox_corners(pid, off=np.zeros(3)):
    b = DEL[pid]["bbox_mm"]
    mn, mx = np.array(b["min"]) + off, np.array(b["max"]) + off
    return [np.array([x, y, z]) for x in (mn[0], mx[0]) for y in (mn[1], mx[1]) for z in (mn[2], mx[2])]


def path_point(pts, t):
    pts = [np.array(p, float) for p in pts]
    seg = [np.linalg.norm(b - a) for a, b in zip(pts[:-1], pts[1:])]
    total = sum(seg)
    if total < 1e-9:
        return pts[-1]
    s = t * total
    for i, (a, b, L) in enumerate(zip(pts[:-1], pts[1:], seg)):
        if s <= L or i == len(seg) - 1:
            return a + (b - a) * (min(s, L) / L if L > 0 else 1)
        s -= L
    return pts[-1]


def visible_parts():
    return [p for p in IDS if STATE[p]["vis"]]


# ------------------------------------------------------------------ maskirna scena (ID slika): kontrola vidnosti in prekrivanja
MW, MH = 960, 540
MIN_PX = 4
mrw = vtk.vtkRenderWindow()
mrw.SetOffScreenRendering(1)
mrw.SetSize(MW, MH)
mrw.SetMultiSamples(0)
mren = vtk.vtkRenderer()
mren.SetBackground(0, 0, 0)
mrw.AddRenderer(mren)
mw2i = vtk.vtkWindowToImageFilter()
mw2i.SetInput(mrw)
mw2i.SetInputBufferTypeToRGB()
mw2i.ReadFrontBufferOff()
MID, MACT = {}, {}
N_MASK = [0]


def raw_polydata(V, F):
    pts = vtk.vtkPoints()
    pts.SetData(numpy_to_vtk(np.ascontiguousarray(V, dtype=np.float64), deep=True))
    cells = np.hstack([np.full((len(F), 1), 3, dtype=np.int64), F.astype(np.int64)]).ravel()
    ca = vtk.vtkCellArray()
    ca.ImportLegacyFormat(numpy_to_vtkIdTypeArray(cells, deep=True))
    pd = vtk.vtkPolyData()
    pd.SetPoints(pts)
    pd.SetPolys(ca)
    return pd


def mask_add(name, pd):
    i = len(MID) + 1
    m = vtk.vtkPolyDataMapper()
    m.SetInputData(pd)
    m.ScalarVisibilityOff()
    a = vtk.vtkActor()
    a.SetMapper(m)
    p = a.GetProperty()
    p.LightingOff()
    p.SetColor((i % 256) / 255.0, (i // 256) / 255.0, 0.0)
    a.VisibilityOff()
    mren.AddActor(a)
    MID[name], MACT[name] = i, a


for pid in IDS:
    mask_add(pid, raw_polydata(meshes[pid + "_V"], meshes[pid + "_F"]))
for kid, (v, k) in KOS.items():
    mask_add(kid, raw_polydata(vmesh[v["vrsta"] + "_V"], vmesh[v["vrsta"] + "_F"]))
for sid in SEAMS:
    _pd = vtk.vtkPolyData()
    set_lines(_pd, SEAMS[sid])
    _tf = vtk.vtkTubeFilter()
    _tf.SetInputData(_pd)
    _tf.SetRadius(3.0)
    _tf.SetNumberOfSides(8)
    _tf.Update()
    mask_add("Z" + sid, _tf.GetOutput())
ID2NAME = {i: n for n, i in MID.items()}


def mask_render(names, camc):
    """ID slika (MH x MW, izhodisce zgoraj levo): 0 = ozadje, sicer MID[ime] najblizjega objekta."""
    names = set(names)
    for n, a in MACT.items():
        a.SetVisibility(int(n in names))
    mc = mren.GetActiveCamera()
    mc.SetViewAngle(cam.GetViewAngle())
    mc.SetFocalPoint(*camc[0])
    mc.SetPosition(*camc[1])
    mc.SetViewUp(0, 0, 1)
    mren.ResetCameraClippingRange()
    mrw.Render()
    mw2i.Modified()
    mw2i.Update()
    a = vtk_to_numpy(mw2i.GetOutput().GetPointData().GetScalars()).reshape(MH, MW, 3)[::-1]
    N_MASK[0] += 1
    return a[..., 0].astype(np.int32) + a[..., 1].astype(np.int32) * 256


def mask_parts_sync():
    for pid in IDS:
        MACT[pid].SetPosition(*STATE[pid]["off"])


def mask_fast(kid, back):
    MACT[kid].SetUserMatrix(vtk_matrix(fast_matrix(kid, back)))


def visibility(targets, occluders, camc):
    """Delez vidnih pikslov vsakega cilja: (vidno ob vseh delih) / (vidno, ce bi bil cilj sam)."""
    alone = mask_render(targets, camc)
    full = mask_render(set(targets) | set(occluders), camc)
    out = {}
    for t in targets:
        m = alone == MID[t]
        n = int(m.sum())
        out[t] = float((full[m] == MID[t]).sum()) / n if n >= MIN_PX else 0.0
    return out, alone, full


FAZE_VIJAKA = ((1.0, "izvlecen", 0.4), (0.5, "na_pol", 0.3), (0.0, "privit", 0.3))


def back0(kid):
    return 45.0 + FAST[kid]["dostop"]


def fast_vis(kosi_, occl, camc):
    """Vidnost vijakov v treh legah (izvlecen, na pol, privit). Vrne {lega: {kid: delez}}."""
    res = {}
    for frac, key, _w in FAZE_VIJAKA:
        for kid in kosi_:
            mask_fast(kid, frac * back0(kid))
        res[key] = visibility(kosi_, occl, camc)[0]
    return res


def fast_score(res, kosi_):
    s = [sum(w * res[key][kid] for _f, key, w in FAZE_VIJAKA) for kid in kosi_]
    return min(s), float(np.mean(s))


def vdir(az, el):
    a, e = math.radians(az), math.radians(el)
    return np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])


KANDIDATI = [(az, el) for el in (-62, -45, -28, -12, 10, 25, 42, 60) for az in range(0, 360, 20)]


def search_view(frame_pts, eval_fn, axis=None, prefer=None, w_cont=0.06, margin=1.0, fx=0.72, fy=0.60, pregled=False):
    """Preisce smeri kamere; vrne najboljso po izmerjeni vidnosti. axis = smer, iz katere pride vijak (stran dostopa)."""
    best = None
    vsi = []
    n = 0
    for az, el in KANDIDATI:
        v = vdir(az, el)
        if pregled and (abs(el) > 45 or (el < 0 and (axis is None or axis[2] > -0.3))):
            continue                                    # pregled celega izdelka: brez tlorisnih pogledov; od spodaj samo, ce je treba
        if axis is not None and v @ axis < 0.15:
            continue                                    # kamera mora biti na strani dostopa
        camc = frame_cam(frame_pts, v, margin, fx, fy)
        mn, me = eval_fn(camc)
        n += 1
        s = 0.5 * mn + 0.5 * me
        if axis is not None:                            # posevno na os vijaka (~50 st.): vidi se glava IN gibanje vzdolz osi
            ang = math.degrees(math.acos(max(-1.0, min(1.0, float(v @ axis)))))
            s *= 1 - 0.35 * min(1.0, abs(ang - 50) / 50)
        s *= 1 - 0.4 * max(0.0, (abs(el) - 28) / 34)    # zmerna elevacija je za orientacijo bolj naravna kot pogled v tloris
        if el < 0 and (axis is None or axis[2] > -0.3) and (prefer is None or prefer[2] >= 0):
            s *= 0.8                                    # od spodaj samo, ce spoj res lezi spodaj
        vsi.append({"ocena": s, "smer": v, "cam": camc, "min": mn, "povp": me, "az": az, "el": el,
                    "blizina": float(v @ prefer) if prefer is not None else 0.0})
        if prefer is not None:                          # ob enaki vidnosti raje manjsi zasuk kamere
            s += w_cont * (float(v @ prefer) + 1) / 2
        if best is None or s > best["ocena"] + 1e-9:
            best = {"ocena": s, "smer": v, "cam": camc, "min": mn, "povp": me, "az": az, "el": el}
    if pregled and prefer is not None:
        # pregled: med smermi z vsaj 75 % najboljse vidnosti vzemi tisto, ki je najblizje glavnemu pogledu koraka
        # (operater ostane orientiran; mesta vijakov dodatno oznacijo obroci)
        top = max(c["ocena"] for c in vsi)
        best = max((c for c in vsi if c["ocena"] >= 0.75 * top), key=lambda c: (round(c["blizina"], 3), c["ocena"]))
    best["preizkusenih_smeri"] = n
    return best


# ------------------------------------------------------------------ 2D sloj (PIL) v slogu FINES
C_ORANZNA, C_ORANZNA_SV = (202, 80, 16), (238, 122, 58)                     # fines-500, fines-400
INK = {50: (247, 247, 248), 200: (220, 220, 223), 300: (194, 194, 199), 400: (154, 154, 161), 500: (107, 107, 114),
       600: (77, 77, 83), 700: (58, 58, 63), 800: (43, 43, 47), 900: (28, 28, 31)}
TOP_H, TOP_CRTA, BOT_H = 64, 4, 56
PISAVE = REPO / "trening" / "okolje" / "fable" / "pisave"
_FONTI = {"r": "Inter-Regular.ttf", "s": "Inter-SemiBold.ttf", "b": "Inter-Bold.ttf"}
_REZERVA = {"r": "C:/Windows/Fonts/segoeui.ttf", "s": "C:/Windows/Fonts/seguisb.ttf", "b": "C:/Windows/Fonts/segoeuib.ttf"}
PISAVA_IME = "Inter" if (PISAVE / _FONTI["b"]).exists() else "Segoe UI (rezerva - Inter ni namescen)"
_fc = {}


def font(kind, size):
    key = (kind, int(size))
    if key not in _fc:
        p = PISAVE / _FONTI[kind]
        _fc[key] = ImageFont.truetype(str(p) if p.exists() else _REZERVA[kind], int(size))
    return _fc[key]


LOGO = Image.open(REPO / "public" / "fines-logo.png").convert("RGBA") if (REPO / "public" / "fines-logo.png").exists() else None


def build_chrome(title, instr, st=None, n=None, badge=None):
    """Glava (logo, korak, naslov, nacin spajanja) in noga (navodilo, napredek). Izris pri 2x in pomanjsan (gladki robovi)."""
    s = 2
    im = Image.new("RGBA", (OUT_W * s, OUT_H * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, OUT_W * s, TOP_H * s], fill=(255, 255, 255, 255))
    d.rectangle([0, TOP_H * s, OUT_W * s, (TOP_H + TOP_CRTA) * s - 1], fill=C_ORANZNA + (255,))
    x = 28 + (LOGO.width if LOGO else 0) + 22
    d.rectangle([x * s, 16 * s, x * s + s, (TOP_H - 16) * s], fill=INK[200] + (255,))
    x += 22
    cy = TOP_H / 2
    if st is not None:
        txt = f"{st} / {n}"
        f = font("b", 22 * s)
        tw = d.textlength(txt, font=f)
        d.rounded_rectangle([x * s, (cy - 19) * s, x * s + tw + 32 * s, (cy + 19) * s], radius=19 * s, fill=C_ORANZNA + (255,))
        d.text((x * s + 16 * s + tw / 2, cy * s), txt, font=f, fill=(255, 255, 255, 255), anchor="mm")
        x += tw / s + 32 + 18
    d.text((x * s, cy * s), title, font=font("b", 28 * s), fill=INK[900] + (255,), anchor="lm")
    if badge:
        f = font("s", 20 * s)
        tw = d.textlength(badge, font=f)
        x1 = (OUT_W - 28) * s
        d.rounded_rectangle([x1 - tw - 36 * s, (cy - 19) * s, x1, (cy + 19) * s], radius=8 * s, fill=INK[800] + (255,))
        d.text((x1 - 18 * s - tw / 2, cy * s), badge, font=f, fill=(255, 255, 255, 255), anchor="mm")
    y0 = (OUT_H - BOT_H) * s
    for j in range(BOT_H * s):                       # preliv ink-700 -> ink-800 (kot glava tabele v aplikaciji)
        t = j / (BOT_H * s - 1)
        col = tuple(int(round(INK[700][c] * (1 - t) + INK[800][c] * t)) for c in range(3))
        d.line([0, y0 + j, OUT_W * s, y0 + j], fill=col + (255,))
    d.rectangle([0, y0, OUT_W * s, y0 + 2 * s - 1], fill=C_ORANZNA + (255,))
    d.text((28 * s, y0 + (BOT_H / 2 + 1) * s), instr, font=font("s", 25 * s), fill=(255, 255, 255, 255), anchor="lm")
    if st is not None:
        sw, sh, gap = 26, 8, 6
        x = OUT_W - 28 - n * sw - (n - 1) * gap
        for i in range(1, n + 1):
            col = C_ORANZNA if i < st else (255, 255, 255) if i == st else INK[600]
            yy = OUT_H - BOT_H / 2 - sh / 2 + 1
            d.rounded_rectangle([x * s, yy * s, (x + sw) * s, (yy + sh) * s], radius=4 * s, fill=col + (255,))
            x += sw + gap
    im = im.resize((OUT_W, OUT_H), Image.LANCZOS)
    if LOGO:
        im.alpha_composite(LOGO, (28, (TOP_H - LOGO.height) // 2))
    return im


def make_pill(text):
    s = 2
    f = font("s", 18 * s)
    tw = int(ImageDraw.Draw(Image.new("RGBA", (4, 4))).textlength(text, font=f))
    w, h = tw + 36 * s, 36 * s
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=h // 2, fill=INK[800] + (235,))
    d.text((w / 2, h / 2), text, font=f, fill=(255, 255, 255, 255), anchor="mm")
    return im.resize((w // s, h // s), Image.LANCZOS)


def make_box(lines):
    """Napis ob delu: bel zaobljen okvir z oranzno crto levo, notranji odmik, senca. lines = [(besedilo, 'b'|'r')]."""
    s = 2
    px_, py_, stripe, m = 16, 11, 6, 12                 # notranji odmik, sirina crte, rob za senco
    meas = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
    rows = []
    for txt, kind in lines:
        size, col, lh = (23, INK[900], 31) if kind == "b" else (18, INK[500], 25)
        f = font("b" if kind == "b" else "r", size * s)
        rows.append((txt, f, col, lh, meas.textlength(txt, font=f) / s))
    w = int(math.ceil(stripe + px_ * 2 + max(r[4] for r in rows)))
    h = py_ * 2 + sum(r[3] for r in rows)
    im = Image.new("RGBA", ((w + 2 * m) * s, (h + 2 * m) * s), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([m * s, (m + 3) * s, (m + w) * s, (m + h + 3) * s], radius=9 * s, fill=(20, 20, 24, 90))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(5 * s)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([m * s, m * s, (m + w) * s, (m + h) * s], radius=9 * s, fill=C_ORANZNA + (255,))
    d.rounded_rectangle([(m + stripe) * s, m * s, (m + w) * s, (m + h) * s], radius=9 * s, fill=(255, 255, 255, 255),
                        corners=(False, True, True, False))
    d.rounded_rectangle([m * s, m * s, (m + w) * s, (m + h) * s], radius=9 * s, outline=INK[300] + (255,), width=s)
    y = m + py_
    for txt, f, col, lh, _tw in rows:
        d.text(((m + stripe + px_) * s, (y + lh / 2) * s), txt, font=f, fill=col + (255,), anchor="lm")
        y += lh
    return im.resize((w + 2 * m, h + 2 * m), Image.LANCZOS), (w, h), m


def to_out(p):
    """Svetovna tocka (mm) -> piksel izhodne slike (izhodisce zgoraj levo)."""
    ren.SetWorldPoint(p[0], p[1], p[2], 1.0)
    ren.WorldToDisplay()
    d = ren.GetDisplayPoint()
    return np.array([d[0] / SS, (H - d[1]) / SS])


def aa_shape(layer, bbox, draw_fn, s=3):
    """Gladek izris (crta, krog) na lokalnem platnu s nadvzorcenjem."""
    x0, y0 = int(math.floor(max(0, bbox[0]))), int(math.floor(max(0, bbox[1])))
    x1, y1 = int(math.ceil(min(OUT_W, bbox[2]))), int(math.ceil(min(OUT_H, bbox[3])))
    if x1 <= x0 or y1 <= y0:
        return
    can = Image.new("RGBA", ((x1 - x0) * s, (y1 - y0) * s), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(can), lambda q: ((q[0] - x0) * s, (q[1] - y0) * s), s)
    layer.alpha_composite(can.resize((x1 - x0, y1 - y0), Image.LANCZOS), (x0, y0))


OVL = {"chrome": None, "callouts": [], "alpha": 1.0, "rings": [], "ring_t": 0.0}
PILL_SPODAJ = make_pill("POGLED OD SPODAJ")


def compose(img):
    base = img.convert("RGBA")
    if OVL["callouts"] or OVL["rings"]:
        lay = Image.new("RGBA", (OUT_W, OUT_H), (0, 0, 0, 0))
        for p in OVL["rings"]:                          # utripajoc obroc na mestu vijaka
            c = to_out(p)
            r = 15 + 5 * math.sin(OVL["ring_t"] * 2 * math.pi * 1.6)

            def ring(d, T, s, c=c, r=r):
                cx, cy = T(c)
                d.ellipse([cx - r * s, cy - r * s, cx + r * s, cy + r * s], outline=(255, 255, 255, 235), width=int(5.5 * s))
                d.ellipse([cx - (r - 1) * s, cy - (r - 1) * s, cx + (r - 1) * s, cy + (r - 1) * s], outline=C_ORANZNA + (255,), width=int(3.5 * s))
            aa_shape(lay, (c[0] - r - 4, c[1] - r - 4, c[0] + r + 4, c[1] + r + 4), ring)
        for co in OVL["callouts"]:
            x0, y0, x1, y1 = co["rect"]
            for p in co["anchors"]():
                a = to_out(p)
                if x0 <= a[0] <= x1 and y0 <= a[1] <= y1:
                    continue
                q = np.array([min(max(a[0], x0), x1), min(max(a[1], y0), y1)])

                def lead(d, T, s, a=a, q=q):
                    d.line([T(q), T(a)], fill=(255, 255, 255, 200), width=int(4.5 * s))
                    d.line([T(q), T(a)], fill=INK[800] + (255,), width=int(2.2 * s))
                    ax, ay = T(a)
                    d.ellipse([ax - 7 * s, ay - 7 * s, ax + 7 * s, ay + 7 * s], fill=(255, 255, 255, 255))
                    d.ellipse([ax - 5 * s, ay - 5 * s, ax + 5 * s, ay + 5 * s], fill=C_ORANZNA + (255,))
                aa_shape(lay, (min(a[0], q[0]) - 9, min(a[1], q[1]) - 9, max(a[0], q[0]) + 9, max(a[1], q[1]) + 9), lead)
        for co in OVL["callouts"]:
            m = co["m"]
            lay.alpha_composite(co["img"], (int(co["rect"][0]) - m, int(co["rect"][1]) - m))
        if OVL["alpha"] < 0.999:
            lay.putalpha(lay.getchannel("A").point(lambda v: int(v * OVL["alpha"])))
        base.alpha_composite(lay)
    if CAM_NOW[0] is not None and cam_decomp(CAM_NOW[0])[2] < math.radians(-15):
        base.alpha_composite(PILL_SPODAJ, (28, TOP_H + TOP_CRTA + 16))
    if OVL["chrome"] is not None:
        base.alpha_composite(OVL["chrome"])
    return base.convert("RGB")


# ------------------------------------------------------------------ postavitev napisov z masko (brez prekrivanja)
KS = OUT_W // MW                                     # 1 piksel maske = KS pikslov slike


def box_sums(mask, w, h):
    S = np.zeros((mask.shape[0] + 1, mask.shape[1] + 1), np.int64)
    S[1:, 1:] = mask.astype(np.int64).cumsum(0).cumsum(1)
    return S[h:, w:] - S[:-h, w:] - S[h:, :-w] + S[:-h, :-w]


def dilate(mask, r):
    return box_sums(np.pad(mask, r), 2 * r + 1, 2 * r + 1) > 0


KONTROLA_NAPISOV = []


def place_callouts(specs, important, geometry, oznaka, max_leaders=4):
    """specs = [(vrstice, anchors_fn)]. `important` = maska pikslov, ki jih napis NE sme prekriti (gibajoci deli, vijaki, zvari
    cez celo fazo); `geometry` = vsa geometrija (napis naj bo raje na ozadju). Izbere mesto z najmanjso ceno."""
    OVL["callouts"] = []
    imp = dilate(important, 7)
    sx0, sy0 = 16 // KS, (TOP_H + TOP_CRTA + 14) // KS
    sx1, sy1 = (OUT_W - 16) // KS, (OUT_H - BOT_H - 14) // KS
    pill = (0, sy0 - 4, (28 + PILL_SPODAJ.width + 12) // KS, (TOP_H + TOP_CRTA + 16 + PILL_SPODAJ.height + 10) // KS)
    placed = [pill]
    for lines, fn in specs:
        img, (w, h), m = make_box(lines)
        wm, hm = int(math.ceil(w / KS)) + 1, int(math.ceil(h / KS)) + 1
        si, sg, sr = box_sums(imp, wm, hm), box_sums(geometry, wm, hm), box_sums(important, wm, hm)
        ys, xs = np.mgrid[0:si.shape[0], 0:si.shape[1]]
        anc = np.array([to_out(p) / KS for p in fn()])
        an = anc.mean(0)
        dx = np.maximum(np.maximum(xs - an[0], an[0] - (xs + wm)), 0)
        dy = np.maximum(np.maximum(ys - an[1], an[1] - (ys + hm)), 0)
        dist = np.hypot(dx, dy)
        cost = si * 1000.0 + sg / float(wm * hm) * 60.0 + dist * 0.25 + np.where(dist < 24, 200.0, 0.0)
        cost[(xs < sx0) | (xs + wm > sx1) | (ys < sy0) | (ys + hm > sy1)] = 1e15
        for (a0, b0, a1, b1) in placed:
            cost[(xs < a1 + 5) & (xs + wm > a0 - 5) & (ys < b1 + 5) & (ys + hm > b0 - 5)] += 1e12
        j = int(np.argmin(cost))
        y, x = divmod(j, si.shape[1])
        placed.append((x, y, x + wm, y + hm))
        rect = (x * KS, y * KS, x * KS + w, y * KS + h)
        c = np.array([x + wm / 2, y + hm / 2])
        order = np.argsort(np.linalg.norm(anc - c, axis=1))[:max_leaders]
        OVL["callouts"].append({"img": img, "m": m, "rect": rect, "anchors": (lambda fn=fn, order=order: [fn()[i] for i in order])})
        KONTROLA_NAPISOV.append({"faza": oznaka, "napis": " | ".join(t for t, _ in lines), "okvir_px": [int(v) for v in rect],
                                 "prekrivanje_pomembnega_px": int(sr[y, x]) * KS * KS,
                                 "prekrivanje_z_varnostnim_robom_px": int(si[y, x]) * KS * KS,
                                 "delez_na_geometriji": round(float(sg[y, x]) / (wm * hm), 3)})


def clear_callouts():
    OVL["callouts"] = []
    OVL["rings"] = []
    OVL["alpha"] = 1.0


def ime_dela(d):
    w = " ".join(d["ime"].split()).split(" ")
    if w[0].isalpha() and not w[0].isupper():
        w[0] = w[0].capitalize()                       # "CEv" -> "Cev"
    return " ".join(w)


def ime_vijaka(v):
    return v["ime"].replace(" (predpostavka)", "").replace("Šestkotna zakovična", "Zakovična").replace(" s šestrobo glavo", "")


def smer_besedilo(kosi_):
    dz = float(np.mean([FAST[k]["dir"][2] for k in kosi_]))
    s = "od spodaj" if dz > 0.7 else "od zgoraj" if dz < -0.7 else "s strani"
    return s + (" skozi cev" if all(FAST[k]["dostop"] > 0 for k in kosi_) else "")


# ------------------------------------------------------------------ zajem
ff = None
if not SAMO_SLICICE:
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{OUT_W}x{OUT_H}", "-r", str(FPS), "-i", "-",
                           "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
                           "-movflags", "+faststart", str(POSKUS / "video.mp4")], stdin=subprocess.PIPE)
w2i = vtk.vtkWindowToImageFilter()
w2i.SetInput(rw)
w2i.SetInputBufferTypeToRGB()
w2i.ReadFrontBufferOff()
n_frames = [0]
timeline = []


def frame_image():
    rw.Render()
    w2i.Modified()
    w2i.Update()
    a = vtk_to_numpy(w2i.GetOutput().GetPointData().GetScalars()).reshape(H, W, 3)[::-1]
    return compose(Image.fromarray(np.ascontiguousarray(a)).resize((OUT_W, OUT_H), Image.LANCZOS))


def grab(save=None):
    n_frames[0] += 1
    if n_frames[0] % 300 == 0:
        print("slicica", n_frames[0], flush=True)
    if SAMO_SLICICE and not save:
        return
    img = frame_image()
    if ff:
        ff.stdin.write(img.tobytes())
    if save:
        img.save(save)


def run(seconds, fn, save=None, save_at=0.5):
    n = max(1, int(round(seconds * FPS)))
    k_save = int(save_at * (n - 1))
    for i in range(n):
        t = i / (n - 1) if n > 1 else 1.0
        OVL["ring_t"] = i / FPS
        fn(t)
        grab(save if (save and i == k_save) else None)


def move_cam(a, b, seconds, extra=None, save=None):
    def f(t):
        set_cam(*cam_interp(a, b, ease(t)))
        if extra:
            extra(t)
    run(seconds, f, save=save, save_at=1.0)


all_pts = [p for pid in IDS for p in bbox_corners(pid)]


def orbit_view(az_deg):
    base = np.array(POGLEDI["celota"])
    r = math.hypot(base[0], base[1])
    ang = math.atan2(base[1], base[0]) + math.radians(az_deg)
    return (r * math.cos(ang), r * math.sin(ang), base[2])


def show_all(final=True):
    for pid in IDS:
        STATE[pid].update(off=np.zeros(3), tint=0.0, vis=True, op=1.0)
        apply_part(pid)
    for kid in FAST:
        set_fastener(kid, final, 0, 0, 0.0)


# samokontrola maskirne scene: vsi ID-ji v sliki morajo biti znani (brez mesanja barv / osvetlitve)
show_all(True)
mask_parts_sync()
_m = mask_render(IDS, frame_cam(all_pts, POGLEDI["celota"], 1.05))
assert set(np.unique(_m)) <= ({0} | {MID[p] for p in IDS}), "maskirna scena vraca neznane ID-je"
assert len(set(np.unique(_m))) > 10, "maskirna scena je prazna"

IZDELEK = "Voziček proizvodni montažni 1000x500"

# ------------------------------------------------------------------ predogled.png
for sid in SEAMS:
    add_bead(sid)
set_cam(*frame_cam(all_pts, POGLEDI["celota"], 1.05))
OVL["chrome"] = build_chrome(IZDELEK, f"Montažno navodilo  ·  {len(koraki)} korakov")
frame_image().save(POSKUS / "predogled.png")

# ------------------------------------------------------------------ uvod
timeline.append((0.0, "uvod: celoten sestav"))
run(4.0, lambda t: set_cam(*frame_cam(all_pts, orbit_view(-25 + 50 * ease(t)), 1.05)), save=SLICICE / "uvod.png")

for pid in IDS:
    STATE[pid].update(vis=False)
    apply_part(pid)
for kid in FAST:
    set_fastener(kid, False)
for sid, (a, _) in list(BEADS.items()):
    ren.RemoveActor(a)
BEADS.clear()

# ------------------------------------------------------------------ koraki
KONTROLA_VIDNOSTI = []
KAMERE = {}
prev_cam = None
for k in koraki:
    st = k["st"]
    ids = k["deli_step"]
    paths = {p: [np.array(q, float) for q in v] for p, v in k["gibanje"]["pot_po_delih_mm"].items()}
    end_off = np.array(k["gibanje"]["do_mm"], float)
    sp = k["spajanje"]
    nacin = sp["nacin"]
    view = POGLEDI[k["kamera"]["pogled"]]
    kosi = [kid for g in sp["vijacni_material"] for kid in g["kosi"]]
    seams = [sid for sid in sp["spoji"] if sid in SEAMS]
    visible_now = visible_parts()
    KAMERE[st] = {}

    pts = [c for p in visible_now for c in bbox_corners(p, STATE[p]["off"])]
    for p in ids:
        for q in paths[p]:
            pts += bbox_corners(p, q)
    main_cam = frame_cam(pts, view, 1.06)
    timeline.append((n_frames[0] / FPS, f"korak {st}: {k['naslov']} ({sp['napis']})"))
    OVL["chrome"] = build_chrome(k["naslov"], k["navodilo"], st, len(koraki), sp["napis"])
    clear_callouts()

    # 1) prehod kamere, deli se pojavijo v izhodiscu; napis (ime + kolicina) na mestu, ki ga gibanje ne precka
    c0 = prev_cam or main_cam
    for p in ids:
        STATE[p].update(off=paths[p][0].copy(), tint=1.0, vis=True, op=0.0)
        apply_part(p)
    set_cam(*main_cam)
    if ids:
        mask_parts_sync()
        imp = np.zeros((MH, MW), bool)
        for tt in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
            for p in ids:
                MACT[p].SetPosition(*path_point(paths[p], tt))
            imp |= mask_render(ids, main_cam) > 0
        geo = (mask_render(visible_parts(), main_cam) > 0) | imp
        groups = {}
        for p in ids:
            groups.setdefault(DEL[p]["sifra"], []).append(p)
        specs = []
        for sif, pl in groups.items():
            kol = f"{len(pl)}x  " if len(pl) > 1 else ""
            specs.append(([(kol + ime_dela(DEL[pl[0]]), "b")], (lambda pl=pl: [PART[p]["center"] + STATE[p]["off"] for p in pl])))
        place_callouts(specs, imp, geo, f"korak {st}: premik")

    def ph1(t):
        e = ease(t)
        set_cam(*cam_interp(c0, main_cam, e))
        OVL["alpha"] = min(1.0, max(0.0, (t - 0.55) / 0.4))
        for p in ids:
            STATE[p]["op"] = e
            apply_part(p)
    run(1.0, ph1)
    OVL["alpha"] = 1.0

    # 2) premik po poti
    if ids:
        def ph2(t):
            e = ease(t)
            for p in ids:
                STATE[p]["off"] = path_point(paths[p], e)
                apply_part(p)
        run(0.5, lambda t: None)
        run(float(k["gibanje"]["trajanje_s"]) * (1.5 if len(next(iter(paths.values()))) > 2 else 1.0), ph2,
            save=SLICICE / f"korak_{st:02d}_a_premik.png", save_at=0.55)
        run(0.7, lambda t: None)
    clear_callouts()
    for p in ids:
        STATE[p]["tint"] = 0.0 if (seams or kosi) else 1.0      # med spajanjem pravi material, da se zvar / vijak jasno vidi
        apply_part(p)
    mask_parts_sync()
    occl = visible_parts()
    last_cam = main_cam

    # 3a) varjenje: detajl iz smeri, iz katere se stik najbolje vidi (izmerjeno)
    if seams:
        for sid in seams:
            MACT["Z" + sid].SetPosition(*end_off)
        cents = {sid: np.mean(np.vstack(SEAMS[sid]), axis=0) + end_off for sid in seams}
        seed = cents[min(seams, key=lambda s_: np.linalg.norm(cents[s_] - np.array(main_cam[1])))]
        cl = [sid for sid in seams if np.linalg.norm(cents[sid] - seed) < 190.0]
        cc = np.mean([cents[s_] for s_ in cl], axis=0)
        dpts = [cc + np.array([sx, sy, sz]) * 50.0 for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)] + [cents[s_] for s_ in cl]
        tg = ["Z" + s_ for s_ in cl]

        def ev_w(camc):
            vals = list(visibility(tg, occl, camc)[0].values())
            return min(vals), float(np.mean(vals))
        base = ev_w(frame_cam(dpts, view, 1.0, 0.72, 0.60))
        best = search_view(dpts, ev_w, prefer=unit(view), w_cont=0.15)
        det_cam = best["cam"]
        KONTROLA_VIDNOSTI.append({"korak": st, "faza": "detajl zvara", "cilji": cl, "smer_az_el": [best["az"], best["el"]],
                                  "vidnost_min": round(best["min"], 3), "vidnost_povp": round(best["povp"], 3),
                                  "vidnost_pogled_poskusa_02_min_povp": [round(base[0], 3), round(base[1], 3)],
                                  "preizkusenih_smeri": best["preizkusenih_smeri"],
                                  "opomba": "zvar tece po obodu stika - zadnja stran oboda je vedno zakrita"})
        KAMERE[st]["detajli"] = [{"spoj": "varjenje", "smer": np.round(best["smer"], 3).tolist(), "vidnost_povp": round(best["povp"], 3)}]
        move_cam(main_cam, det_cam, 1.0)
        imp = mask_render(tg, det_cam) > 0
        geo = (mask_render(occl, det_cam) > 0) | imp
        place_callouts([([("Zvar po obodu stika", "b")], (lambda: [cents[s_] for s_ in cl]))], imp, geo, f"korak {st}: detajl zvara")
        run(2.8, lambda t: weld_progress(seams, t, end_off), save=SLICICE / f"korak_{st:02d}_c_spoj.png", save_at=0.6)
        weld_progress(seams, 1.0, end_off)
        for sid in seams:
            add_bead(sid)
            BEADS[sid][0].SetPosition(*end_off)
        run(0.7, lambda t: None)
        clear_callouts()
        last_cam = det_cam

    # 3b) vijaki / zakovicne matice: pregled vseh mest s strani dostopa, nato detajl za vsako vrsto vijaka
    if kosi:
        is_nut = nacin == "zakovicenje"
        for kid in kosi:
            FAST[kid]["_back"] = back0(kid)
        ret = {kid: FAST[kid]["pos"] - FAST[kid]["dir"] * back0(kid) for kid in kosi}
        vstop = {kid: FAST[kid]["pos"] - FAST[kid]["dir"] * FAST[kid]["dostop"] for kid in kosi}
        ax = -np.mean([FAST[kid]["dir"] for kid in kosi], axis=0)
        ax = unit(ax) if np.linalg.norm(ax) > 0.5 else None
        wpts = [c for p in occl for c in bbox_corners(p, STATE[p]["off"])] + list(ret.values())

        def ev_all(camc):
            return fast_score(fast_vis(kosi, occl, camc), kosi)
        wide = search_view(wpts, ev_all, axis=ax, prefer=unit(view), w_cont=0.30, margin=1.04, fx=0.80, fy=0.74, pregled=True)
        wide_cam = wide["cam"]
        base_w = ev_all(main_cam)
        KONTROLA_VIDNOSTI.append({"korak": st, "faza": "pregled mest vijakov", "cilji": len(kosi), "smer_az_el": [wide["az"], wide["el"]],
                                  "vidnost_min": round(wide["min"], 3), "vidnost_povp": round(wide["povp"], 3),
                                  "vidnost_pogled_poskusa_02_min_povp": [round(base_w[0], 3), round(base_w[1], 3)],
                                  "preizkusenih_smeri": wide["preizkusenih_smeri"]})
        KAMERE[st]["pregled_spojev"] = {"smer": np.round(wide["smer"], 3).tolist(), "vidnost_povp": round(wide["povp"], 3)}
        for kid in kosi:
            set_fastener(kid, True, back0(kid), 0, tint=1.0)
        move_cam(last_cam, wide_cam, 1.3)
        by_name = {}
        for g in sp["vijacni_material"]:
            by_name.setdefault(ime_vijaka(VIJ[g["id"]]), []).extend(g["kosi"])
        imp = np.zeros((MH, MW), bool)
        for frac, _k, _w in FAZE_VIJAKA:
            for kid in kosi:
                mask_fast(kid, frac * back0(kid))
            imp |= mask_render(kosi, wide_cam) > 0
        geo = (mask_render(occl, wide_cam) > 0) | imp
        place_callouts([([(f"{len(gk)}x  {name}", "b"), (smer_besedilo(gk), "r")], (lambda gk=gk: [ret[kid] for kid in gk]))
                        for name, gk in by_name.items()], imp, geo, f"korak {st}: pregled mest vijakov", max_leaders=2)
        OVL["rings"] = [vstop[kid] for kid in kosi]
        run(2.0, lambda t: None, save=SLICICE / f"korak_{st:02d}_b_pregled.png", save_at=0.5)
        clear_callouts()
        last_cam = wide_cam
        KAMERE[st]["detajli"] = KAMERE[st].get("detajli", [])
        ghost_prev = []
        for gi, (name, gk) in enumerate(by_name.items()):
            # detajl pokaze vijak, ki je najblizje sredini skupine (pri vrsti vijakov srednji - stran od vogalov in koles)
            gc = np.mean([FAST[kid]["pos"] for kid in gk], axis=0)
            seed = FAST[min(gk, key=lambda kid: (round(float(np.linalg.norm(FAST[kid]["pos"] - gc)), 1),
                                                 float(np.linalg.norm(ret[kid] - np.array(wide_cam[1])))))]["pos"]
            cl = [kid for kid in gk if np.linalg.norm(FAST[kid]["pos"] - seed) < 190.0]
            cc = np.mean([FAST[kid]["pos"] for kid in cl], axis=0)
            dpts = ([cc + np.array([sx, sy, sz]) * 50.0 for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
                    + [FAST[kid]["pos"] for kid in cl] + [ret[kid] for kid in cl])
            axg = -np.mean([FAST[kid]["dir"] for kid in cl], axis=0)
            axg = unit(axg) if np.linalg.norm(axg) > 0.5 else None

            # profil, skozi katerega gre vijak (dostopna luknja), bo med vijacenjem prosojen -> pri izbiri smeri ne steje kot ovira
            skozi = {FAST[kid]["owner"] for kid in cl if FAST[kid]["dostop"] > 0}
            occl_g = [p for p in occl if p not in skozi]

            def ev_cl(camc, cl=cl, occl_g=occl_g):
                return fast_score(fast_vis(cl, occl_g, camc), cl)
            rocno = k["kamera"].get("detajl_smer_rocno")
            if rocno:                                    # rocni popravek cloveka ima prednost pred iskanjem
                camc = frame_cam(dpts, rocno, 1.0, 0.72, 0.60)
                mn, me = ev_cl(camc)
                best = {"smer": unit(rocno), "cam": camc, "min": mn, "povp": me, "az": None, "el": None, "preizkusenih_smeri": 0}
            else:
                best = search_view(dpts, ev_cl, axis=axg, prefer=unit(wide["smer"]), w_cont=0.10)
            det_cam = best["cam"]
            res = fast_vis(cl, occl, det_cam)
            res02 = fast_vis(cl, occl, frame_cam(dpts, view, 1.0, 0.72, 0.60))
            # privit vijak zakrit (npr. glava v cevi) -> zakrivajoci del za cas vijacenja prosojen
            privit = float(np.mean([res["privit"][kid] for kid in cl]))
            ghost = []
            if privit < 0.2:
                for kid in cl:
                    mask_fast(kid, 0.0)
                _v, alone, full = visibility(cl, occl, det_cam)
                tm = np.isin(alone, [MID[kid] for kid in cl])
                hid = full[tm & ~np.isin(full, [MID[kid] for kid in cl])]
                cnt = np.bincount(hid, minlength=len(MID) + 1)
                tot = max(1, int(cnt.sum()))
                ghost = [ID2NAME[i] for i in np.argsort(-cnt)[:3] if cnt[i] >= 0.25 * tot and ID2NAME[i] in STATE]
            KONTROLA_VIDNOSTI.append({
                "korak": st, "faza": "detajl vijačenja", "vijak": name, "cilji": cl, "smer_az_el": [best["az"], best["el"]],
                "vidnost_izvlecen": round(float(np.mean([res["izvlecen"][c] for c in cl])), 3),
                "vidnost_na_pol": round(float(np.mean([res["na_pol"][c] for c in cl])), 3),
                "vidnost_privit": round(privit, 3),
                "vidnost_pogled_poskusa_02": {key: round(float(np.mean([res02[key][c] for c in cl])), 3) for _f, key, _w in FAZE_VIJAKA},
                "prosojni_deli_med_vijacenjem": ghost, "preizkusenih_smeri": best["preizkusenih_smeri"]})
            KAMERE[st]["detajli"].append({"spoj": name, "smer": np.round(best["smer"], 3).tolist(),
                                          "vidnost_izvlecen": KONTROLA_VIDNOSTI[-1]["vidnost_izvlecen"], "prosojni_deli": ghost})

            def gh(t, ghost=ghost, ghost_prev=ghost_prev):
                for p in set(ghost) | set(ghost_prev):
                    a0 = 0.42 if p in ghost_prev else 1.0
                    a1 = 0.42 if p in ghost else 1.0
                    STATE[p]["op"] = a0 + (a1 - a0) * ease(t)
                    apply_part(p)
            move_cam(last_cam, det_cam, 1.1, extra=gh)
            imp = np.zeros((MH, MW), bool)
            for frac, _k, _w in FAZE_VIJAKA:
                for kid in cl:
                    mask_fast(kid, frac * back0(kid))
                imp |= mask_render(cl, det_cam) > 0
            geo = (mask_render(occl, det_cam) > 0) | imp
            place_callouts([([(f"{len(gk)}x  {name}", "b"), (smer_besedilo(gk), "r")],
                             (lambda cl=cl: [FAST[kid]["pos"] - FAST[kid]["dir"] * FAST[kid]["_back"] for kid in cl]))],
                           imp, geo, f"korak {st}: detajl vijačenja ({name})")

            def ph_screw(t, gk=gk):
                e = ease(min(1.0, t / 0.85))
                for kid in gk:
                    FAST[kid]["_back"] = back0(kid) * (1 - e)
                    set_fastener(kid, True, FAST[kid]["_back"], 0 if is_nut else 1440.0 * e, tint=1.0)
            run(0.6, lambda t: None)
            run(3.2, ph_screw, save=SLICICE / f"korak_{st:02d}_c_spoj{'' if gi == 0 else gi + 1}.png", save_at=0.4)
            run(0.6, lambda t, gk=gk: [set_fastener(kid, True, 0, 0, tint=1 - ease(t)) for kid in gk])
            clear_callouts()
            last_cam = det_cam
            ghost_prev = ghost

        def unghost(t, ghost_prev=ghost_prev):
            for p in ghost_prev:
                STATE[p]["op"] = 0.42 + 0.58 * ease(t)
                apply_part(p)
        move_cam(last_cam, main_cam, 1.2, extra=unghost)
    elif seams:
        move_cam(last_cam, main_cam, 1.0)

    # 4) konec koraka: prava barva materiala
    def ph4(t):
        for p in ids:
            STATE[p]["tint"] = (0.0 if (seams or kosi) else 1.0) * (1 - ease(t))
            apply_part(p)
    run(0.6, ph4, save=SLICICE / f"korak_{st:02d}_d_konec.png", save_at=1.0)
    clear_callouts()
    prev_cam = main_cam
    print(f"korak {st} pripravljen | maskirnih izrisov do zdaj: {N_MASK[0]}", flush=True)

# ------------------------------------------------------------------ zakljucek
show_all(True)
timeline.append((n_frames[0] / FPS, "zakljucek: koncni sestav"))
OVL["chrome"] = build_chrome(IZDELEK, "Voziček je sestavljen.")
fin = frame_cam(all_pts, orbit_view(0), 1.05)
move_cam(prev_cam, fin, 1.0)
run(5.0, lambda t: set_cam(*frame_cam(all_pts, orbit_view(70 * ease(t)), 1.05)), save=SLICICE / "zakljucek.png")

if ff:
    ff.stdin.close()
    ff.wait()
dolzina = n_frames[0] / FPS
(IZVOZ / "video_casovnica.json").write_text(json.dumps(
    {"fps": FPS, "velikost": [OUT_W, OUT_H], "nadvzorcenje": SS, "slicic": n_frames[0], "dolzina_s": round(dolzina, 2),
     "pisava": PISAVA_IME, "poglavja": [{"cas_s": round(t, 2), "opis": d} for t, d in timeline]}, ensure_ascii=False, indent=2), encoding="utf-8")

# ------------------------------------------------------------------ kontrole (pisne) + kamere nazaj v koraki.json
slabi_napisi = [n for n in KONTROLA_NAPISOV if n["prekrivanje_pomembnega_px"] > 0]
slaba_vidnost = [v for v in KONTROLA_VIDNOSTI if v["faza"] == "detajl vijačenja" and v["vidnost_izvlecen"] < 0.6]
(IZVOZ / "kontrola_vidnosti.json").write_text(json.dumps({
    "metoda": "ID slika 960x540 (vsak del / vijak / zvar svoja barva). vidnost = vidni piksli cilja ob vseh delih / piksli cilja, ce bi bil sam. "
              "Vijak se meri v treh legah: izvlecen, na pol, privit. 'pogled poskusa 02' = isti izrez v smeri glavnega pogleda koraka.",
    "kandidatov_smeri": len(KANDIDATI), "maskirnih_izrisov": N_MASK[0], "prag_opozorila": "detajl vijačenja: izvlecen < 0,6",
    "pod_pragom": slaba_vidnost, "meritve": KONTROLA_VIDNOSTI}, ensure_ascii=False, indent=2), encoding="utf-8")
(IZVOZ / "kontrola_napisov.json").write_text(json.dumps({
    "metoda": "Maska gibajocih delov / vijakov / zvarov cez celo fazo (unija ID slik) + varnostni rob 14 px; napis se postavi na mesto z najmanjso ceno. "
              "prekrivanje_pomembnega_px mora biti 0.",
    "napisov": len(KONTROLA_NAPISOV), "s_prekrivanjem": slabi_napisi, "napisi": KONTROLA_NAPISOV}, ensure_ascii=False, indent=2), encoding="utf-8")
doc = json.loads((POSKUS / "koraki.json").read_text(encoding="utf-8"))
for k in doc["koraki"]:
    k["kamera"].update({kk: vv for kk, vv in KAMERE.get(k["st"], {}).items()})
(POSKUS / "koraki.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

print("slicic", n_frames[0], "dolzina", round(dolzina, 1), "s, ffmpeg", ff.returncode if ff else "ni (samo slicice)")
print("napisov", len(KONTROLA_NAPISOV), "| s prekrivanjem pomembnega:", len(slabi_napisi))
for v in KONTROLA_VIDNOSTI:
    if v["faza"] == "detajl vijačenja":
        print(f"  korak {v['korak']:>2} {v['vijak']:<28} izvlecen {v['vidnost_izvlecen']:.2f} na pol {v['vidnost_na_pol']:.2f} privit {v['vidnost_privit']:.2f}"
              f" | pogled 02: {v['vidnost_pogled_poskusa_02']} | prosojno: {v['prosojni_deli_med_vijacenjem']}")
    else:
        print(f"  korak {v['korak']:>2} {v['faza']:<28} min {v['vidnost_min']:.2f} povp {v['vidnost_povp']:.2f} | pogled 02: {v['vidnost_pogled_poskusa_02_min_povp']}")
